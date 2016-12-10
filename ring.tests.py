import numpy as np

from ring import Ring, RingPointerWarning, AnnotatedRing

def test_annotated_ring():
    a = AnnotatedRing(2, 4)
    assert len(a) == 8

    # return the number of boundaries crossed
    assert a.append(np.arange(3)) == 0
    assert a.append(np.arange(1)) == 1
    assert a.append([1]) == 0
    assert a.append(np.arange(7)) == 2
    assert a.append(np.arange(8)) == 2

    a = AnnotatedRing(3, 4)
    a.append([2, 2, 2, 2])
    assert np.all(a.recent_energy(1) == [16])
    a.append([3, 3, 3, 3])
    assert np.all(a.recent_energy(2) == [36, 16])
    a.append(np.ones(4))
    assert np.all(a.recent_energy(3) == [4, 36, 16])
    a.append([5, 5, 5, 5])
    assert np.all(a.recent_energy(2) == [100, 4])

    # verify when we append less than a full block
    a.append([2, 2])
    assert np.all(a.recent_energy(2) == [100, 4])
    a.append([2, 2])
    assert np.all(a.recent_energy(2) == [16, 100])

    # AnnotatedRingTap
    a = AnnotatedRing(3, 4)
    t = a.create_tap()
    assert t.block_index == 2
    a.append(np.arange(11))
    t.advance(1)
    assert t.block_index == 0




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

    # test rewinding pointer
    a = Ring(5)
    a.append(np.arange(2))
    assert a.pointer == 2
    a.rewind(1)
    assert a.p  == 1
    a.rewind(3)
    assert a.p == 3

if __name__ == '__main__':
    test()
    test_annotated_ring()

