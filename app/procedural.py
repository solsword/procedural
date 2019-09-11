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
import traceback
import datetime

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

# Default permissions
DEFAULT_PERMISSIONS = { "admins": [], "puzzles": {} }

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
  permissions file and returns 403 (forbidden) if the user isn't set up
  as an admin.
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
#@admin_only
def route_test():
  return flask.render_template(
    "test.html",
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
  puzzle_id = flask.request.form.get("id", None)
  if puzzle_id == None:
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
    puzzle_id = werkzeug.utils.secure_filename(puzzle_id)
    if '.' in puzzle_id:
      return ("Invalid puzzle ID: '{}'".format(puzzle_id), 400)
    user = flask.session.get("CAS_USERNAME", None)
    if has_permission(puzzle_id, user):
      bits = puzzle_id.split('-')
      pdir = app.config.get("PUZZLES_DIRECTORY", "puzzles")
      target = os.path.join(pdir, *bits) + ".json"
      if os.path.exists(target):
        with open(target, 'r') as fin:
          puzzle = fin.read()
        return puzzle
      else:
        return ("Puzzle '{}' does not exist.".format(puzzle_id), 404)
    else:
      return (
        "You don't have permissions to view puzzle '{}'.".format(
          puzzle_id
        ),
        403
      )

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
    result = record_solution(flask.session["CAS_USERNAME"], puzzle, solution)
    if result != True:
      return {
        "status": "invalid",
        "reason": "failed to save solution"
      }
  except Exception as e:
    if sys.version_info >= (3, 5):
      tbe = traceback.TracebackException.from_exception(e)
      print("Failed to save solution:\n" + '\n'.join(tbe.format()))
    else:
      print("Failed to save solution:")
      traceback.print_exception(*sys.exc_info())
    return {
      "status": "invalid",
      "reason": "failed to save solution (crashed)"
    }

  # TODO: Verify solutions at all?

  return { "status": "valid" }

#--------------------#
# Database Functions #
#--------------------#

def record_solution(username, puzzle, solution):
  """
  Records a solution in the solutions directory. Returns True if it
  succeeds and False if it fails.
  """
  # create solutions directory if necessary
  sd = app.config.get("SOLUTIONS_DIR", "submissions")
  try:
    if not os.path.exists(sd):
      os.mkdir(sd, 0o770)
  except Exception as e:
    print("Failed to create submissions directory '{}'.".format(sd))
    traceback.print_exception(*sys.exc_info())
    return False

  # create user directory if necessary
  ud = os.path.join(sd, username)
  try:
    if not os.path.exists(ud):
      os.mkdir(ud, 0o770)
  except Exception as e:
    print("Failed to create user subdirectory '{}'.".format(ud))
    traceback.print_exception(*sys.exc_info())
    return False

  # timestamp
  ts = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f")
  # full filename
  fn = "{}-solution:{}.json".format(
    puzzle.get("id", "__unknown__"),
    ts
  )
  # with path
  sf = os.path.join(ud, fn)

  # write the solution into a file
  try:
    with open(sf, 'w') as fout:
      json.dump({"puzzle": puzzle, "solution": solution}, fout)
  except Exception as e:
    print("Failed to write solution file '{}'.".format(sf))
    traceback.print_exception(*sys.exc_info())
    return False

  # we succeeded!
  return True

def all_solutions_by(username):
  """
  Retrieves from the solutions directory a list of all solutions by the
  given user. The return value is a list of full filenames.
  """
  sd = app.config.get("SOLUTIONS_DIR", "submissions")
  ud = os.path.join(sd, username)

  if not os.path.exists(ud):
    return []

  result = []
  for f in os.listdir(ud):
    ff = os.path.join(ud, f)
    if os.path.isfile(ff):
      result.append(ff)

  return result

def all_solutions_to(puzzle_id):
  """
  Scans solution files to list of all solutions to the given puzzle by
  any user. The return value is a list of pairs of username and
  submission filename (potentially with multiple files submitted per
  user).
  """
  result = []
  sd = app.config.get("SOLUTIONS_DIR", "submissions")
  if not os.path.exists(sd):
    return []

  # Loop over user directories
  for dirname in os.listdir(sd):
    ud = os.path.join(sd, dirname)
    if os.path.isdir(ud):
      # Loop over files for this user:
      # TODO: wildcard based on puzzle ID should be much faster?
      for filename in os.listdir(ud):
        ff = os.path.join(ud, filename)
        # check for submissions that match our puzzle ID:
        if os.path.isfile(ff) and "-solution:" in filename:
          fpid = filename[:filename.index("-solution:")]
          if fpid == puzzle_id:
            result.append((dirname, ff))

  return result

def is_admin(user_id):
  """
  Retrieves a user's admin status from the permissions file.
  """
  perms = get_current_permissions()
  return user_id in perms["admins"]

def get_permisisons(puzzle_id):
  """
  Retrieves a puzzle's permissions object from the permissions file.
  Returns None for unlisted puzzles.
  """
  perms = get_current_permissions()
  return perms["puzzles"].get(puzzle_id, None)

def set_permissions(puzzle_id, perm_obj):
  """
  Resets a puzzle's permissions entirely. Adds an entry to the
  permissions file if necessary. THIS OPERATION MODIFIES THE PERMISSIONS
  FILE, so be careful about not using it concurrently across multiple
  contexts. Returns True on success and False on failure.
  """
  perms = get_current_permissions()
  perms["puzzles"][puzzle_id] = perm_obj

  return safely_overwrite_permissions_file(perms)

def deny_permission(puzzle_id, user_id):
  """
  Adds an exception that prevents the given user from viewing the given
  puzzle. Returns True if it succeeds and False if it fails.
  """
  pzperms = get_permisisons(puzzle_id)
  if pzperms == None:
    # Create a new permissions object for this puzzle
    perms["puzzles"][puzzle_id] = { "allow": False, "deny": [ user_id ] }
  elif user_id in pzperms.get("deny", []):
    return True # already denied; no action requried
  else:
    # Add to deny list
    pzperms["deny"].append(user_id)

  return set_permissions(puzzle_id, pzperms)

def reinstate_permission(puzzle_id, user_id):
  """
  Removes the given user from the deny list for the given puzzle.
  """
  pzperms = get_permisisons(puzzle_id)
  if pzperms == None:
    return True # no work to be done, as puzzle doesn't have a deny list yet

  if user_id not in pzperms.get("deny", []):
    return True # no work to be done, wasn't on the deny list
  else:
    pzperms["deny"].remove(user_id)

  return set_permissions(puzzle_id, pzperms)


def has_permission(puzzle_id, user_id):
  """
  Retrieves a puzzle's permissions object from the permissions file, and
  checks whether the user has permission to view it. Returns True or
  False. Admin accounts have permission to view all puzzles, and if the
  user_id is None, it always returns False.
  """
  if is_admin(user_id):
    return True
  elif user_id == None:
    return False

  # Actually check puzzle permissions:
  pzperms = get_permisisons(puzzle_id)
  if pzperms == None:
    return False # no permissions for unknown puzzle
  allow = pzperms.get("allow", False)
  if allow == True:
    deny = pzperms.get("deny", [])
    return user_id not in deny
  elif isinstance(allow, list):
    return user_id in allow
  else: # allow is false or some other unexpected value
    return False

def set_admin(user_id, admin=True):
  """
  Promotes the user to an admin, if admin is True, or demotes them to a
  normal user, if admin is False. Returns True if it succeeds and False
  if it fails.
  """
  perms = get_current_permissions()
  if admin:
    if user_id not in perms["admins"]:
      perms["admins"].append(user_id)
      return safely_overwrite_permissions_file(perms)
    # otherwise don't need to do anything, user is already an admin
  else:
    if user_id in perms["admins"]:
      perms["admins"].remove(user_id)
      return safely_overwrite_permissions_file(perms)
    # otherwise don't need to do anything, user is already NOT an admin

def get_current_permissions():
  """
  Re-reads the permissions file to get up-to-date info on who is allowed
  to view which puzzles. Returns default permissions if trouble is
  encountered loading the permissions file.
  """
  pf = app.config.get("PERMISSIONS_FILE", "permissions.json")
  try:
    with open(pf, 'r') as fin:
      perms = json.load(fin)
    if "admins" not in perms:
      perms["admins"] = []
    if "puzzles" not in perms:
      perms["puzzles"] = {}
    return perms
  except Exception as e:
    if sys.version_info >= (3, 5):
      tbe = traceback.TracebackException.from_exception(e)
      print(
        "Error loading permissions from file '{}':\n".format(pf)
      + '\n'.join(tbe.format())
      )
    else:
      print("Error loading permissions from file '{}':".format(pf))
      traceback.print_exception(*sys.exc_info())
    return DEFAULT_PERMISSIONS

def safely_overwrite_permissions_file(perms):
  """
  Attempts to overwrite the permissions file with new permissions, but
  respects a simple file-based lock. Not really much safer than a raw
  write (there's still a potential race condition, for example), but
  offers at least a modicum of corruption protection.
  """
  pf = app.config.get("PERMISSIONS_FILE", "permissions.json")
  lf = pf + ".lock"
  if os.path.exists(lf):
    return False

  # Convert JSON -> string first to save time we need the lock for
  perms_string = json.dumps(perms, indent=2, separators=(',', ': '))

  try:
    with open(lf, 'w') as fout:
      fout.write("")
  except:
    print("Failed to create lock file '{}'.".format(lf))
    return False

  # here we "have" the lock (but of course there's a race condition above)
  try:
    with open(pf, 'w') as fout:
      fout.write(perms_string)
  except:
    print("Failed to write to permissions file '{}'.".format(pf))
    try:
      os.remove(lf)
    except:
      print("Failed to clean up lock file '{}'.".format(lf))
    return False

  try:
    os.remove(lf)
  except:
    print("Failed to clean up lock file '{}'.".format(lf))
    return False

  # We succeeded!
  return True


#--------------#
# Startup Code #
#--------------#

if __name__ == "__main__":
  #app.run('localhost', 1947, ssl_context=('cert.pem', 'key.pem'))
  #app.run('0.0.0.0', 1947, ssl_context=('cert.pem', 'key.pem'))
  app.run('localhost', 1947)
