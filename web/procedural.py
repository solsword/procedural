"""
procedural.py

Parson's puzzles widget, using Brython to work with Python code.
"""

# Built-in imports
import re
import random
import sys
import traceback

# Brython imports
import browser
from browser import document, window
import browser.ajax

#-------------#
# Scaffolding #
#-------------#

def error(*messages):
  """
  Reports an error by logging it to the console (as an error if possible).
  """
  if hasattr(browser.console, "error"):
    browser.console.error(*messages)
  else:
    browser.console.log("ERROR:")
    browser.console.log(*messages)

def log(*messages):
  """
  Logs a message to the console.
  """
  browser.console.log(*messages)

def has_class(elt, *classes):
  """
  Returns True if the given DOM element has (any of) the given class(es).
  """
  if not hasattr(elt, "classList"):
    return False
  return any(elt.classList.contains(x) for x in classes)

def add_class(elt, *classes):
  """
  Adds (all of) the given class(es) to the given DOM element.
  """
  for cl in classes:
    elt.classList.add(cl)

def remove_class(elt, *classes):
  """
  Removes (all of) the given class(es) from the given DOM element.
  """
  for cl in classes:
    elt.classList.remove(cl)

#---------------#
# Drag handlers #
#---------------#

# global reference to DOM element being dragged
DRAGGED = None

# Collection of event handlers for dragging & dropping code blocks
def drag_start(ev):
  """
  Handles the drag start event, which happens when the mouse is moved with the
  button held down. The element under the cursor becomes the event's target.
  """
  global DRAGGED
  if not has_class(ev.target, "code_block"):
    ev.preventDefault()
    return False

  DRAGGED = ev.target
  DRAGGED.style.opacity = 0.6
  return False

def drag_end(ev):
  """
  Handles the drag end event, which happens when the drag ends without a drop.
  """
  global DRAGGED
  if DRAGGED != None:
    DRAGGED.style.opacity = "";
    DRAGGED = None
  ev.preventDefault()
  return False

def drag_enter(ev):
  """
  Handles the drag enter event, when during a drag the mouse is moved over a
  new element (the target).
  """
  global DRAGGED
  if not same_widget(ev.target, DRAGGED):
    return False
  if has_class(ev.target, "code_slot") or has_class(ev.target, "code_block"):
    ev.dataTransfer.dropEffect = "move"
    add_class(ev.target, "hovered")

def drag_leave(ev):
  """
  Handles the drag leave event, when during a drag the mouse is moved off of an
  element (the target) that it was previously over.
  """
  global DRAGGED
  if not same_widget(ev.target, DRAGGED):
    return False
  if has_class(ev.target, "code_slot") or has_class(ev.target, "code_block"):
    ev.dataTransfer.dropEffect = "none"
    remove_class(ev.target, "hovered")

def drag_over(ev):
  """
  Handles the drag over event, which fires repeatedly while an element is being
  dragged over another element (the target). Preventing the default allows
  dropping.
  """
  ev.preventDefault()
  return False

def drag_drop(ev):
  """
  Handles the drag drop event, when during a drag the mouse is released over an
  element (the target).
  """
  global DRAGGED
  if not same_widget(ev.target, DRAGGED):
    ev.preventDefault()
    return False
  is_block = has_class(ev.target, "code_block")
  if has_class(ev.target, "code_slot") or is_block:
    # drop on a slot: insert ourselves after the slot
    slot = ev.target
    block = DRAGGED
    if slot == block: # drop on ourselves: do nothing
      ev.preventDefault()
      remove_class(slot, "hovered")
      return
    if is_block:
      before = block.previousSibling
    block.parentNode.removeChild(block);
    if is_block and slot == before:
      # if we're dropping on a block and it's the block above us, we should
      # swap places instead of going nowhere:
      slot.parentNode.insertBefore(block, before)
    else:
      # otherwise just add ourselves after the target:
      slot.parentNode.insertBefore(block, slot.nextSibling)
    # Note: it's ok if nextSibling is None because insertBefore defaults to
    # append if the second argument is None.
    # now clean up classes:
    remove_class(slot, "hovered")
  else:
    ev.preventDefault()

  # reset dragged element's style and then get rid of it:
  DRAGGED.style.opacity = "";
  DRAGGED = None

  return False

#--------------------------#
# DOM Management Functions #
#--------------------------#

def create_slot():
  """
  Creates a new empty slot div.
  """
  slot = document.createElement("div")
  add_class(slot, "code_slot")
  slot.innerHTML = "&nbsp;" # don't let it be completely empty
  return slot

def add_code_block_to_bucket(bucket, block):
  """
  Adds a block of code to a code block bucket. Creates the requisite DOM
  element and translates from raw code to HTML specifics. The given bucket
  element should be a DOM element with the code_bucket class.
  """
  codeblock = document.createElement("div")
  add_class(codeblock, "code_block")
  codeblock.draggable = True
  codeblock.__code__ = block
  codeblock.innerHTML = block
  bucket.appendChild(codeblock)

