from google.appengine.api import mail

def text(number, message):
    mail.send_mail(sender="FoodMe <foodme14@gmail.com>", to=str(number)+'@txt.att.net', body=message, subject="Food Plz")