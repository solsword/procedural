#!/usr/bin/env python3
"""
procedural.py

Flask WSGI app that serves Parson's puzzles and records who has solved which
puzzles using CAS logins.
"""

import flask
import flask_cas
#import flask_talisman
import werkzeug

import os
import sys
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

# Solutions database filename
SOL_DATABASE = "solutions.sqlite3"

# Permissions database filename
PERM_DATABASE = "permissions.sqlite3"

# Database schema
SOL_SCHEMA = """
CREATE TABLE solutions (
  username TEXT NOT NULL,
  timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
  puzzle_id TEXT,
  solution TEXT,
  puzzle TEXT
);
"""

PERM_SCHEMA = """
CREATE TABLE permissions (
  username TEXT UNIQUE NOT NULL,
  is_admin TEXT,
  permissions TEXT
);
"""


#-------------------------#
# Setup and Configuration #
#-------------------------#

app = flask.Flask(__name__)
#flask_talisman.Talisman(app, content_security_policy=CSP) # force HTTPS
cas = flask_cas.CAS(app, '/cas') # enable CAS

app.config.from_object('config')
app.config["DEBUG"] = False

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

#-------------------#
# Custom Decorators #
#-------------------#

def returnJSON(f):
  """
  Wraps a function so that returned objects are dumped to JSON strings before
  being passed further outwards. 
  """
  def wrapped(*args, **kwargs):
    r = f(*args, **kwargs)
    return json.dumps(r)

  wrapped.__name__ = f.__name__
  return wrapped

def admin_only(f):
  """
  Wraps a function so that it first checks the CAS username against the
  permissions database and retursn 403 (forbidden) if the user isn't set up as
  an admin.
  """
  def wrapped(*args, **kwargs):
    username = flask.session.get("CAS_USERNAME", None)
    if username == None:
      return ("Unregistered user.", 403)
    else:
      if not is_admin(username):
        return ("You must be an administrator to access this page.", 403)
      else:
        return f(*args, **kwargs)

  wrapped.__name__ = f.__name__
  return wrapped

#---------------#
# Server Routes #
#---------------#

@flask_cas.login_required
@app.route('/')
def route_root():
  return flask.render_template(
    "main.html",
    username=cas.username
  )

@app.route('/test')
@admin_only
def route_test():
  return flask.render_template(
    "main.html",
    username='test'
  )

@app.route("/categories")
def route_categories():
  """
  This route returns JSON for the categories from the CATEGORIES_FILE.
  """
  with open(app.config.get("CATEGORIES_FILE", "categories.json"), 'r') as fin:
    return fin.read()

