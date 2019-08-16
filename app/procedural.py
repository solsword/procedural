#!/usr/bin/env python3
"""
procedural.py

Flask WSGI app that serves Parson's puzzles and records who has solved which
puzzles using CAS logins.
"""

import flask
import flask_cas
import flask_talisman

import os
import json
import sqlite3
import traceback

#------------------#
# Global Variables #
#------------------#

# content security policy
CSP = {
  'default-src': [
    "https:",
    "'self'",
  ],
  'script-src': [
    "https:",
    "'self'",
    "'unsafe-inline'",
    "'unsafe-eval'",
  ],
}

# Database filename
DATABASE = "solutions.sqlite3"

# Database schema
SCHEMA = """
CREATE TABLE solutions (
  username TEXT NOT NULL,
  timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
  puzzle_id TEXT,
  solution TEXT,
  puzzle TEXT
);
"""

#-------------------------#
# Setup and Configuration #
#-------------------------#

app = flask.Flask(__name__)
flask_talisman.Talisman(app, content_security_policy=CSP) # force HTTPS
cas = flask_cas.CAS(app, '/cas') # enable CAS
# Wellesley College login config:
app.config["CAS_SERVER"] = "https://login.wellesley.edu:443"
app.config["CAS_LOGIN_ROUTE"] = "/module.php/casserver/cas.php/login"
app.config["CAS_LOGOUT_ROUTE"] = "/module.php/casserver/cas.php/logout"
app.config["CAS_VALIDATE_ROUTE"] = "/module.php/casserver/serviceValidate.php"
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

#------------#
# Fake Login #
#------------#

def fake_login(f):
  def wrapped(*args, **kwargs):
    if 'CAS_USERNAME' not in flask.session:
      flask.flash("You must log in first.")
      return flask.redirect(
        flask.url_for("route_login", next=flask.request.url)
      )
    else:
      return f(*args, **kwargs)
  return wrapped

@app.route('/login')
def route_login():
  next = flask.request.args.get("next", flask.url_for("route_root"))
  flask.session["CAS_USERNAME"] = "LOGGED IN"
  return flask.redirect(next)

#---------------#
# Server Routes #
#---------------#

# TODO: real login!
#@flask_cas.login_required
@fake_login
@app.route('/')
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

def returnJSON(f):
  """
  Wraps a function so that returned objects are dumped to JSON strings before
  being passed further outwards. 
  """
  def wrapped(*args, **kwargs):
    r = f(*args, **kwargs)
    return json.dumps(r)
  return wrapped

@app.route("/solved", methods=["POST"])
@returnJSON
def route_solved():
  """
  POST route that accepts and records puzzle solutions. The requests must have
  "puzzle" and "solution" fields which contain valid JSON strings, and the user
  must be logged in when submitting the request.
  """
  if "CAS_USERNAME" not in flask.session:
    return { "status": "invalid", "reason": "not logged in" }

  # Get puzzle object from request:
  puzzle = flask.request.form.get("puzzle", None)
  if puzzle == None:
    return { "status": "invalid", "reason": "no puzzle sent" }

  # Parse puzzle from JSON:
  try:
    puzzle = json.loads(puzzle)
  except:
    return { "status": "invalid", "reason": "invalid puzzle" }

  # Get solution object from request:
  solution = flask.request.form.get("solution", None)
  if solution == None:
    return { "status": "invalid", "reason": "no solution sent" }

  # Parse solution as JSON:
  try:
    solution = json.loads(solution)
  except:
    return { "status": "invalid", "reason": "invalid solution" }

  try:
    record_solution(flask.session["CAS_USERNAME"], puzzle, solution)
  except Exception as e:
    tbe = traceback.TracebackException.from_exception(e)
    print("Failed to save solution:\n" + '\n'.join(tbe.format()))
    return {
      "status": "invalid",
      "reason": "failed to save solution"
    }

  # TODO: Verify solutions at all?

  return { "status": "valid" }

#--------------------#
# Database Functions #
#--------------------#

def record_solution(username, puzzle, solution):
  """
  Records a solution in the database.
  """
  conn = get_db_connection()
  conn.execute(
    "INSERT INTO solutions VALUES (?, DATETIME('now'), ?, ?, ?);",
    (
      username,
      puzzle.get("id", "__unknown__"),
      json.dumps(puzzle),
      json.dumps(solution)
    )
  )
  conn.commit()

def all_solutions_by(username):
  """
  Retrieves from the database a list of all solutions by the given user. The
  return value is a list of sqlie3 Row objects.
  """
  conn = get_db_connection()
  cur = conn.execute("SELECT * FROM solutions WHERE username = ?;", (username,))
  return list(cur.fetchall())

def all_solutions_to(puzzle_id):
  """
  Retrieves from the database a list of all solutions to the given puzzle. The
  return value is a list of sqlie3 Row objects.
  """
  conn = get_db_connection()
  cur = conn.execute(
    "SELECT * FROM solutions WHERE puzzle_id = ?;",
    (puzzle_id,)
  )
  return list(cur.fetchall())

def get_db_connection():
  """
  Gets a connection to the database.
  """
  conn = sqlite3.connect(DATABASE)
  conn.row_factory = sqlite3.Row # return results as Row objects
  return conn

#--------------#
# Startup Code #
#--------------#

if __name__ == "__main__":
  # Set up database if it doesn't already exist:
  if not os.path.exists(DATABASE):
    conn = get_db_connection()
    conn.execute(SCHEMA)
  #app.debug = True
  #app.run('localhost', 1942, ssl_context=('cert.pem', 'key.pem'))
  app.run('0.0.0.0', 1947, ssl_context=('cert.pem', 'key.pem'))
  #app.run('localhost', 1947)
