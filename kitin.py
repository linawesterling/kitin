#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import logging
import re
from datetime import datetime, timedelta
import json
import urllib2
from urlparse import urlparse
import mimetypes
from flask import (Flask, render_template, request, make_response, Response,
        abort, redirect, url_for, Markup, session)
from flask_login import LoginManager, login_required, login_user, flash, current_user, logout_user
import jinja2
import requests
from storage import Storage
from user import User


here = os.path.dirname(os.path.abspath(__file__))
logger = logging.getLogger(__name__)
mimetypes.add_type('application/font-woff', '.woff')


app = Flask(__name__)
app.config.from_pyfile('config.cfg')
app.config.from_envvar('SETTINGS', silent=True)
app.secret_key = app.config.get('SESSION_SECRET_KEY')
app.remember_cookie_duration = timedelta(days=31)
app.permanent_session_lifetime = timedelta(days=31)

login_manager = LoginManager()
login_manager.setup_app(app)

storage = Storage(app.config.get("DRAFTS_DIR"))

JSON_LD_MIME_TYPE = 'application/ld+json'



@login_manager.user_loader
def _load_user(uid):
    print "Loading user %s " % uid
    print "Sigel in session %s" % session.get('sigel')
    if not 'sigel' in session:
        return None
    return User(uid, sigel=session.get('sigel'))

@login_manager.unauthorized_handler
def _handle_unauthorized():
    return redirect("/login")


@app.context_processor
def global_view_variables():
    mtime = os.stat(here).st_mtime
    return {'modified': datetime.fromtimestamp(mtime)}


@app.route("/login", methods=["GET", "POST"])
def login():
    msg = None
    remember = False
    if request.method == "POST" and "username" in request.form:
        username = request.form["username"]
        password = request.form["password"]
        if "remember" in request.form:
            remember = True
        print "remember %s" % remember
        user = User(username)
        if getattr(app, 'fakelogin', False):
            sigel = "NONE"
        else:
            sigel = user.authorize(password, app.config)
        if sigel == None:
            sigel = ""
            msg = u"Kunde inte logga in. Kontrollera användarnamn och lösenord."
        else:
            user.sigel = sigel
            session['sigel'] = sigel
            login_user(user, remember)
            session.permanent = remember
            print "User logged in"
            print "User %s logged in with sigel %s" % (user.username, user.sigel)
            return redirect("/")
    return render_template("partials/login.html", msg = msg, remember = remember)

@app.route("/signout")
@login_required
def logout():
    "Trying to sign out..."
    logout_user()
    session.pop('sigel', None)
    return redirect("/login")

@app.route("/")
@login_required
def index():
    return render_template('index.html', user=current_user, partials = {"/partials/index" : "partials/index.html"})

@app.route("/search.json")
def search_json():
    resp = do_search()
    return raw_json_response(resp.text)

@app.route("/search")
@login_required
def search():
    #if 'q' in request.args:
    #    resp = do_search()
    return render_template('index.html', partials = {"/partials/search" : "partials/search.html"})

def do_search():
    q = request.args.get('q')
    f = request.args.get('f')
    freq = "&f=%s" % f.strip() if f else ''
    b = request.args.get('b', '')
    boost = ("&boost=%s" % b) if b else ''
    search_url = "%s/bib/_search?q=%s%s%s" % (app.config['WHELK_HOST'], q, freq, boost)
    return requests.get(search_url, headers=extract_x_forwarded_for_header(request))

@app.route('/record/<record_type>/<record_id>/holdings')
@login_required
def get_holdings(record_type, record_id):
        #path = "%s/hold/_find?q=annotates.@id:%s" % (app.config['WHELK_HOST'], record_id)
        bibnr = record_id.split("/")[-1]
        path = "%s/hold/_search?q=*+about.annotates.@id:\/resource\/bib\/%s" % (app.config['WHELK_HOST'], bibnr)
        resp = requests.get(path)
        return raw_json_response(resp.text)

@app.route('/holding/<holding_id>', methods=['GET'])
@login_required
def get_holding(holding_id):
    response = requests.get("%s/hold/%s" % (app.config['WHELK_HOST'], holding_id))
    if response.status_code == 200:
        resp = raw_json_response(response.text)
        resp.headers['etag'] = response.headers['etag'].replace('"', '')
        return resp
    else:
        abort(response.status_code)

