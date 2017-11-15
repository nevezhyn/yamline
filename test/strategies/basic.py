def echo(*args, **kwargs):
    if args and kwargs:
        return args, kwargs

    if args and not kwargs:
        return args

    if kwargs and not args:
        return kwargs


def print_params(*args, **kwargs):
    print args, kwargs


def zero():
    a = 1 / 0
