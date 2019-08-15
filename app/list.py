#!/usr/bin/env python3
"""
list.py

Lists items from solutions table of the solutions.sqlite3 database in TSV
format. If command-line arguments are given, lists just solutions for those
users. The '-s' or '--short' flag may be given to just list username,
timestamp, and puzzle id instead of the full username, timestamp, solution, and
puzzle.
"""

import sys
import csv
import json
import sqlite3

conn = sqlite3.connect("solutions.sqlite3")
conn.row_factory = sqlite3.Row # return results as Row objects


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

if sys.argv[1:]:
  users = sys.argv[1:]
else:
  users = None

rows = []

if users:
  for user in users:
    cur = conn.execute("SELECT * FROM solutions WHERE username = ?;", (user,))
    results = cur.fetchall()
    for r in results:
      rows.append((r["username"], r["timestamp"], r["solution"], r["puzzle"]))
else:
  cur = conn.execute("SELECT * FROM solutions;")
  results = cur.fetchall()
  for r in results:
    rows.append((r["username"], r["timestamp"], r["solution"], r["puzzle"]))

writer = csv.writer(sys.stdout, dialect='excel-tab')
if short:
  writer.writerow(('username', 'timestamp', 'puzzle_id'))
else:
  writer.writerow(('username', 'timestamp', 'solution', 'puzzle'))
for row in rows:
  if short:
    puzzle = json.loads(row[3])
    writer.writerow((row[0], row[1], puzzle["id"]))
  else:
    writer.writerow(row)
