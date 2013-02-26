#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pickle
import json
import requests
import os
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, username, password="Secret", active=True):
        try:
            self.username = unicode(username)
            self.password = unicode(password)
            self.active = active
        except Exception as e:
            print "Could not initiate user %s %s" % (username, e)

    def __repr__(self):
        return '<User %r>' % (self.username) 

    def get_id(self):
        return self.username

    def is_active(self):
        return self.active

class Storage(object):
    def __init__(self, path="/opt/kitin"):
        self.path = path
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def save(self, json_data):
        path = "/".join([self.path, self.get_type(json_data)])
        self.create_dir_if_not_exists(path)
        filename = "/".join([path, self.get_id(json_data)])
        f = open(filename, 'w')
        try:
            f.write(json.dumps(json_data))
        except IOError as e:
            print "no profit"

    def update(self, json_data):
        self.save(json_data)

    def delete(self, id):
        raise RuntimeError("no impl yet")

    def find_by_user(self, uid):
        raise RuntimeError("no impl yet")

    def load_user(self, uname, pword, remember):
        raise RuntimeError("no impl yet")

    @staticmethod
    def get_id(json):
        return json['@id'].rsplit("/",1)[1]

    @staticmethod
    def get_type(json):
        return json['@type']

    def create_dir_if_not_exists(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
