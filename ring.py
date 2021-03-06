import numpy as np
import weakref
import random
import string
import sys
eps = np.finfo(float).eps


class Ring(object):
    """

    """
    def __init__(self, length, dtype=None):
        self.__index         = 0 # where we will place the next sample (not the last sample placed)
        self.__content       = np.zeros(length, dtype)
        self.__length        = length
        self.__active_taps   = {}
        self.__inactive_taps = {}

    def __setitem__(self, key, value):
        raise TypeError('Ring only supports assignment through the .append method')

    def __getitem__(self, key):
        if type(key) == int:
            return self.__content[self.index_of(key)]
        elif type(key) is slice:
            raise TypeError('Ring does not support slices')

    def __delitem__(self, key):
        raise Exception('Ring does not support deletion')

    def __len__(self):
        return self.__length

    def index_of(self, i):
        """
        i (int): a position relative to the last sample appended. If i is 0,
                 this will get the index of the last sample added. If i is -1,
                 this will get the index of the second last sample added
        """
        return (self.__index + i - 1)  % self.__length

    def recent(self, size):
        """
        Get the <size> most recently appended samples
        """
        if size <= self.__index:
            return self.__content[self.__index - size:self.__index]

        # we need to wrap
        if size > self.__length:
            raise IndexError('larger than current buffer size')

        last_part = self.__content[:self.__index]
        first_part = self.__content[-(size - len(last_part)):]
        return np.concatenate([first_part, last_part])

    def append(self, items):
        count = len(items)

        # We cannot use iteritems because deactivate() modifies __active_taps.
        # We must use items instead.
        for name, tap in self.__active_taps.items():
            if tap.valid_ring_space < count:
                print 'Tap deactivated: {0}'.format(name)
                tap.valid = False
                tap.deactivate()

        # In the most common case, we don't have to loop around
        if self.__index + count <= self.__length:
            self.__content[self.__index:self.__index + count] = items

        elif count > self.__length:
            raise IndexError('Cannot append buffer longer than the ring length')

        else:
            # space remaining before end of the raw buffer
            len1 = self.__length - self.__index
            # amount of items that will be placed at the beginning of the buffer
            len2 = count - len1

            self.__content[self.__index:] = items[:len1]
            self.__content[:len2] = items[len1:]

        self.__index += count
        self.__index %= self.__length

    def rewind(self, amount):
        self.__index = (self.__index - amount) % len(self)

    def create_tap(self):
        tap = RingTap(self)
        self.add_tap(tap)
        return tap

    def add_tap(self, tap):
        if tap.name in self.__active_taps:
            raise NameError('a tap named {0} already exists'.format(tap.name))
        self.__active_taps[tap.name] = tap

    @property
    def raw(self):
        return self.__content

    @property
    def index(self):
        return self.__index

    @property
    def active_taps(self):
        return self.__active_taps

    @property
    def inactive_taps(self):
        return self.__inactive_taps


