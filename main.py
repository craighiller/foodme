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
import cgi
import datetime

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
        
	def get_current_user(self):
		return db.GqlQuery("SELECT * FROM User WHERE id = :1", self.session['id']).get()


class MainHandler(BaseHandler):
    def get(self):
        template_values = {}
        template = jinja_environment.get_template("home.html")
        self.response.out.write(template.render(template_values))
        
class PickHandler(BaseHandler):
    def get(self):
        template_values = {'user_name':self.session['name']}
        template = jinja_environment.get_template("pick.html")
        self.response.out.write(template.render(template_values))

    def post(self):
    	self.response.write('<html><body>Your free time:<pre>')
    	start_times = self.request.get_all('start_time')
    	end_times = self.request.get_all('end_time')
    	current_user = db.GqlQuery("SELECT * FROM User WHERE id = :1", self.session['id']).get()

    	for index, t in enumerate(start_times):
    		s_time = t
    		e_time = end_times[index]
    		self.response.write(cgi.escape(s_time) + ' to ' + cgi.escape(e_time) + '<br>')
    		s_time = datetime.time(int(s_time.split(':')[0]), int(s_time.split(':')[1]))
    		s_time = datetime.datetime.combine(datetime.datetime.now().date(), s_time)
    		e_time = datetime.time(int(e_time.split(':')[0]), int(e_time.split(':')[1]))
    		e_time = datetime.datetime.combine(datetime.datetime.now().date(), e_time) 
    		free_time = FreeTimeZone(reference=current_user, startTime=s_time, endTime=e_time)
    		free_time.put()
        self.response.write('</pre></body></html>')
    	self.redirect('/results')

class ResultHandler(BaseHandler):
    def get(self):
    	current_user = db.GqlQuery("SELECT * FROM User WHERE id = :1", self.session['id']).get()
    	my_valid_friend = current_user.valid_friends()

    	friends_times = {}
    	for friend in my_valid_friend:
    		friends_times[friend] = current_user.shared_free(friend)
        template_values = {'friends':friends_times}
        template = jinja_environment.get_template("result.html")
        self.response.out.write(template.render(template_values))

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
                            	friends[item['name']] = item['id']
                            user = User.get_or_insert(user_id, id=user_id, name=user_name)
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

class Logout(webapp2.RequestHandler):
    def any(self):
        self.response.set_cookie(None)    
 
config = {}       
config['webapp2_extras.sessions'] = {
    'secret_key': '42',
}   

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/pick', PickHandler),
    ('/results', ResultHandler),
    webapp2.Route(r'/login/<:.*>', Login, handler_method='any'),
    webapp2.Route('/logout', Logout, handler_method = 'any')

], config=config, debug=True)

