#!/usr/bin/env python
import json, os

from fabric.api import *

from sqlalchemy import *
from sqlalchemy.orm import *


@task
def create_db():
    if not os.path.exists(kitinconfig['DBNAME']):
        db = create_engine(kitinconfig['DBENGINE'] + ':///' + kitinconfig['DBNAME'])
        db.echo = True
        metadata = MetaData(db)
        marcpost = Table('marcpost', metadata,
            Column('id', Integer, primary_key=True),
            Column('userid', String),
            Column('marc', PickleType(pickler=json)),
            Column('bibid', String),
            Column('spills', PickleType(pickler=json))
        )
        marcpost.create()

@task
def create_wsgi_file():
    wsgifile = open('kitin.wsgi', 'w')
    wsgifile.write("activate_this = '%s/kitin/bin/activate_this.py'\n" % os.environ.get('WORKON_HOME'))
    wsgifile.write("execfile(activate_this, dict(__file__=activate_this))\n\n")
    wsgifile.write("from kitin import app as application\n")
    wsgifile.close()

@task
def prepare():
    if not os.path.exists(appconfig['UPLOAD_FOLDER']):
        os.mkdir(appconfig['UPLOAD_FOLDER'])
    create_db()

@task
def fetch_vendor_assets():
    local("tools/fetch-vendor-assets.sh")