@app.route('/holding', methods=['POST'])
@login_required
def create_holding():
    path = "%s/hold/" % (app.config['WHELK_HOST'])
    response = requests.post(path, data=request.data, allow_redirects=False)
    if response.status_code == 200:
        resp = raw_json_response(response.text)
        resp.headers['etag'] = response.headers['etag'].replace('"', '')
    elif response.status_code == 303:
        data = {}
        data['document'] = json.loads(response.text)
        data['document_id'] = urlparse(response.headers['Location']).path.rsplit("/")[-1]
        resp = raw_json_response(json.dumps(data))
        resp.headers['etag'] = response.headers['etag'].replace('"', '')
        return resp
    else:
        abort(response.status_code)

@app.route('/holding/<holding_id>', methods=['PUT'])
@login_required
def save_holding(holding_id):
    if_match = request.headers.get('If-match')
    h = {'content-type': JSON_LD_MIME_TYPE, 'If-match': if_match}
    path = "%s/hold/%s" % (app.config['WHELK_HOST'], holding_id)
    response = requests.put(path, data=request.data, headers=h, allow_redirects=True)
    if response.status_code == 200:
        resp = raw_json_response(response.text)
        resp.headers['etag'] = response.headers['etag'].replace('"', '')
        return resp
    else:
        abort(response.status_code)

@app.route('/holding/<holding_id>', methods=['DELETE'])
@login_required
def delete_holding(holding_id):
    path = "%s/hold/%s" % (app.config['WHELK_HOST'], holding_id)
    response = requests.delete(path)
    return make_response("success")

@app.route("/resource/<path:path>")
@login_required
def get_resource(path):
    qs = request.query_string
    url = "%s/resource/%s?%s" % (app.config['WHELK_HOST'], path, qs)
    remote_resp = requests.get(url)
    resp = Response(
        remote_resp.text,
        status=remote_resp.status_code,
        content_type=remote_resp.headers['content-type'])
    resp.headers['Expires'] = '-1'
    return resp

def extract_x_forwarded_for_header(request):
    if not request.headers.getlist("X-Forwarded-For"):
        remote_ip = request.remote_addr
    else:
        remote_ip = request.headers.getlist("X-Forwarded-For")[0]
    return {"X-Forwarded-For":"%s" % remote_ip}

def get_mockresult():
    with open("mocked_result_set.json") as f:
        return raw_json_response(f.read())

def chunk_number(num):
    number = str(num)
    return re.sub(r'\B(?=(\d{3})+(?!\d))', " ", number)

def get_facet_labels(f_group, f_values):

    mm = json.loads(open(app.config['MARC_MAP']).read())['bib']

    #group labels
    fparts = f_group.split('.')
    f_value_labels = {}
    propref = ''
    label_sv = ''

    #value labels
    if fparts[0] == "leader":
        propref = fparts[2]
        label_sv = _get_fixfield_label(propref, mm['000']['fixmaps'][0]['columns'])
        f_values = _get_value_label(f_values, propref, mm['fixprops'])
    elif fparts[0] == "custom":
        propref = fparts[1]
        label_sv, f_values = _get_custom_label(f_values, propref)

    elif fparts[0] == "fields":
        propref = fparts[3]
        if fparts[1].startswith('00'): #fixfield
            if fparts[3] == 'carrierType':
                f_values = _get_carrier_type(f_values, mm['007']['fixmaps'])
                propref = 'carrierType'
                label_sv = u'B\u00e4rartyp'
            else:
                label_sv = _get_fixfield_label(propref, mm[fparts[1]]['fixmaps'][0]['columns'])
                f_values = _get_value_label(f_values, propref, mm['fixprops'])

        else:
                f_values = dict([(value, [count]) for value, count in f_values.items()])
                label_sv = _get_subfield_label(fparts[1], fparts[3], mm)
    else:
        f_values = dict([(value, [count, value]) for value, count in f_values.items()])

    if not propref == "yearTime1":
        a = sorted(f_values.items(), key=lambda x: x[1][0], reverse=True)

    else:
        a = sorted(f_values.items(), key=lambda x: x[0], reverse=True)

    f_labels = {}
    f_labels['propref'] = propref
    f_labels['label_sv'] = label_sv
    f_labels['link'] = f_group
    f_labels['f_values'] = a#f_values
    return f_labels


