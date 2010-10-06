#!/usr/bin/env python

from google.appengine.ext import db
    
class Image(db.Model):
    url = db.StringProperty(required=True)
    tags = db.StringListProperty(required=True)
    submitter = db.StringProperty(required=True)

class Banned(db.Model):
    name = db.StringProperty(required=True)

class TagMetrics(db.Model):
    tag = db.StringProperty(required=True)
    count = db.IntegerProperty(required=True)
