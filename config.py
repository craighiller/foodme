# config.py

from authomatic.providers import oauth2, oauth1, openid, gaeopenid

CONFIG = {
    
    'fb': {
           
        'class_': oauth2.Facebook,
        
        # Facebook is an AuthorizationProvider too.
        'consumer_key': '597526260333748',
        'consumer_secret': '20e8697a83086a6d8316794528e460b7',
        
        # But it is also an OAuth 2.0 provider and it needs scope.
        'scope': ['user_about_me', 'read_friendlists'],
    }

}