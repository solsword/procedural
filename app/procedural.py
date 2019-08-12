#!/usr/bin/env python3
"""
procedural.py

Flask WSGI app that serves Parson's puzzles and records who has solved which
puzzles using CAS logins.
"""

import flask
import flask_cas
import flask_talisman
import sqlite3

app = flask.Flask(__name__)
flask_talisman.Talisman(app) # force HTTPS
cas = flask_cas.CAS(app, '/cas') # enable CAS
# Wellesley College login config:
app.config["CAS_SERVER"] = "https://login.wellesley.edu:443"
app.config["CAS_LOGIN_ROUTE"] = "/module.php/casserver/cas.php/login"
app.config["CAS_LOGOUT_ROUTE"] = "/module.php/casserver/cas.php/logout"
#app.config["CAS_VALIDATE_ROUTE"] = "/module.php/casserver/serviceValidate.php"
app.config["CAS_AFTER_LOGIN"] = "route_root"

# Set secret key from secret file:
with open("secret", 'rb') as fin:
  app.secret_key = fin.read()

# Redirect from http to https:
# TODO: Test in production whether this is necessary given Talisman...
#@app.before_request
#def https_redirect():
#  print("REQ: " + str(flask.request.url))
#  if not flask.request.is_secure:
#    url = flask.request.url.replace('http://', 'https://', 1)
#    code = 301
#    return flask.redirect(url, code=code)

@app.route('/')
@flask_cas.login_required
def route_root():
  return flask.render_template(
    "main.html",
    username=cas.username
  )

@app.route('/test')
def route_test():
  return flask.render_template(
    "main.html",
    username='test'
  )

@app.route("/puzzle")
def route_puzzle():
  """
  This route returns JSON puzzles.

  TODO: Not always the same one...
  """
  return { # default puzzle:
    "code": [
      "a = 3",
      "b = 4",
      "c = a*b",
      "a += 5",
      "b = a + 1",
      "c = c + a"
    ],
    "tests": [
      ['a', '8'], # note: both sides will be evaluated
      ['b', '9'],
      ['c', '20'],
    ]
  }

if __name__ == "__main__":
  #app.debug = True
  app.run('localhost', 1947, ssl_context=('cert.pem', 'key.pem'))
  #app.run('localhost', 1947)
