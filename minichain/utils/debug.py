from minichain.utils.disk_cache import disk_cache

def debug(f):
    def debugged(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            print(type(e), e)
            try:
                disk_cache.invalidate(f, *args, **kwargs)
            except:
                pass
            breakpoint()
            f(*args, **kwargs)

    return debugged