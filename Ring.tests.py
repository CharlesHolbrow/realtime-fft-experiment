import numpy as np

from Ring import Ring
from Ring import RingPointerWarning

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
    p = a.create_tap()

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
    p = a.create_tap()
    assert(p.get_samples(1)[0] == 7)
    # pointing to the last item in the sample
    a.append(np.arange(7))
    try:
        a.append([99])
    except RingPointerWarning as e:
        pass
    assert p.valid is False

    a = Ring(8)
    p = a.create_tap()
    try:
        p.advance(2)
    except RingPointerWarning as e:
        pass
    assert p.valid is False
    return a, p

if __name__ == '__main__':
    test()