class RingTap(object):
    def __init__(self, ring, name=None):
        if not isinstance(ring, Ring):
            raise TypeError('RingPosition requires an instance of Ring')

        # If no name was supplied, use a random string
        if name is None:
            name = ''.join(random.choice(string.ascii_uppercase) for i in range(8))
        if not isinstance(name, str):
            raise TypeError('RingTap name must be a string')
        self.name = name

        # weakref returns a function. call self.get_ring() to get the ring
        self.get_ring = weakref.ref(ring)

        # Are all the samples between here and the ring[0] valid?
        self.valid = True

        # note that the __ring_index is a index OF the ring.__content
        self.index = self.get_ring().index_of(0)

        self.__samples_elapsed = 0

    def activate(self):
        ring = self.get_ring()
        if self.name in ring.inactive_taps:
            del ring.inactive_taps[self.name]
        ring.active_taps[self.name] = self

    def deactivate(self):
        ring = self.get_ring()
        if self.name in ring.active_taps:
            del ring.active_taps[self.name]
        ring.inactive_taps[self.name] = self

    def advance(self, amount):
        """ advance the index by <amount> samples """
        ring = self.get_ring()
        if amount > len(ring):
            raise RingPointerWarning('advance amount larger than ring buffer size')
        if amount >= self.valid_buffer_length:
            self.valid = False
            raise RingPointerWarning('amount ({0}) exceeded valid_buffer_length'.format(amount))

        self.__samples_elapsed += amount
        self.__ring_index += amount
        self.__ring_index %= len(ring)

    def get_samples(self, number):
        if number > self.valid_buffer_length or number < 0:
            print('get_sample argument out of range')
            raise BufferError('get_sample agrument out of range')

        ring = self.get_ring()
        first_part = ring.raw[self.index:self.index + number]
        missing_sample_count = number - len(first_part)
        if missing_sample_count == 0:
            return first_part
        else:
            return np.concatenate((first_part, ring.raw[:missing_sample_count]))

    @property
    def valid_buffer_length(self):
        """ How many samples behind the 'seam' are we?

        For example if 'C' is our current self.index, and 'E' is ring[0] (the
        last sample appended), this will return 3. Note that in this example,
        ring.__index would be pointing to f

        [a, b, C, d, E, f]

        This should be equal to the number of samples that it is safe to get
        """
        ring = self.get_ring()
        if self.__ring_index <= ring.index_of(0):
            return ring.index_of(0) - self.index + 1
        else:
            return ring.index_of(0) + len(ring) - self.index + 1

    @property
    def valid_ring_space(self):
        """ How many samples may be appended to the ring without invalidating this tap"""
        ring = self.get_ring()
        return len(ring) - self.valid_buffer_length

    @property
    def index(self):
        return self.__ring_index

    @index.setter
    def index(self, i):
        """ set the index of ring.__content[index]. Assume i is a valid index
        """
        self.__ring_index = i % len(self.get_ring())
        self.valid = True
        self.__samples_elapsed = 0

    @property
    def samples_elapsed(self):
        return self.__samples_elapsed


