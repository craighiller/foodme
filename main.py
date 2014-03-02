#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os
import logging
from user_model import User
from user_model import FreeTimeZone
from authomatic import Authomatic
from authomatic.adapters import Webapp2Adapter
from webapp2_extras import sessions
from google.appengine.ext import db
import texter
import cgi
import datetime
from google.appengine.api import urlfetch
import urllib


from config import CONFIG

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

authomatic = Authomatic(config=CONFIG, secret='some random secret string')

class BaseHandler(webapp2.RequestHandler):
    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)
 
        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)
 
    @webapp2.cached_property
    def session(self):
        # Returns a session using the default cookie key.
        return self.session_store.get_session()
        
    


class MainHandler(BaseHandler):
    def get(self):
        template_values = {}
        template = jinja_environment.get_template("home.html")
        self.session['number'] = None
        self.response.out.write(template.render(template_values))
        
class PickHandler(BaseHandler):
    def get(self):
        current_user = db.GqlQuery("SELECT * FROM User WHERE id = :1", self.session['id']).get()
        template_values = {
            'user_name':current_user.name, 
            'places':current_user.top_picks, 
            'start_time': current_user.last_start_time,
            'end_time': current_user.last_end_time
        }
        template = jinja_environment.get_template("pick.html")
        self.response.out.write(template.render(template_values))

    def post(self):     
        start_times = self.request.get_all('start_time')
        end_times = self.request.get_all('end_time')
        key = db.Key.from_path('User', self.session['id'])
        current_user = User.get(key)
        current_user.clearFreeTime()
        picks = []
        checked = self.request.get_all('food')
        for c in checked:
            if c == 'other':
                picks.append(self.request.get('picks'))
                continue
            picks.append(c)
        current_user.top_picks = ", ".join(picks)
        for index, t in enumerate(start_times):
            s_time = t
            e_time = end_times[index]
            s_time = datetime.time(int(s_time.split(':')[0]), int(s_time.split(':')[1]))
            current_user.last_start_time = s_time
            s_time = datetime.datetime.combine(datetime.datetime.now().date(), s_time)
            e_time = datetime.time(int(e_time.split(':')[0]), int(e_time.split(':')[1]))
            current_user.last_end_time = e_time
            e_time = datetime.datetime.combine(datetime.datetime.now().date(), e_time) 
            free_time = FreeTimeZone(reference=current_user, startTime=s_time, endTime=e_time)
            free_time.put()

        current_user.put()
        self.redirect('/results')

class ResultHandler(BaseHandler):
    def get(self):
        key = db.Key.from_path('User', self.session['id'])
        current_user = User.get(key)
        my_valid_friend = current_user.valid_friends()

        friends_times = {}
        for friend in my_valid_friend:
            friends_times[friend] = current_user.shared_free(friend)
        template_values = {'friends':friends_times}
        template = jinja_environment.get_template("result.html")
        self.response.out.write(template.render(template_values))

    def post(self):
        key = db.Key.from_path('User', self.session['id'])
        current_user = User.get(key)
        time = self.request.get('time')
        place = self.request.get('place')
        checked = self.request.get_all('user')
        friends = []
        for c in checked:
            key = db.Key.from_path('User', c)
            friend = User.get(key)
            friends.append(friend.name + " - " + str(friend.number))
            url = "http://food-me.appspot.com/accepted?from={}:to={}".format(current_user.id, friend.id)
            x = "http://is.gd/create.php?format=simple&url={}".format(url)
            result = urlfetch.fetch(x).content
            texter.text(friend.number, "{} has invited you to eat at {} at {}! Click here to accept:{}".format(current_user.name, place, time, result))

        template_values = {
            'friends':", ".join(friends),
            'place': place,
            'time': time
        }
        template = jinja_environment.get_template("success.html")
        self.response.out.write(template.render(template_values))

class AcceptedHandler(BaseHandler):
    def get(self):
        from_user, to_user = self.request.get("from").split(":to=")
        key = db.Key.from_path('User', from_user)
        from_user = User.get(key)
        key = db.Key.from_path('User', str(to_user))
        to_user = User.get(key)
        
        texter.text(from_user.number, "{} has accepted your invitaion!".format(to_user.name))
        
                 
class Login(BaseHandler):

    # The handler must accept GET and POST http methods and
    # Accept any HTTP method and catch the "provider_name" URL variable.
    def any(self, provider_name):

        # It all begins with login.
        result = authomatic.login(Webapp2Adapter(self), provider_name)

        # Do not write anything to the response if there is no result!
        if result:
            # If there is result, the login procedure is over and we can write to response.
            self.response.write('<a href="..">Home</a>')

            if result.error:
                # Login procedure finished with an error.
                self.response.write('<h2>Damn that error: {}</h2>'.format(result.error.message))

            elif result.user:
                # Hooray, we have the user!

                # OAuth 2.0 and OAuth 1.0a provide only limited user data on login,
                # We need to update the user to get more info.
                if not (result.user.name and result.user.id):
                    result.user.update()

                # Welcome the user.
                user_name = result.user.name
                user_id = result.user.id
                #self.response.write(result.user.credentials)
                self.redirect('/pick')
                # Seems like we're done, but there's more we can do...

                # If there are credentials (only by AuthorizationProvider),
                # we can _access user's protected resources.
                if result.user.credentials:

                    # Each provider has it's specific API.
                    if result.provider.name == 'fb':
                        self.response.write('Your are logged in with Facebook.<br />')

                        # We will access the user's 5 most recent statuses.

                        url = 'https://graph.facebook.com/me/friends'
                        # Access user's protected resource.
                        response = result.provider.access(url)
                        #self.response.write(response.data['data'][4])

                        if response.status == 200:
                            # Parse response.
                            friends = {}
                            user_friends = response.data['data']
                            for item in user_friends:
                                friends[item['id']] = item['name']
                            
                            user = User.get_or_insert(user_id, id=user_id, name=user_name)
                            if self.session['number'] != None:
                                user.number = self.session['number']
                            user.friends = str(friends)
                            user.put()
                            
                            self.session['id'] = user_id
                            self.session['name'] = user_name
                            
                            error = response.data.get('error')

                            if error:
                                self.response.write('Damn that error: {}!'.format(error))
                        else:
                            self.response.write('Damn that unknown error!<br />')
                            self.response.write('Status: {}'.format(response.status))
                            
class SignUpHandler(BaseHandler):
    def get(self):
        self.session['number'] = self.request.get("number")
        self.redirect('/login/fb')

class Logout(BaseHandler):
    def any(self):
        self.session['id'] = None
        self.session['name'] = None
        self.redirect('/')
 
config = {}       
config['webapp2_extras.sessions'] = {
    'secret_key': '42',
}   

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/pick', PickHandler),
    ('/results', ResultHandler),
    ('/signup', SignUpHandler),
    ('/accepted', AcceptedHandler),
    webapp2.Route(r'/login/<:.*>', Login, handler_method='any'),
    webapp2.Route('/logout', Logout, handler_method = 'any')

], config=config, debug=True)

