# Copyright 2008-2009 Brian Boyer, Ryan Mark, Angela Nitzke, Joshua Pollock,
# Stuart Tiffen, Kayla Webley and the Medill School of Journalism, Northwestern
# University.
#
# This file is part of django-facebookconnect.
#
# django-facebookconnect is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-facebookconnect is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with django-facebookconnect.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import logging
log = logging.getLogger('facebookconnect.models')
import sha, random
from urllib2 import URLError
from urlparse import urlparse

import facebook

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db.models.signals import post_delete

from facebookconnect.localfb import get_facebook_client

import threading

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

_thread_locals = local()


class FacebookBackend:
    def authenticate(self, request=None):
        user = facebook.get_user_from_cookie(request.COOKIES, 
                                             settings.FACEBOOK_APP_ID, 
                                             settings.FACEBOOK_SECRET_KEY)
        if user:
            try:
                log.debug("Checking for Facebook Profile %s..." % user["uid"])
                fbprofile = FacebookProfile.objects.get(facebook_id=user["uid"])
                return fbprofile.user
            except FacebookProfile.DoesNotExist:
                log.debug("FB account hasn't been used before...")
                return None
            except User.DoesNotExist:
                log.error("FB account exists without an account.")
                return None
        else:
            log.debug("Invalid Facebook login")
            return None
        
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        
class BigIntegerField(models.IntegerField):
    empty_strings_allowed=False
    def get_internal_type(self):
        return "BigIntegerField"
    
    def db_type(self):
        if settings.DATABASE_ENGINE == 'oracle':
            return "NUMBER(19)"
        else:
            return "bigint"

class FacebookTemplate(models.Model):
    name = models.SlugField(unique=True)
    template_bundle_id = BigIntegerField()
    
    def __unicode__(self):
        return self.name.capitalize()

