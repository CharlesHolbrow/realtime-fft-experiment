import numpy as np
import weakref

class Ring(object):
    """

    """
    def __init__(self, length, dtype=None):
        self.__index = 0 # where we will place the next sample (not the last sample placed)
        self.__content = np.zeros(length, dtype)
        self.__length = length
        self.__taps = []

    def __setitem__(self, key, value):
        if key.step != None or key.step != 1:
            raise TypeError('Ring does not support stepped slices')

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

        for tap in self.__taps:
            if tap.valid_ring_space < count:
                tap.valid = False
                raise RingPointerWarning('Pointer broken')

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
        self.__taps.append(tap)
        return tap

    @property
    def raw(self):
        return self.__content

    @property
    def index(self):
        return self.__index



class RingTap(object):
    def __init__(self, ring):
        if not isinstance(ring, Ring):
            raise TypeError('RingPosition requires an instance of Ring')
        # weakref returns a function. call self.get_ring() to get the ring
        self.get_ring   = weakref.ref(ring)

        # Are all the samples between here and the ring[0] valid?
        self.valid = True

        # note that the __ring_index is a index OF the ring.__content
        self.index = self.get_ring().index_of(0)

    def advance(self, amount):
        """ advance the index by <amount> samples """
        ring = self.get_ring()
        if amount > len(ring):
            raise RingPointerWarning('advance amount larger than ring buffer size')
        if amount >= self.valid_buffer_length:
            self.valid = False
            raise RingPointerWarning('amount ({0}) exceeded valid_buffer_length'.format(amount))

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

        For example if 'C' is our current __ring_index, and 'G' is ring[0] (the
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
        if i >= len(self.get_ring()):
            raise IndexError('index out of range')
        self.__ring_index = i
        self.valid = True

class RingPointerWarning(UserWarning):
    pass
