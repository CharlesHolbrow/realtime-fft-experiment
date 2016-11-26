import numpy as np

class Ring():
    """
    note that unlike arrays when you slice Ring, both indices are inclusive

    ```
    a  = Ring(8)
    a.append(range(8))
    assert a[0] = 7
    assert a[0:0] = [7]
    ```
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
            if key.step != None and key.step != 1:
                raise TypeError('Ring does not support stepped slices')

            start = 0
            stop = 0
            print key.start, key.stop, key.step
            if key.start is not None: start = key.start
            if key.stop is not None and key.stop < self.__length: stop = key.stop
            print(start, stop)
            start += self.__index - 1
            start %= self.__length
            stop += self.__index
            print(start, stop)
            results_to_end = self.__content[start:stop]
            if stop < self.__length
                return results_to_end

            # at this point, the stop should always be larger than start. 
            missing_size = len()


    def __delitem__(self, key):
        raise Exception('Ring does not support deletion')

    def __len__(self):
        return self.__length

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

