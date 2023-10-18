from minichain.utils.disk_cache import disk_cache


def debug(f):
    def debugged(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            try:
                disk_cache.invalidate(f, *args, **kwargs)
            except:
                pass
            # breakpoint()
            print(type(e), e)
            f(*args, **kwargs)

    return debugged
