try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

_thread_locals = local()

def set_it(obj):
    _thread_locals.facebook = obj


def get_it():
    return _thread_locals.facebook