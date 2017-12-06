import traceback
import sys


def exptract_traceback():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    tr = traceback.extract_tb(exc_traceback)


def print_traceback():
    # tr = traceback.extract_tb(exc_traceback)
    traceback.print_exc()


def raise_last():
    raise


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