def add_empty_slot_to_bucket(bucket):
  """
  Adds an empty slot to a code bucket (should be a DOM element with class
  code_bucket).
  """
  bucket.appendChild(create_slot())

def my_widget(node):
  """
  Figure out which widget a DOM node belongs to. Recursively asks parent DOM
  node until a node with __widget__ defined is found.
  """
  if hasattr(node, "__widget__"):
    return node.__widget__
  elif hasattr(node, "parentNode"):
    return my_widget(node.parentNode)
  else:
    return None

def same_widget(a, b):
  """
  Generic function for asking if two elements belong to the same widget or not.
  Just uses my_widget on each and compares results.
  """
  # TODO: check that this isn't vulnerable to collisions?
  #mwa = my_widget(a)
  #mwb = my_widget(b)
  #log(dir(mwa), dir(mwb), id(mwa), id(mwb), mwa == mwb)
  return id(my_widget(a)) == id(my_widget(b))

#----------------------#
# Evaluation Functions #
#----------------------#

def exec_code(code, env=None):
  """
  Executes the given code block in the given environment (globals, locals
  tuple), modifying that environment. It returns the modified environment (or a
  newly-constructed environment if no environment was given).
  """
  if env == None:
    env = ({}, {}) # create a new object

  exec(code, globals=env[0], locals=env[1])

  return env

#-----------------#
# Setup functions #
#-----------------#

def setup_widget(node, puzzle=None):
  """
  Sets up a widget as a Parson's puzzle. First argument should be a DOM div and
  second should be a puzzle object with the following keys:
  
    code:
      A list of strings, each of which will be made into a draggable code
      block. If a single string is given instead, it will be split up into
      lines and each line will become a block (empty lines will be removed).
    tests:
      A list of strings, each of which must be a single expression that will
      evaluate to True after executing the puzzle code if the puzzle has been
      solved.
      TODO
    pretest (optional):
      A string of code to be executed before testing blocks.
      TODO
    goal (optional):
      An HTML string to be displayed to the user that describes the goal of the
      puzzle.
      TODO
    show_tests (optional; default True):
      True or False, whether the tests should be displayed to the user or not.
      TODO
  """
  # TODO: Use data- properties to define what kind of widget?
  if puzzle == None:
    if node.hasAttribute("data-puzzle"):
      try:
        puzzle = browser.window.JSON.parse(node.getAttribute("data-puzzle"))
      except Exception as e:
        error(
          "Malformed JSON in data-puzzle attribute:\n{}".format(
            node.getAttribute("data-puzzle")
          )
        )
        tbe = traceback.TracebackException(*sys.exc_info())
        error(''.join(tbe.format()))

  setup_base_puzzle(node, puzzle) # accepts None puzzle and defaults

  # Set up event handlers on this widget
  node.addEventListener("dragstart", drag_start, False);
  node.addEventListener("dragend", drag_end, False);
  node.addEventListener("dragover", drag_over, False);
  node.addEventListener("dragenter", drag_enter, False);
  node.addEventListener("dragenter", drag_enter, False);
  node.addEventListener("dragleave", drag_leave, False);
  node.addEventListener("drop", drag_drop, False);

def blocks_from_lines(code):
  """
  Takes a multiline string of code and returns a list of strings, where blank
  lines have been removed and the rest preserved.
  """
  return list(
    filter(
      lambda x: len(x) > 0 and not x.isspace(),
      code.split('\n')
    )
  )


def eval_button_handler(ev):
  """
  Click handler for the evaluate button of a puzzle.
  """
  bucket = ev.target.__bucket__
  code = "";
  for child in bucket.children:
    if child.hasOwnProperty("__code__"):
      code += child.__code__ + '\n'
  log("Code:\n{}".format(code))
  try:
    env = exec_code(code)
  # TODO: handle syntax errors separately?
  #except SyntaxError as se:
  except Exception as e:
    tbe = traceback.TracebackException(*sys.exc_info())
    log("Result was an exception:\n" + ''.join(tbe.format()))
    block = block_responsible_for(bucket, tbe)
    add_class(block, "error")

    err = document.createElement("div")
    err.innerHTML = list(tbe.format())[-1].strip()
    block.appendChild(err)

def block_responsible_for(bucket, tbe):
  """
  Figures out which block of code in a bucket was responsible for the given
  traceback by counting code lines and looking at the traceback's final line
  number.
  """
  line = tbe.stack[-1].lineno
  sofar = 0
  for child in bucket.children:
    if child.hasOwnProperty("__code__"):
      lines = len(child.__code__.split('\n'))
      if sofar + lines >= line:
        return child
      else:
        sofar += lines
  error("Ran out of code lines trying to find responsible block!")
  error(
    "children: {}, lines: {}, target: {}".format(
      len(bucket.children),
      sofar,
      line
    )
  )
  return None

