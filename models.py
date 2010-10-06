# See LICENSE file for license information

#!/usr/bin/env python

from google.appengine.ext import db
    
class Image(db.Model):
    url = db.StringProperty(required=True)
    tags = db.StringListProperty(required=True)
    submitter = db.StringProperty(required=True)

class Banned(db.Model):
    name = db.StringProperty(required=True)
