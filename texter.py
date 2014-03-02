import smtplib

def text(number, message):
    fromaddr = 'foodme14@gmail.com'
    toaddrs  = str(number)+'@txt.att.net'
    msg = message

    username = 'foodme14@gmail.com'
    password = 'foodme14password'

    server = smtplib.SMTP('smtp.gmail.com:587')
    server.starttls()
    server.login(username,password)
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()