def _get_custom_label(f_values, propref):
    #TODO: sync with backend
    specialdict = {"book": "Bok",
                    "audiobook": "Ljudbok",
                    "ebook": "E-bok",
                    "serial": "Tryckt tidskrift",
                    "eserial": "E-tidskrift",
                    "bookSerial": "Bok-/tidskriftstyp"
        }
    for code, count in f_values.items():
        if specialdict.get(code, None):
            f_values[code] = [count, specialdict[code]]
        else:
            f_values[code] = [count, code]
    label_sv = specialdict.get(propref, propref)
    return (label_sv, f_values)


def _get_subfield_label(tag, subfield, mm):
    for sf, sfinfo in mm[tag]['subfield'].items():
        if sf == subfield:
            return sfinfo['label_sv']

    return ""

def _get_carrier_type(f_values, fixmaps):
    for fm in fixmaps:
        for code, count in f_values.items():
            if code in fm['matchKeys']:
                label_sv = fm.get("label_sv", '').strip("&").replace("&", '')
                #TODO remove '&' from sv-labels in marcmap to avoid ugly strip-solution above
                f_values[code] = [count, label_sv]
    return f_values

def _get_value_label(f_values, propref, fp):
    #print "pf", fp
    for code, count in f_values.items():
        if fp.get(propref, None):
            value_label = fp[propref][code]['label_sv']
            f_values[code] = [count, value_label]
        else:
            if code in ['audiobook']:
                f_value[code] = [count, "Ljudbok"]
            f_values[code] = [count, code]

    return f_values

def _get_fixfield_label(pr, columns):
    #pr = PropRef, bibLevel
    #extracting the label of the leader position
    label_sv = pr
    for column in columns:
        try:
            if column['propRef'] == pr:
                label_sv = column.get('label_sv', pr)
                label_sv = label_sv.strip(" (1)")
        except Exception as e:
            print "propRef fail: ", e
            return None
    return label_sv

@app.route('/edit/<rec_type>/<rec_id>')
@login_required
def show_edit_record(rec_type, rec_id):
    return index()

@app.route('/marc/<rec_type>/<rec_id>')
@login_required
def show_marc_record(rec_type, rec_id):
    return index()
    #return render_template('index.html', partials = {"/partials/frbr" : "partials/frbr.html"})

@app.route('/jsonld/<rec_type>/<rec_id>')
@login_required
def show_jsonld_record(rec_type, rec_id):
    return index()

@app.route('/record/<rec_type>/<rec_id>')
@login_required
#@_required
def get_bib_data(rec_type, rec_id):
    # TODO: How check if user is logged in?
    draft = storage.get_draft(current_user.get_id(), rec_type, rec_id)
    if draft == None:
        whelk_url = "%s/%s/%s" % (app.config['WHELK_HOST'], rec_type, rec_id)
        response = requests.get(whelk_url)
        if response.status_code >= 400:
            app.logger.warning("Error response %s on GET <%s>" % (response.status_code, whelk_url))
            abort(response.status_code)
        else:
            document = response.text
            etag = response.headers['etag']
    else:
        json_data = json.loads(draft)
        document = json.dumps(json_data['document'])
        etag = json_data['etag']

    resp = raw_json_response(document)
    resp.headers['etag'] = etag
    return resp

## TODO: Add middleware to support DELETE method instead of POST
@app.route('/record/bib/<id>/draft/delete', methods=['POST'])
@login_required
def delete_draft(id):
    storage.delete_draft(current_user.get_id(), "bib", id)
    return redirect("/drafts")

@app.route('/record/bib/<id>/draft', methods=['POST'])
@login_required
def save_draft(id):
    """Save draft to kitin, called by form"""
    json_data = request.data
    storage.save_draft(current_user.get_id(), "bib", id, json_data, request.headers['If-match'])
    return json.dumps(request.json)

