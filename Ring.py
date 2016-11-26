import numpy as np

class Ring():
    """

    """
    def __init__(self, length, dtype=None):
        self.__index = 0 # where we will place the next sample (not the last sample placed)
        self.__content = np.zeros(length, dtype)
        self.__length = length

    def __setitem__(self, key, value):
        if key.step != None or key.step != 1:
            raise TypeError('Ring does not support stepped slices')

    def __getitem__(self, key):
        if type(key) == int:
            return self.__content[(self.__index + key - 1)  % self.__length]
        elif type(key) is slice:
            raise TypeError('Ring does not support slices')

    def __delitem__(self, key):
        raise Exception('Ring does not support deletion')

    def __len__(self):
        return self.__length

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

    @property
    def raw(self):
        return np.copy(self.__content)

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
