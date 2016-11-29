import numpy as np
import weakref

class Ring(object):
    """

    """
    def __init__(self, length, dtype=None):
        self.__index = 0 # where we will place the next sample (not the last sample placed)
        self.__content = np.zeros(length, dtype)
        self.__length = length
        self.__positions = []

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

        for position in self.__positions:
            if position.valid_ring_space < count:
                position.valid = False
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

    def create_position(self):
        position = RingPosition(self)
        self.__positions.append(position)
        return position

    @property
    def raw(self):
        return self.__content

    @property
    def index(self):
        return self.__index



class RingPosition(object):
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
        """ How many samples may be appended to the ring without invalidating this position"""
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

def test():
    a = Ring(4)
    a.append([1, 2])
    assert np.all(a.raw == [1, 2, 0, 0])
    a.append([3, 4])
    assert np.all(a.raw == [1, 2, 3, 4])
    a.append([5])
    assert np.all(a.raw == [5, 2, 3, 4])
    a.append([6, 7])
    a.append([8, 9])
    assert np.all(a.raw == [9, 6, 7, 8])
    a.append([10, 11])
    assert np.all(a.raw == [9, 10, 11, 8])

    # test getitem
    a = Ring(4)
    a.append([0, 1, 2, 3])
    assert a[0] == 3
    assert a[-1] == 2
    a.append([4])
    assert(np.all(a.raw == [4, 1, 2, 3]))
    assert(a[0] == 4)
    assert(a[-1] == 3)
    assert(np.all(a.recent(0) == []))
    assert(np.all(a.recent(1) == [4]))
    a.append([5])
    assert(np.all(a.recent(2) == [4, 5]))
    # test wrap around
    assert(np.all(a.recent(3) == [3, 4, 5]))

    # test RingPosition
    a = Ring(8)
    p = a.create_position()

    assert p.valid_buffer_length == 1
    a.append(np.arange(4))
    assert p.valid_buffer_length == 5
    p.advance(1)
    assert p.valid_buffer_length == 4
    assert p.index == 0

    assert np.all(p.get_samples(4) == [0, 1, 2, 3])
    p.advance(2)
    assert np.all(p.get_samples(2) == [2, 3])
    a.append([4, 5, 6, 7, 8])


    p.advance(4)

    assert np.all(p.get_samples(2) == [6, 7])
    # test wraping
    assert np.all(p.get_samples(3) == [6, 7, 8])
    p.advance(2)
    assert(p.valid)
    assert(a.raw[p.index] == 8)

    # Ensure that we throw when breaking a ring pointer
    a = Ring(8)
    a.append(np.arange(8))
    p = a.create_position()
    assert(p.get_samples(1)[0] == 7)
    # pointing to the last item in the sample
    a.append(np.arange(7))
    try:
        a.append([99])
    except RingPointerWarning as e:
        pass
    assert p.valid is False

    a = Ring(8)
    p = a.create_position()
    try:
        p.advance(2)
    except RingPointerWarning as e:
        pass
    assert p.valid is False
    return a, p