@app.route("/puzzle", methods=["GET", "POST"])
def route_puzzle():
  """
  This route returns JSON puzzles from the PUZZLES_DIRECTORY.
  """
  id = flask.request.form.get("id", None)
  if id == None:
    return { # default puzzle:
      "id": "default_server_puzzle",
      "name": "Default Server Puzzle",
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
  else:
    id = werkzeug.utils.secure_filename(id)
    if '.' in id:
      return ("Invalid puzzle ID: '{}'".format(id), 400)
    user = flask.session.get("CAS_USERNAME", None)
    if has_permission(user, "view_puzzle", id):
      bits = id.split('-')
      pdir = app.config.get("PUZZLES_DIRECTORY", "puzzles")
      target = os.path.join(pdir, *bits) + ".json"
      if os.path.exists(target):
        with open(target, 'r') as fin:
          puzzle = fin.read()
        return puzzle
      else:
        return ("Puzzle '{}' does not exist.".format(id), 404)
    else:
      return ("You don't have permissions to view puzzle '{}'.".format(id), 403)

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
  conn = get_sol_db_connection()
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
  conn.close()
  return True

def all_solutions_by(username):
  """
  Retrieves from the database a list of all solutions by the given user. The
  return value is a list of sqlie3 Row objects.
  """
  conn = get_sol_db_connection()
  cur = conn.execute("SELECT * FROM solutions WHERE username = ?;", (username,))
  result = list(cur.fetchall())
  conn.close()
  return result

def all_solutions_to(puzzle_id):
  """
  Retrieves from the database a list of all solutions to the given puzzle. The
  return value is a list of sqlie3 Row objects.
  """
  conn = get_sol_db_connection()
  cur = conn.execute(
    "SELECT * FROM solutions WHERE puzzle_id = ?;",
    (puzzle_id,)
  )
  result = list(cur.fetchall())
  conn.close()
  return result

def is_admin(user_id):
  """
  Retrieves a user's admin status from the permissions database.
  """
  conn = get_perm_db_connection()
  cur = conn.execute(
    "SELECT is_admin FROM permissions WHERE username = ?;",
    (user_id,)
  )
  results = list(cur.fetchall())
  conn.close()

  return (
    len(results) > 0
and results[0][0] == "True"
  )

def get_permisisons(user_id):
  """
  Retrieves a user's permissions object from the permissions database. Returns
  None for unlisted users.
  """
  conn = get_perm_db_connection()
  cur = conn.execute(
    "SELECT permissions FROM permissions WHERE username = ?;",
    (user_id,)
  )
  results = list(cur.fetchall())
  conn.close()
  if len(results) <= 0:
    return None
  else:
    try:
      return json.loads(results[0][0])
    except:
      print(
        "Warning: error fetching or parsing permissions for  user '{}'".format(
          user_id
        )
      )
      return None

def set_permissions(user_id, perm_obj):
  """
  Resets a user's permissions entirely. Adds a non-admin entry to the
  permissions database if necessary. Returns True if it succeeds or False if it
  fails.
  """

  try:
    perm_string = json.dumps(perm_obj)
  except:
    print(
      (
        "Warning: user permissions not set for '{}' because object couldn't "
      + "be serialized:\n{}"
      ).format(user_id, repr(perm_obj))
    )
    return False

  conn = get_perm_db_connection()
  cur = conn.execute(
    "SELECT * FROM permissions WHERE username = ?;",
    (user_id,)
  )
  if len(list(cur.fetchall())) > 0: # user already exists
    conn.execute(
      "UPDATE permissions SET permissions = ? WHERE username = ?;",
      (perm_string, user_id,)
    )
    conn.commit()
  else: # new user
    conn.execute(
      "INSERT INTO permissions VALUES (?, ?, ?);",
      (user_id, 'False', perm_string)
    )
    conn.commit()
  conn.close()
  return True

def grant_permission(user_id, action, item):
  """
  Adds permission for the given user to take the given action. Returns True if
  it succeeds and False if it fails.
  """
  perms = get_permisisons(user_id)
  if perms == None:
    print(
      (
        "Warning: permission {}:{} not added for '{}' because of trouble "
      + "retrieving permissions for that user."
      ).format(action, item, user_id)
    )
    return False

  if action not in perms:
    perms[action] = { item: True }
  else:
    perms[action][item] = True

  # Update permissions object in the database
  return set_permissions(user_id, perms)

def revoke_permission(user_id, action, item):
  """
  Revokes permission for the given user to take the given action.
  """
  perms = get_permisisons(user_id)
  if perms == None:
    print(
      (
        "Warning: permission {}:{} not revoked for '{}' because of trouble "
      + "retrieving permissions for that user."
      ).format(action, item, user_id)
    )
    return False

  if action not in perms:
    return # already didn't have it
  else:
    del perms[action][item]

  # Update permissions object in the database
  return set_permissions(user_id, perms)


def has_permission(user_id, action, item):
  """
  Retrieves a user's permissions object from the permissions database, and
  checks whether the user has permission to perform the given action on the
  given item. Returns True or False. Admin accounts have permission to do
  everything, and if the user_id is None, it always returns False.
  """
  if user_id != None:
    conn = get_perm_db_connection()
    cur = conn.execute(
      "SELECT permissions, is_admin FROM permissions WHERE username = ?;",
      (user_id,)
    )
    results = list(cur.fetchall())
    conn.close()
    if len(results) >= 1:
      is_admin = results[0][1] == "True"
      try:
        perm_obj = json.loads(results[0][0])
      except:
        print(
          "Warning: error parsing permissions for user '{}'".format(user_id)
        )
        perm_obj = None
  
      if (
        is_admin # can do anything
     or (perm_obj and action in perm_obj and perm_obj[action].get(item, False))
      ):
        return True
  
  # If we fall out, check global permissions
  conn = get_perm_db_connection()
  cur = conn.execute(
    'SELECT permissions FROM permissions WHERE username = "__all__";'
  )
  results = list(cur.fetchall())
  conn.close()
  if len(results) > 0:
    try:
      perm_obj = json.loads(results[0][0])
    except:
      print(
        "Warning: error parsing permissions for '__all__':\n{}".format(
          results[0][0]
        )
      )
      perm_obj = None

    return (
      perm_obj != None
  and action in perm_obj
  and perm_obj[action].get(item, False)
    )

  return False

def set_admin(user_id, admin='True'):
  """
  Sets the 'admin' property of the given user, by default making them an admin.
  Any value besides 'True' will be treated as a regular user. Prints a warning
  message and returns False if the given user doesn't already exist.
  """
  conn = get_perm_db_connection()
  # Check if the user already exists: 
  cur = conn.execute(
    "SELECT * FROM permissions WHERE username = ?;",
    (user_id,)
  )
  if len(list(cur.fetchall())) == 0: # user doesn't exists
    print(
      "Attempt to set admin status of non-existent user '{}'.".format(user_id)
    )
    conn.close()
    return False
  else:
    conn.execute(
      "UPDATE permissions SET is_admin = ? WHERE username = ?;",
      (admin, user_id)
    )
    conn.commit()

  conn.close()
  return True

def add_user(user_id, is_admin='False'):
  """
  Adds the given user to the permissions database. Set is_admin to the string
  'True' to make the user an administrator. Prints a warning and returns False
  if the user already exists.
  """
  conn = get_perm_db_connection()
  # Check if the user already exists: 
  cur = conn.execute(
    "SELECT * FROM permissions WHERE username = ?;",
    (user_id,)
  )
  results = list(cur.fetchall())
  conn.close()
  if len(results) > 0: # user already exists
    print(
      "Attempt to create user '{}' who already exists.".format(user_id)
    )
    return False
  else:
    if not set_permissions(user_id, {}): # creates user automatically
      return False
    if is_admin != 'False': # that's the default in set_permissions
      if not set_admin(user_id, is_admin):
        return False

  return True

def get_sol_db_connection():
  """
  Gets a connection to the solutions database.
  """
  conn = sqlite3.connect(SOL_DATABASE)
  conn.row_factory = sqlite3.Row # return results as Row objects
  return conn

def get_perm_db_connection():
  """
  Gets a connection to the permissions database.
  """
  conn = sqlite3.connect(PERM_DATABASE)
  conn.row_factory = sqlite3.Row # return results as Row objects
  return conn

#--------------#
# Startup Code #
#--------------#

if __name__ == "__main__":
  # Set up databases if they doesn't already exist:
  if not os.path.exists(SOL_DATABASE):
    conn = get_sol_db_connection()
    conn.execute(SOL_SCHEMA)
    conn.commit()
    conn.close()
  if not os.path.exists(PERM_DATABASE):
    conn = get_perm_db_connection()
    conn.execute(PERM_SCHEMA)
    conn.commit()
    conn.close()
  #app.run('localhost', 1947, ssl_context=('cert.pem', 'key.pem'))
  #app.run('0.0.0.0', 1947, ssl_context=('cert.pem', 'key.pem'))
  app.run('localhost', 1947)