def setup_base_puzzle(node, puzzle):
  """
  Sets up a basic two-column puzzle where you drag blocks from the left into
  numbered slots on the right.
  """
  if puzzle == None:
    puzzle = { # default puzzle:
      "code": [
        "a = 3;",
        "b = 4;",
        "c = a*b;",
        "a += 5",
        "b = a + 1;",
        "c = c + a;"
      ],
      "pretest": "",
      "tests": [ "a == 8", "b == 9", "c == 20" ],
      "goal": "Rearrange the code so that all of the tests are satisfied.",
      "show_tests": True
    }
  w = { "puzzle": puzzle } # the widget object
  node.__widget__ = w # attach it to the DOM

  code_blocks = puzzle["code"]
  if isinstance(code_blocks, str):
    code_blocks = blocks_from_lines(code_blocks)

  w["code_blocks"] = code_blocks

  # bucket for source blocks
  w["source_bucket"] = document.createElement("div");
  add_class(w["source_bucket"], "code_bucket", "code_source")
  node.appendChild(w["source_bucket"])

  # Shuffle the code blocks
  # TODO: random seeding?
  seed = puzzle["seed"] if "seed" in puzzle else 1712873
  random.seed(seed)
  random.shuffle(code_blocks)

  # First add a source slot so that we can drag things back if it's empty:
  add_empty_slot_to_bucket(w["source_bucket"])

  # Add each code block to our source div:
  for block in code_blocks:
    add_code_block_to_bucket(w["source_bucket"], block)

  # bucket for solution blocks
  w["soln_bucket"] = document.createElement("div")
  add_class(w["soln_bucket"], "code_bucket", "soln_list")
  node.appendChild(w["soln_bucket"]);

  # Create the answer slot:
  add_empty_slot_to_bucket(w["soln_bucket"])

  # Create evaluate button in solution bucket:
  eb = document.createElement("input");
  eb.type = "button";
  eb.value = "evaluate";
  eb.__bucket__ = w["soln_bucket"];
  eb.addEventListener("click", eval_button_handler)
  w["soln_bucket"].appendChild(eb);


def sequence_puzzles(widget, puzzles):
  """
  Takes a list of puzzle objects and presents them one at a time through the
  given widget, displaying a new puzzle when the current one is solved.
  """
  #log(puzzles[0]);
  setup_widget(widget, puzzles[0]);
  # TODO: HERE

def load_puzzles(url, continuation):
  """
  Loads the given URL (a relative URL) and parses a JSON array of objects which
  each define a puzzle. Passes the resulting array to the given continuation
  function when the loading is done.
  
  See:
  https://codepen.io/KryptoniteDove/post/load-json-file-locally-using-pure-javascript

  Note that with Chrome --allow-file-access-from-files will be necessary if not
  being hosted by a server.
  """
  # TODO: this?!?
  #xobj = browser.ajax.Ajax()
  #xobj.overrideMimeType("application/json");
  base = window.location.href;
  path = '/'.join(base.split('/')[:-1])
  dpath = path + "/" + url;

  # Load asynchronously
  def catch(req):
    if req.status == 200 or (req.status == 0 and dpath.startswith("file://")):
      try:
        # Using Python's json module here is horrifically slow
        obj = browser.window.JSON.parse(req.text)
      except Exception as e:
        error("Malformed JSON from '{}':\n{}".format(dpath, req.text))
        tbe = traceback.TracebackException(*sys.exc_info())
        error(''.join(tbe.format()))
        return
      # Call our callback and we're done
      continuation(obj)
    else:
      error("Failed to load puzzles from: '" + dpath + "'")
      error("(XMLHTTP request failed with status {})".format(req.stats))
      return

  try:
    browser.ajax.get(dpath, oncomplete=catch)
  except Exception as e:
    error("Failed to load puzzles from: '" + dpath + "'")
    error("(XMLHTTP request raised error)")
    tbe = traceback.TracebackException(*sys.exc_info())
    error(''.join(tbe.format()))

def init():
  """
  Selects all procedural_widget divs and creates elements inside each one to
  play a Parson's puzzle.
  """

  # Collect each widget:
  widgets = document.querySelectorAll(".procedural_widget");

  # Set up each widget automatically:
  #for widget in widgets:
  #  setup_widget(widget)

  # Sequence loaded puzzles into the first widget:
  first = widgets[0]
  load_puzzles(
    "puzzles.json",
    lambda puzzles: sequence_puzzles(first, puzzles)
  )

  # Testing: set up second and third widgets as default:
  setup_widget(widgets[1])
  setup_widget(widgets[2])
  # TODO: implement data-puzzle-source and plural puzzles

# Initialize when this script is run:
init()
