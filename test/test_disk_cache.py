from minichain.utils.disk_cache import disk_cache


def test_disk_cache():
    a = 0

    @disk_cache
    def f(x):
        nonlocal a
        a += 1
        return a

    assert f(1) == 1
    assert f(1) == 1
    assert f(2) == 2
    assert f(2) == 2
