#!/usr/bin/env python
"""
list.py

Lists items from solutions table of the solutions.sqlite3 database in TSV
format. If command-line arguments are given, lists just solutions for those
users.

The '-s' or '--short' flag may be given to just list username, timestamp, and
puzzle id instead of the full username, timestamp, solution, and puzzle.

The '-p' or '--puzzles' flag may be given to treat command-line arguments as a
list of puzzle IDs instead of a list of usernames to filter by.
"""

import sys
import csv
import json
import sqlite3

import procedural

USAGE = """\
list.py -h|--help
list.py [-s|--short] [-p|--puzzles] [IDs...]

Lists submissions that match one of the given user IDs (or puzzle IDs if
-p/--puzzles is given). If -s/--short is given, it omits the actual solutions
and puzzles and just lists user IDs, timestamps, and puzzle IDs. If no
user/puzzle ID is given, it lists all submissions.
"""

if '-h' in sys.argv or '--help' in sys.argv:
  print(USAGE)
  exit()

conn = procedural.get_sol_db_connection()

short = False
if '-s' in sys.argv or '--short' in sys.argv:
  try:
    sys.argv.remove('-s')
  except:
    pass
  try:
    sys.argv.remove('--short')
  except:
    pass
  short = True

puzzles = False
if '-p' in sys.argv or '--puzzles' in sys.argv:
  try:
    sys.argv.remove('-p')
  except:
    pass
  try:
    sys.argv.remove('--puzzles')
  except:
    pass
  puzzles = True


if sys.argv[1:]:
  users = sys.argv[1:]
else:
  users = None

rows = []
results = []

if users:
  if puzzles:
    for puzzle in users:
      cur = conn.execute(
        "SELECT * FROM solutions WHERE puzzle_id = ?;",
        (puzzle,)
      )
      results.extend(list(cur.fetchall()))
  else:
    for user in users:
      cur = conn.execute("SELECT * FROM solutions WHERE username = ?;", (user,))
      results.extend(list(cur.fetchall()))
else:
  cur = conn.execute("SELECT * FROM solutions;")
  results = cur.fetchall()

for r in results:
  rows.append(
    (
      r["username"],
      r["timestamp"],
      r["puzzle_id"],
      r["solution"],
      r["puzzle"]
    )
  )

writer = csv.writer(sys.stdout, dialect='excel-tab')
if short:
  writer.writerow(('username', 'timestamp', 'puzzle_id'))
else:
  writer.writerow(('username', 'timestamp', 'puzzle_id', 'solution', 'puzzle'))
for row in rows:
  if short:
    writer.writerow(row[:3])
  else:
    writer.writerow(row)
