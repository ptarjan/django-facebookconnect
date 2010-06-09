
from django.core.exceptions import ImproperlyConfigured

import facebook

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

_thread_locals = local()


class LocalFacebookClient(object):
    
    def __init__(self, uid, access_token):
        self.uid = uid
        self.session_key = access_token # CHOP THIS
        self.access_token = access_token
        self.graph = facebook.GraphAPI(access_token)
        _thread_locals.facebook = self

    def __unicode__(self):
        return "<LocalFacebookClient: %s>" % (self.uid)


def get_facebook_client():
    try:
        return _thread_locals.facebook
    except AttributeError:
        raise ImproperlyConfigured('Make sure you have the Facebook middleware installed.')