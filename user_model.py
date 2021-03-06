import datetime
from google.appengine.ext import db, ndb

class User(db.Model):
    id = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    name = db.StringProperty(required=True)
    friends = db.BlobProperty()
    top_picks = db.StringProperty()
    number = db.StringProperty()
    last_start_time = db.TimeProperty()
    last_end_time = db.TimeProperty()
    #profile_url = db.StringProperty(required=True)
    #access_token = db.StringProperty(required=True)

    def valid(self):
        return updated.date() == datetime.datetime.now().date()

    def shared_free(self, other_user):
        my_free = db.GqlQuery("SELECT * FROM FreeTimeZone WHERE reference = :1", self)
        they_free = db.GqlQuery("SELECT * FROM FreeTimeZone WHERE reference = :1", other_user)
        both_free = []
        for m in my_free:
            for t in they_free:
                included = m.check_inclusion(t)
                if included != None:
                    both_free.append(included)
        return both_free

    def valid_friends(self):
        results = User.all()
        my_valid_friends = []
        for p in results.run():
            if p == self: # don't include self
                continue
            if p.id in eval(self.friends) and self.shared_free(p):
                my_valid_friends.append(p)

        return my_valid_friends

    def clearFreeTime(self):
        my_free = db.GqlQuery("SELECT * FROM FreeTimeZone WHERE reference = :1", self)
        entries = my_free.fetch(1000)
        db.delete(entries)



class FreeTimeZone(db.Model):
    reference = db.ReferenceProperty(User)
    startTime = db.DateTimeProperty()
    endTime = db.DateTimeProperty()

    def check_inclusion(self, other_free_time):
        real_start = max(self.startTime, other_free_time.startTime)
        real_end = min(self.endTime, other_free_time.endTime)
        if real_start > real_end:
            return None
        return (real_start, real_end)