@app.route('/draft/<rec_type>/<rec_id>')
@login_required
def get_draft(rec_type, rec_id):
    draft = storage.get_draft(current_user.get_id(), rec_type, rec_id)
    if(draft):
        json_data = json.loads(draft)
        resp = raw_json_response(json.dumps(json_data['document']))
        resp.headers['etag'] = json_data['etag']
        return resp
    else:
        abort(404)

@app.route('/drafts')
@login_required
def get_drafts():
    drafts = storage.get_drafts_as_json(current_user.get_id())
    return raw_json_response(drafts)

@app.route("/record/bib/new", methods=["GET"])
@login_required
def get_template():
    """Returns a template object"""
    return raw_json_response(open(os.path.join(here, "examples/templates/monografi.json"), 'r').read())

@app.route("/holding/bib/new", methods=["GET"])
@login_required
def get_holding_template():
    return raw_json_response(open(os.path.join(here, "examples/templates/holding.json"), 'r').read())

@app.route('/record/<rec_type>/<rec_id>', methods=['PUT'])
@login_required
def update_document(rec_type, rec_id):
    """Saves updated records to whelk"""
    json_string = json.dumps(request.json)
    if_match = request.headers['If-match']
    h = {'content-type': JSON_LD_MIME_TYPE, 'If-match': if_match}
    path = "%s/bib/%s" % (app.config['WHELK_HOST'], rec_id)
    response = requests.put(path, data=json_string, headers=h, allow_redirects=True)
    if response.status_code == 200:
        storage.delete_draft(current_user.get_id(), "bib", rec_id)
        resp = raw_json_response(response.text)
        resp.headers['etag'] = response.headers['etag'].replace('"', '')
        return resp
    else:
        abort(response.status_code)

@app.route('/record/bib/create', methods=['POST'])
@login_required
def create_record():
    h = {'content-type': JSON_LD_MIME_TYPE, 'format': 'jsonld'}
    path = "%s/bib/" % (app.config['WHELK_HOST'])
    response = requests.post(path, data=json.dumps(request.json), headers=h, allow_redirects=False)
    if response.status_code == 200:
        resp = raw_json_response(response.text)
        resp.headers['etag'] = response.headers['etag'].replace('"', '')
        return resp
    elif response.status_code == 303:
        data = {}
        data['document'] = json.loads(response.text)
        data['document_id'] = urlparse(response.headers['Location']).path.rsplit("/")[-1]
        resp = raw_json_response(json.dumps(data))
        resp.headers['etag'] = response.headers['etag'].replace('"', '')
        return resp
    else:
        abort(response.status_code)

@app.route('/marcmap.json')
@login_required
def get_marcmap():
    with open(app.config['MARC_MAP']) as f:
        return raw_json_response(f.read())


@app.route('/suggest/auth')
@login_required
def suggest_auth_completions():
    q = request.args.get('q')
    response = requests.get("%s/person/_search?q=%s" % (app.config['WHELK_HOST'], q))
    if response.status_code >= 400:
        abort(response.status_code)
    return raw_json_response(response.text)

@app.route('/suggest/subject')
@login_required
def suggest_subject_completions():
    q = request.args.get('q')
    response = requests.get("%s/concept/_search?q=%s" % (app.config['WHELK_HOST'], q))
    if response.status_code >= 400:
        abort(response.status_code)
    return raw_json_response(response.text)

@app.route("/partials/<name>")
@login_required
def show_partial(name):
    return render_template('partials/%s.html' % name)


def raw_json_response(s):
    resp = make_response(s)
    resp.headers['Content-Type'] = 'application/json'
    resp.headers['Expires'] = '-1'
    return resp


jinja2.filters.FILTERS['chunk_number'] = chunk_number


if __name__ == "__main__":
    from optparse import OptionParser
    oparser = OptionParser()
    oparser.add_option('-d', '--debug', action='store_true', default=False)
    oparser.add_option('-L', '--fakelogin', action='store_true', default=False)
    oparser.add_option('-m', '--marcmap', type=str, default="marcmap.json")
    opts, args = oparser.parse_args()
    app.debug = opts.debug
    app.fakelogin = opts.fakelogin
    app.config['MARC_MAP'] = opts.marcmap
    app.run(host='0.0.0.0')