class FacebookProfile(models.Model):
    user = models.OneToOneField(User,related_name="facebook_profile")
    facebook_id = BigIntegerField(unique=True)
    
    __facebook_info = None
    dummy = True

    DUMMY_FACEBOOK_INFO = {
        'uid': 0,
        'name': '(Private)',
        'first_name': '(Private)',
        'last_name': '(Private)',
        'pic_square_with_logo': 'http://www.facebook.com/pics/t_silhouette.gif',
        'affiliations': None,
        'status': None,
        'proxied_email': None,
    }
    
    def __init__(self, *args, **kwargs):
        """reset local DUMMY info"""
        super(FacebookProfile,self).__init__(*args,**kwargs)
        try:
            self.DUMMY_FACEBOOK_INFO = settings.DUMMY_FACEBOOK_INFO
        except AttributeError:
            pass
        
        if hasattr(_thread_locals,'fbids'):
            if ( self.facebook_id 
                    and self.facebook_id not in _thread_locals.fbids ):
                _thread_locals.fbids.append(str(self.facebook_id))
        else: _thread_locals.fbids = [self.facebook_id]
    
    
    def __get_first_name(self):
        if self.__configure_me() and self.__facebook_info["first_name"]:
            return u"%s" % self.__facebook_info["first_name"]
        else:
            return self.DUMMY_FACEBOOK_INFO["first_name"]
    first_name = property(__get_first_name)

    def __get_last_name(self):
        if self.__configure_me() and self.__facebook_info["last_name"]:
            return u"%s" % self.__facebook_info["last_name"]
        else:
            return self.DUMMY_FACEBOOK_INFO["last_name"]
    last_name = property(__get_last_name)
    
    def __get_name(self):
        if self.__configure_me() and self.__facebook_info["name"]:
            return u"%s" % self.__facebook_info["name"]
        else:
            return self.DUMMY_FACEBOOK_INFO["name"]
    name = property(__get_name)
    full_name = property(__get_name)
    
    def __get_link(self):
        if self.__configure_me() and self.__facebook_info["link"]:
            return u"%s" % self.__facebook_info["link"]
        else:
            return self.DUMMY_FACEBOOK_INFO["link"]
    link = property(__get_link)
        
    def __get_about(self):
        if self.__configure_me() and self.__facebook_info["about"]:
            return u"%s" % self.__facebook_info["about"]
        else:
            return self.DUMMY_FACEBOOK_INFO["about"]
    about = property(__get_about)

    def __get_birthday(self):
        if self.__configure_me() and self.__facebook_info["birthday"]:
            return u"%s" % self.__facebook_info["birthday"]
        else:
            return self.DUMMY_FACEBOOK_INFO["birthday"]
    birthday = property(__get_birthday)
    
    def __get_work(self):
        if self.__configure_me() and self.__facebook_info["work"]:
            return u"%s" % self.__facebook_info["work"]
        else:
            return self.DUMMY_FACEBOOK_INFO["work"]
    work = property(__get_work)

    def __get_education(self):
        if self.__configure_me() and self.__facebook_info["education"]:
            return u"%s" % self.__facebook_info["education"]
        else:
            return self.DUMMY_FACEBOOK_INFO["education"]
    education = property(__get_education)
    
    def __get_email(self):
        if self.__configure_me() and self.__facebook_info["email"]:
            return u"%s" % self.__facebook_info["email"]
        else:
            return self.DUMMY_FACEBOOK_INFO["email"]
    email = property(__get_email)
    
    def __get_website(self):
        if self.__configure_me() and self.__facebook_info["website"]:
            return u"%s" % self.__facebook_info["website"]
        else:
            return self.DUMMY_FACEBOOK_INFO["website"]
    website = property(__get_website)

    def __get_hometown(self):
        if self.__configure_me() and self.__facebook_info["hometown"]:
            return u"%s" % self.__facebook_info["hometown"]
        else:
            return self.DUMMY_FACEBOOK_INFO["hometown"]
    hometown = property(__get_hometown)

    def __get_location(self):
        if self.__configure_me() and self.__facebook_info["location"]:
            return u"%s" % self.__facebook_info["location"]
        else:
            return self.DUMMY_FACEBOOK_INFO["location"]
    location = property(__get_location)

    def __get_gender(self):
        if self.__configure_me() and self.__facebook_info["gender"]:
            return u"%s" % self.__facebook_info["gender"]
        else:
            return self.DUMMY_FACEBOOK_INFO["gender"]
    gender = property(__get_gender)

    def __get_interested_in(self):
        if self.__configure_me() and self.__facebook_info["interested_in"]:
            return self.__facebook_info["interested_in"]
        else:
            return self.DUMMY_FACEBOOK_INFO["interested_in"]
    interested_in = property(__get_interested_in)
    
    def __get_meeting_for(self):
        if self.__configure_me() and self.__facebook_info["meeting_for"]:
            return self.__facebook_info["meeting_for"]
        else:
            return self.DUMMY_FACEBOOK_INFO["meeting_for"]
    meeting_for = property(__get_meeting_for)

    def __get_relationship_status(self):
        if self.__configure_me() and self.__facebook_info["relationship_status"]:
            return u"%s" % self.__facebook_info["relationship_status"]
        else:
            return self.DUMMY_FACEBOOK_INFO["relationship_status"]
    relationship_status = property(__get_relationship_status)

    def __get_religion(self):
        if self.__configure_me() and self.__facebook_info["religion"]:
            return u"%s" % self.__facebook_info["religion"]
        else:
            return self.DUMMY_FACEBOOK_INFO["religion"]
    religion = property(__get_religion)
    
    def __get_political(self):
        if self.__configure_me() and self.__facebook_info["political"]:
            return u"%s" % self.__facebook_info["political"]
        else:
            return self.DUMMY_FACEBOOK_INFO["political"]
    political = property(__get_political)

    def __get_verified(self):
        if self.__configure_me() and self.__facebook_info["verified"]:
            return u"%s" % self.__facebook_info["verified"]
        else:
            return self.DUMMY_FACEBOOK_INFO["verified"]
    verified = property(__get_verified)

    def __get_significant_other(self):
        if self.__configure_me() and self.__facebook_info["significant_other"]:
            return u"%s" % self.__facebook_info["significant_other"]
        else:
            return self.DUMMY_FACEBOOK_INFO["significant_other"]
    significant_other = property(__get_significant_other)
    
    def __get_timezone(self):
        if self.__configure_me() and self.__facebook_info["timezone"]:
            return u"%s" % self.__facebook_info["timezone"]
        else:
            return self.DUMMY_FACEBOOK_INFO["timezone"]
    timezone = property(__get_timezone)
    
    def __get_username(self):
        return self.facebook_id if "profile.php" in self.link else urlparse(self.link).path.split("/")[1]
    username = property(__get_username)
    
    def __get_picture_url(self):
       _facebook_obj = get_facebook_client()
       if self.__configure_me():
           return "https://graph.facebook.com/me/picture?access_token=%s" % _facebook_obj.access_token
       else:
           return self.DUMMY_FACEBOOK_INFO['pic_square_with_logo']
    picture_url = property(__get_picture_url)
    
    def facebook_only(self):
        """return true if this user uses facebook and only facebook"""
        if self.facebook_id and str(self.facebook_id) == self.user.username:
            return True
        else:
            return False
    
    def is_authenticated(self):
        """Check if this fb user is logged in"""
        _facebook_obj = get_facebook_client()
        if _facebook_obj.access_token and _facebook_obj.uid:
            my_profile = _facebook_obj.graph.get_object("me")
            fbid = my_profile["id"]
            if int(self.facebook_id) == int(fbid):
                return True
            else:
                return False
        else:
            return False

    def get_friends_profiles(self,limit=50):
        '''returns profile objects for this persons facebook friends'''
        friends = []
        friends_info = []
        friends_ids = []
        try:
            friends_ids = self.__get_facebook_friends()
        except (FacebookError,URLError), ex:
            log.error("Fail getting friends: %s" % ex)
        log.debug("Friends of %s %s" % (self.facebook_id,friends_ids))
        if len(friends_ids) > 0:
            #this will cache all the friends in one api call
            self.__get_facebook_info(friends_ids)
        for id in friends_ids:
            try:
                friends.append(FacebookProfile.objects.get(facebook_id=id))
            except (User.DoesNotExist, FacebookProfile.DoesNotExist):
                log.error("Can't find friend profile %s" % id)
        return friends

    def __get_facebook_friends(self):
        """returns an array of the user's friends' fb ids"""
        _facebook_obj = get_facebook_client()
        friends = []
        cache_key = 'fb_friends_%s' % (self.facebook_id)
    
        fb_info_cache = cache.get(cache_key)
        if fb_info_cache:
            friends = fb_info_cache
        else:
            log.debug("Calling for '%s'" % cache_key)
            friends = _facebook_obj.friends.getAppUsers()
            cache.set(
                cache_key, 
                friends, 
                getattr(settings,'FACEBOOK_CACHE_TIMEOUT',1800)
            )
        
        return friends        

    def __get_facebook_info(self,fbids):
        """
           Takes an array of facebook ids and caches all the info that comes
           back. Returns a tuple - an array of all facebook info, and info for
           self's fb id.
        """
        _facebook_obj = get_facebook_client()
        all_info = []
        my_info = None
        ids_to_get = []
        for fbid in fbids:
            if fbid == 0 or fbid is None:
                continue
            
            if _facebook_obj.uid is None:
                cache_key = 'fb_user_info_%s' % fbid
            else:
                cache_key = 'fb_user_info_%s_%s' % (_facebook_obj.uid, fbid)
        
            fb_info_cache = cache.get(cache_key)
            if fb_info_cache:
                log.debug("Found %s in cache" % fbid)
                all_info.append(fb_info_cache)
                if fbid == self.facebook_id:
                    my_info = fb_info_cache
            else:
                log.debug("User info not found in cache at %s" % cache_key)
                ids_to_get.append(fbid)
        
        if len(ids_to_get) > 0:
            log.debug("Calling for %s" % ids_to_get)
            tmp_info = _facebook_obj.graph.get_objects([str(x) for x in ids_to_get])
            
            all_info.extend(tmp_info)
            for info_key in tmp_info.keys():
                info = tmp_info[info_key]
                if info_key == str(self.facebook_id):
                    my_info = info
                
                if _facebook_obj.uid is None:
                    cache_key = 'fb_user_info_%s' % fbid
                else:
                    cache_key = 'fb_user_info_%s_%s' % (_facebook_obj.uid, info['id'])
                
                log.debug('Caching user info with key %s' % cache_key)
                cache.set(
                    cache_key, 
                    info, 
                    getattr(settings, 'FACEBOOK_CACHE_TIMEOUT', 1800)
                )
                
        return all_info, my_info

    def __configure_me(self):
        """Calls facebook to populate profile info"""
        try:
            log.debug("Configure fb profile %s" % self.facebook_id)
            if self.dummy or self.__facebook_info is None:
                ids = getattr(_thread_locals, 'fbids', [self.facebook_id])
                all_info, my_info = self.__get_facebook_info(ids)
                if my_info:
                    self.__facebook_info = my_info
                    self.dummy = False
                    return True
            else:
                return True
        except ImproperlyConfigured, ex:
            log.error('Facebook not setup')
        except (facebook.GraphAPIError, URLError), ex:
            log.error('Fail loading profile: %s' % ex)
        #except ValueError, ex:
        #    log.error('Fail parsing profile: %s' % ex)
        # except IndexError, ex:
        #     log.error("Couldn't retrieve FB info for FBID: '%s' profile: '%s' user: '%s'" % (self.facebook_id, self.id, self.user_id))
        
        return False

    def get_absolute_url(self):
        return "http://www.facebook.com/profile.php?id=%s" % self.facebook_id

    def __unicode__(self):
        return "FacebookProfile for %s" % self.facebook_id

def unregister_fb_profile(sender, **kwargs):
    """call facebook and let them know to unregister the user"""
    fb = get_facebook_client()
    fb.connect.unregisterUser([fb.hash_email(kwargs['instance'].user.email)])

#post_delete.connect(unregister_fb_profile,sender=FacebookProfile)