class AnnotatedRing(Ring):
    """ Annotated Ring stores audio data in a ring buffer like Ring, but it
    also stores lower resolution metadata about the audio. The metadata is
    calculated and added in calls to self.append

    The resolution of the metadata is determined by the blocksize, which should
    be an integer number of samples. The length of the buffer is defined as the
    <num_blocks> * <blocksize>.

    Metadata is stored in arrays of size <num_blocks>. A block_index refers to
    the index of one of these lower resolution arrays that are in parallel
    to the audio arrays.
    """
    def __init__(self, num_blocks, blocksize=512, dtype=None):
        super(AnnotatedRing, self).__init__(num_blocks * blocksize, dtype=dtype)
        self.__num_blocks = num_blocks
        self.__blocksize  = int(blocksize)
        self.__energy     = np.zeros(num_blocks)
        self.__transients = np.zeros(num_blocks, dtype='bool')

        if num_blocks <= 1:
            raise Exception('Annotated Ring requires two or more blocks')

        # Space to store rfft of each block
        # self.__spectrum  = np.zeros((num_blocks, blocksize), dtype='complex128')

        # Difference in db between this block and the one before it
        self.__diff_db = np.zeros(num_blocks)

    def append(self, items):
        # How far in to the most recent boundary is the index
        boundary_distance = self.index % self.__blocksize

        # How many boundaries are we going to cross in this call to .append?
        boundaries_crossed = (boundary_distance + len(items)) / self.__blocksize

        # At what index does the first boundary start?
        first_boundary_index = int(self.index / self.__blocksize)

        # Now we can actually append the items
        super(AnnotatedRing, self).append(items)

        # Create a python list of of the indicies of self.__energy that we will
        # update. For example if num_blocks==4, this might be [3, 0, 1]
        block_indices = [
            ((first_boundary_index + i) % len(self.__energy))
            for i in range(boundaries_crossed)]

        if len(block_indices) == 0:
            return 0

        self.__annotate(block_indices)

        return boundaries_crossed

    def __annotate(self, block_indices):
        """ Add annotations to block indices supplied by the <indices> array

        Used only internally to analyze recently added blocks.

        block_indices refers to the indices of blocks where we store our metadata

        Two examples:

        1. if our blocksize is 512, block_index 0 would refer to the
        first 512 samples in the self.raw array

        2. For example if num_blocks==4, this might be [3, 0, 1]

        __annotate assumes that the samples for block_indices are written to
        self.raw when it is called
        """

        # The indices in our raw content where our bondaries start
        raw_indices = [i * self.__blocksize for i in block_indices]

        # A python array of the numpy arrays, each containing a region of the
        # raw content. Note that indexing numpy arrays in this way creates a
        # reference (not a copy).
        regions = [self.raw[i:i+self.__blocksize] for i in raw_indices]

        # Convert the arrays to linear (not dB) energy
        energy = [np.sum(np.abs(r) ** 2) for r in regions]
        self.__energy[block_indices] = energy

        # We will compare each block with the block before it.
        # CAREFUL: iterator indexes self.__energy, not local energy variable
        iterator = [(self.__energy[i], self.__energy[i-1]) for i in block_indices]
        diffs =[10. * np.log10((eps + i) / (eps + p)) for i, p in iterator]

        self.__diff_db[block_indices] = diffs

        # Are there any transients?
        transients = np.array(diffs) > 20.
        self.__transients[block_indices] = transients

        # sys.stdout.write("{: >9.3f} {: >9.3f} \r".format(np.max(diffs), np.min(diffs)))
        # sys.stdout.flush()

    def create_tap(self):
        tap = AnnotatedRingTap(self)
        self.add_tap(tap)
        return tap

    @property
    def blocksize(self):
        return self.__blocksize

    @property
    def num_blocks(self):
        return self.__num_blocks

    @property
    def previous_updated_block_index(self):
        """ The "low resolution" block_index that was most recently updated
        """
        i  = int(self.index)
        bs = int(self.__blocksize)
        return ((i // bs) -1) % self.__num_blocks

    def recent_block_indices(self, number):
        start = self.previous_updated_block_index
        stop = start - number
        return range(start, stop, -1)

    def recent_diff(self, number):
        indices = self.recent_block_indices(number)
        return self.__diff_db[indices]

    def recent_energy(self, number=1):
        indices = self.recent_block_indices(number)
        return self.__energy[indices]

    def recent_transients(self, number):
        indices = self.recent_block_indices(number)
        return self.__transients[indices]

    def last_transient_block_index(self, number_to_check=None):
        """ Get the block index of the most recent transient. What we probably
        actually want is the distance of the last transient from the index.
        """
        if number_to_check is None:
            number_to_check = self.num_blocks
        transients = self.recent_transients(number_to_check)
        transient_indices = np.nonzero(transients)[0]
        if len(transient_indices) is 0:
            return None
        else:
            return transient_indices[-1]

    @property
    def transients(self):
        return self.__transients

    @property
    def energy(self):
        return self.__energy


class AnnotatedRingTap(RingTap):

    @property
    def samples_to_next_transient(self):
        annotated_ring    = self.get_ring()
        blocksize         = int(annotated_ring.blocksize)
        valid_indices     = self.valid_indices
        valid_transients  = annotated_ring.transients[valid_indices]
        samples_to_border = blocksize - self.position_in_block

        if len(valid_transients) == 0:
            return None
        elif valid_transients[0]:
            return 0
        else:
            transient_indices = np.nonzero(valid_transients)[0]
            if len(transient_indices) == 0:
                return None
            else:
                return samples_to_border + ((transient_indices[0]-1) * blocksize)

    @property
    def position_in_block(self):
        annotated_ring = self.get_ring()
        blocksize      = int(annotated_ring.blocksize)
        index          = int(self.index)
        return index % blocksize

    @property
    def block_index(self):
        """ get the block_index of the block where our tap is currently """
        annotated_ring = self.get_ring()
        blocksize = int(annotated_ring.blocksize)
        index     = int(self.index)
        return (index // blocksize) % annotated_ring.num_blocks

    @property
    def valid_indices(self):
        """ Get the indices of valid block indices. These will begin with the
        block index of the block that the tap's raw index is currently in. It
        ends with the updated block index (which will be just before the raw
        ring index)
        """
        annotated_ring = self.get_ring()
        tap_block_index = self.block_index
        ring_block_index = annotated_ring.previous_updated_block_index
        num_blocks = annotated_ring.num_blocks

        if not self.valid:
            return np.array([])

        # If both indices are in the same block, the ring index must be in the
        # next block.
        if tap_block_index == ring_block_index:
            return np.array([tap_block_index])

        # the valid buffer wraps around the ring
        elif tap_block_index > ring_block_index:
            return np.arange(tap_block_index, ring_block_index + 1 + num_blocks) % num_blocks

        elif tap_block_index < ring_block_index:
            return np.arange(tap_block_index, ring_block_index + 1)

    @property
    def previous_valid_indices(self):
        annotated_ring = self.get_ring()
        tap_block_index = self.block_index
        ring_block_index = annotated_ring.previous_updated_block_index
        num_blocks = annotated_ring.num_blocks

        if not self.valid:
            return np.array([])

        # If both indices are in the same block, the ring index must be in the
        # next block.
        if tap_block_index == ring_block_index:
            return np.array([tap_block_index])

        # we do not need to wrap around
        elif tap_block_index > ring_block_index:
            return np.arange(tap_block_index, ring_block_index, -1)

        elif tap_block_index < ring_block_index:
            return np.arange(tap_block_index, ring_block_index - num_blocks, -1) % num_blocks

    def upcoming_energy_blocks(self, number=None):
        """ Get an array containing the value of the upcoming <number> energy
        blocks. The actuall array size will be smaller if we have fewer valid
        indices.
        """
        ring = self.get_ring()
        energy = ring.energy[self.valid_indices[:number]]
        return energy

    def previous_energy_blocks(self, number=None):
        """ Get an array containing the value of the preceeding <number> energy
        blocks. Note that the array will be in reverse chronological order.
        [0] will be the current location, [1] will be the energy that happened
        just before
        """
        ring = self.get_ring()
        energy = ring.energy[self.previous_valid_indices[:number]]
        return energy

    def energy_db(self):
        """ Get the most recently upddated energy at this tap. 
        """
        ring = self.get_ring()
        en = float(ring.energy[self.block_index])
        return 10 * np.log10((en / ring.blocksize))

    def energy_unit(self):
        """ Get an energy level roughly scaled from 0. to 1. """
        db = self.energy_db()
        db += 80. # approx between 0 and 70
        if db < eps: db = eps
        if db > 70.: db = 70.
        return float(db / 70.)

    def decrescendo_length(self, number=None):
        """ For how many blocks into the future does this keep getting quieter
        """
        en = self.upcoming_energy_blocks(number)
        energy = np.array([ en[i]<en[i+1] for i in range(len(en) - 1) ])

        # is the block lower than the next one?
        is_increasing = np.nonzero(energy)[0]

        if len(is_increasing) == 0:
            return np.array([])
        else:
            return is_increasing[0]

    def number_below(self, value):
        """ How many of the previous samples are below <value>?
        """
        en = self.previous_energy_blocks()
        is_above = np.array(en) >= float(value)
        if np.any(is_above):
            return np.argmax(is_above)
        else:
            return len(is_above)



class RingPointerWarning(UserWarning):
    pass
