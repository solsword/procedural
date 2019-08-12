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
import javascript

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

def trap_exception(ex):
  """
  Preserves an exception as a list of exception type, string message,
  integer line number, and for syntax errors, integer error position offset
  (other errors have None as their offset).
  """
  if isinstance(ex, SyntaxError):
    if type(ex) == SyntaxError:
      true_offset = len(traceback.format_exception_only(type(ex), ex)[-2]) - 2
    else:
      true_offset = ex.offset
    return [type(ex), ex.msg, ex.lineno, true_offset]
  else:
    if not hasattr(ex, "__traceback__"):
      tb = sys.exc_info()[2]
    else:
      tb = ex.__traceback__
    return [type(ex), str(ex), line_of(tb), None]

def format_error(error):
  """
  Formats a trapped exception from trap_exception. Returns a string.
  """
  error_type, error_msg, error_line, error_offset = error
  return "{}: {} (on line {})".format(
    error_type.__name__,
    error_msg,
    error_line
  )

def line_of(tb):
  """
  Returns the raw line number of the last frame of a traceback.
  """
  while (tb.tb_next != None):
    tb = tb.tb_next
  return tb.tb_lineno

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
  # okay to use this here because things inside aren't draggable, so event will
  # bubble to the code_block div, which is.
  if not has_class(ev.target, "code_block"):
    ev.preventDefault()
    return False

  DRAGGED = ev.target
  add_class(DRAGGED, "dragging")
  return False

def drag_end(ev):
  """
  Handles the drag end event, which happens when the drag ends without a drop.
  """
  global DRAGGED
  if DRAGGED != None:
    remove_class(DRAGGED, "dragging")
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

  if has_class(ev.target, "code_slot"):
    block = ev.target
  else:
    block = my_code_block(ev.target)

  if block != None and not block.isSameNode(DRAGGED):
    ev.dataTransfer.dropEffect = "move"
    add_class(block, "hovered")

def drag_leave(ev):
  """
  Handles the drag leave event, when during a drag the mouse is moved off of an
  element (the target) that it was previously over.
  """
  global DRAGGED

  if not same_widget(ev.target, DRAGGED):
    return False

  if has_class(ev.target, "code_slot"):
    block = ev.target
  else:
    block = my_code_block(ev.target)

  if block != None:
    # Block that we're leaving to:
    to_block = my_code_block(ev.relatedTarget)

    if not block.isSameNode(to_block):
      ev.dataTransfer.dropEffect = "none"
      remove_class(block, "hovered")

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
  my_block = my_code_block(ev.target)
  if has_class(ev.target, "code_slot") or my_block != None:
    # drop on a slot: insert ourselves after the slot
    slot = my_block or ev.target
    if slot.isSameNode(DRAGGED): # drop on ourselves: do nothing
      ev.preventDefault()
      remove_class(slot, "hovered")
      return
    if my_block != None:
      after = DRAGGED.nextSibling
    DRAGGED.parentNode.removeChild(DRAGGED)
    if my_block != None and slot.isSameNode(after):
      # if we're dropping on a block and it's the block below us, we should
      # swap places instead of going nowhere:
      slot.parentNode.insertBefore(DRAGGED, after.nextSibling)
    else:
      # otherwise just add ourselves before the target:
      slot.parentNode.insertBefore(DRAGGED, slot)
    # now clean up classes:
    remove_class(slot, "hovered")

    # Mark errors and tests on this widget as stale:
    w = my_widget(ev.target)
    mark_errors_as_stale(w)
    mark_tests_as_stale(w)

  elif has_class(ev.target, "code_bucket"):
    # drop on a bucket: add ourselves after the last code block in that bucket:
    last = None
    for child in ev.target.children:
      if has_class(child, "code_slot", "code_block"):
        last = child
    if last == None:
      DRAGGED.parentNode.removeChild(DRAGGED)
      ev.target.insertBefore(DRAGGED, ev.target.firstChild)
    else:
      DRAGGED.parentNode.removeChild(DRAGGED)
      ev.target.insertBefore(DRAGGED, last.nextSibling)

    # Mark errors on this widget as stale:
    w = my_widget(ev.target)
    mark_errors_as_stale(w)
    mark_tests_as_stale(w)

  else:
    ev.preventDefault()

  # reset dragged element's style and then get rid of it:
  remove_class(DRAGGED, "dragging")
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

def add_code_block_to_bucket(bucket, code):
  """
  Adds a block of code to a code block bucket. Creates the requisite DOM
  element and translates from raw code to HTML specifics. The given bucket
  element should be a DOM element with the code_bucket class.
  """
  codeblock = document.createElement("code")
  add_class(codeblock, "code_block")
  add_class(codeblock, "language-python")
  codeblock.draggable = True
  codeblock.__code__ = code
  codeblock.innerHTML = code
  # Note: this must be innerHTML, not innerText! (otherwise line breaks get
  # eaten)
  browser.window.Prism.highlightElement(codeblock)
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

def my_code_block(node):
  """
  Figure out which code block a DOM node belongs to. Recursively asks parent
  DOM node until a node with class code_block is found.
  """
  if has_class(node, "code_block"):
    return node
  elif hasattr(node, "parentNode"):
    return my_code_block(node.parentNode)
  else:
    return None

def same_widget(a, b):
  """
  Generic function for asking if two elements belong to the same widget or not.
  Just uses my_widget on each and compares results.
  """
  return my_widget(a) is my_widget(b)

#----------------------#
# Evaluation Functions #
#----------------------#

def exec_code(code, env=None):
  """
  Executes the given code block in the given environment (globals, locals
  tuple), modifying that environment. It returns the modified environment (or a
  newly-constructed environment if no environment was given).
  """
  # TODO: Why are exceptions horribly slow? Can we fix this?
  if env == None:
    env = ({}, {}) # create a new object

  exec(code, globals=env[0], locals=env[1])

  return env

def eval_button_handler(ev):
  """
  Click handler for the evaluate button of a puzzle. Evaluates the code, runs
  the tests, and reports results by updating test statuses and attaching error
  messages.
  """
  # TODO: activity indicator
  bucket = ev.target.__bucket__
  widget = my_widget(bucket)
  remove_errors(widget)
  mark_tests_as_fresh(widget)
  code = ""
  for child in bucket.children:
    if child.hasOwnProperty("__code__"):
      code += child.__code__ + '\n'
  code = code[:-1] # remove trailing newline
  log("Running code:\n---\n{}\n---".format(code))
  exception = None
  try:
    env = exec_code(code)
  except Exception as e:
    exception = trap_exception(e)
    log("Result was an exception:\n" + ''.join(format_error(exception)))
    attach_error_message(bucket, exception)
    env = ({}, {})

  # Now run the pre-test code
  pte = None
  if exception == None and "pretest" in widget["puzzle"]:
    try:
      env = exec_code(widget["puzzle"]["pretest"], env)
    except Exception as e:
      # An exception here is neither recoverable nor reportable. Be careful
      # with your pre-test code.
      pte = trap_exception(e)
      error("Exception in pre-test code:\n" + ''.join(format_error(pte)))

  # Now run tests and report results:
  test_results = run_tests(widget, env)
  report_test_results(widget, test_results, exception, pte)

def attach_error_message(bucket, error):
  """
  Given a code bucket (that was just evaluated) and a TracebackException object
  (which resulted from that evaluation), this method generates an error DOM
  node and attaches it to the relevant code block in the given bucket.
  """
  block, line = block_and_line_responsible_for(bucket, error)
  attach_error_message_at_line(block, line, error)

def attach_error_mesage_to_code(node, error):
  """
  Works like attach_error_message, but attaches the message to an arbitrary
  code block. The error's line number should already be relative to that code
  block.
  """
  attach_error_message_at_line(node, error[2], error)

def attach_error_message_at_line(code_elem, line, error):
  """
  Attaches an error message to the given code element indicating that the given
  error occurred on the given line (inside the element).
  """
  error_type, error_msg, error_line, error_offset = error
  exc_msg = "{}: {}".format(error_type.__name__, error_msg)
  err = document.createElement("details")
  add_class(err, "error")
  err.innerHTML = exc_msg
  errname = document.createElement("summary")
  errname.innerText = error_type.__name__
  err.appendChild(errname)
  if not hasattr(code_elem, "__code__"):
    error(
      "Target element doesn't have a __code__ attribute:\n{}".format(code_elem)
    )
  if issubclass(error_type, SyntaxError):
    err.appendChild(
      document.createTextNode(
        "\nThe error was detected at this point:"
      )
    )
    errdesc = document.createElement("pre")
    add_class(errdesc, "syntax-error-description")
    errcode = document.createElement("code")
    add_class(errcode, "language-python")
    errcode.innerHTML = code_elem.__code__.split('\n')[line]
    browser.window.Prism.highlightElement(errcode) # highlight just the code
    errdesc.appendChild(errcode)
    # add the caret and message after the code
    log("EO:", error_offset)
    caret_text = '<br/>' + ('&nbsp;' * error_offset) + '^'
    caret = document.createElement("span")
    caret.innerHTML = caret_text
    errdesc.appendChild(caret)
    err.appendChild(errdesc)

  elif '\n' in code_elem.__code__: # multi-line code so identify the line
    err.appendChild(
      document.createTextNode(
        "\nThe error was detected on this line:"
      )
    )
    err_line = code_elem.__code__.split('\n')[line]
    errdesc = document.createElement("pre")
    add_class(errdesc, "syntax-error-description")
    errcode = document.createElement("code")
    add_class(errcode, "language-python")
    errcode.innerText = err_line
    browser.window.Prism.highlightElement(errcode) # highlight just the code
    errdesc.appendChild(errcode)
    err.appendChild(errdesc)

  code_elem.appendChild(err)

def block_and_line_responsible_for(bucket, error):
  """
  Figures out which block of code in a bucket was responsible for the given
  traceback by counting code lines and looking at the traceback's final line
  number. Also returns the line number within that block, as the second part of
  a tuple. Logs an error and returns None if the line number is out of range
  for the code block.
  """
  error_type, error_msg, error_line, error_offset = error
  sofar = 0
  last = None
  lines = None
  for child in bucket.children:
    if child.hasOwnProperty("__code__"):
      last = child
      lines = len(child.__code__.split('\n'))
      if sofar + lines >= error_line:
        return (child, error_line - 1 - sofar)
      else:
        sofar += lines
  if error_line == sofar + 1 and last != None:
    # e.g., an indentation error on final added blank line
    return (last, lines - 1)
  error("Ran out of code lines trying to find responsible block!")
  error(
    "children: {}, lines: {}, target: {}".format(
      len(bucket.children),
      sofar,
      error_line
    )
  )
  return None

def mark_errors_as_stale(widget):
  """
  Marks all errors in the given widget as stale (presumably because they're no
  longer 100% valid as code has been moved around).
  """
  for node in widget["node"].querySelectorAll(".error"):
    add_class(node, "stale")

def remove_errors(widget):
  """
  Removes errors from the given widget (presumably in preparation for
  re-executing the code and generating new errors).
  """
  for node in widget["node"].querySelectorAll(".error"):
    node.parentNode.removeChild(node)

def mark_tests_as_stale(widget):
  """
  Marks all tests in the given widget as stale.
  """
  for node in widget["node"].querySelectorAll(".test_feedback"):
    add_class(node, "stale")

def mark_tests_as_fresh(widget):
  """
  Removes the 'stale' class from all tests in the widget, along with the
  'passed' and 'failed' classes.
  """
  for node in widget["node"].querySelectorAll(".test_feedback"):
    remove_class(node, "stale", "passed", "failed")

def run_tests(widget, env):
  """
  Given an environment resulting from running the current code arrangement plus
  the pre-test code, this runs the tests for the widget and returns a list of
  dictionaries (one per test in order) with the following keys:

    "result": The result value.
    "exception": The exception thrown if any. Result will be None in this case.
    "expected": The evaluated expected value
    "exp_exception": The exception thrown when evaluating the expected value,
      if any. Expected will be None in this case.
    "passed": Whether the test passed (True) or failed (False).

  Returns None if the widget doesn't have any tests. Note that the same
  environment is used for all tests, so earlier tests are allowed to influence
  later ones, although they probably shouldn't.

  Because we use == to compare evaluated actual/expected values, for complex
  data structures you may need to use th pre-test code to set __eq__ properties
  on certain objects so that they can be compared properly. You could also use
  this to make equality tests approximate instead of exact.
  """
  if "tests" not in widget["puzzle"]: # no tests, so just check for errors...
    return None

  tests = widget["puzzle"]["tests"]

  results = []
  for test in tests:
    test = full_test(test)
    texpr = test["expression"]
    if "expect_error" in test:
      texpect = test["expect_error"]
    else:
      texpect = test["expected"]
    tresult = {
      "result": None,
      "exception": None,
      "expected": None,
      "exp_exception": None,
      "passed": False
    }

    try:
      tresult["result"] = eval(texpr, globals=env[0], locals=env[1])
    except Exception as e:
      tresult["exception"] = trap_exception(e)

    try:
      tresult["expected"] = eval(texpect, globals=env[0], locals=env[1])
      if "expect_error" in test and test["expect_error"] != None:
        if not isinstance(tresult["expected"], Exception):
          error(
            "Expected expression didn't result in an Exception object even "
          + "though expect_error was not None!"
          )
        tresult["expected"] = trap_exception(tresult["expected"])
    except Exception as e:
      tresult["exp_exception"] = trap_exception(e)

    # Can't pass the test if we weren't able to evaluate the expected
    # expression:
    if tresult["exp_exception"] != None:
      tresult["passed"] = False
    elif "expect_error" in test: # pass if the correct exception was generated
      res = tresult["exception"]
      exp = tresult["expected"]
      if res == None and exp == None:
        tresult["passed"] = True
      elif res == None or exp == None:
        tresult["passed"] = False
      else:
        tresult["passed"] = (
          res.exc_type == exp.exc_type
      and str(res) == str(exp)
        )
    else: # pass if the correct value was returned
      if tresult["exception"] != None:
        tresult["passed"] = False
      else:
        log(
          "Testing...\n{} == {} ? {}".format(
            repr(tresult["result"]),
            repr(tresult["expected"]),
            tresult["result"] == tresult["expected"]
          )
        )
        tresult["passed"] = tresult["result"] == tresult["expected"]

    # Record the result for this test and continue to the next
    results.append(tresult)

  return results

def report_test_results(widget, results, error=None, pretest_error=None):
  """
  Reports test results by updating the status of individual test blocks and/or
  attaching errors to them. If there was an error before testing could be
  initiated (either an error value from execing the code or a pretest_error
  value from attempting the pretest code) tests won't be updated and an error
  indicator will be shown (attaching those errors to the DOM is not handled
  here).
  """
  ind = widget["test_indicator"]
  soln_blocks = list(widget["soln_bucket"].querySelectorAll(".code_block"))
  solution = [block.__code__ for block in soln_blocks]
  if has_class(ind, "boolean"):
    # Widget has no tests; success is an arrangement of all blocks that doesn't
    # cause any errors.
    if results != None:
      error(
        "Non-None results for widget with boolean indicator:\n{}".format(
          results
        )
      )
    if error != None:
      ind.innerText = "Error running code."
    elif pretest_error != None:
      ind.innerText = (
        "Error preparing tests. We could not check your solution, but it is "
      + "probably not correct."
      )
    else: # No errors: puzzle solved (or empty)
      src_blocks = list(
        widget["source_bucket"].querySelectorAll(".code_block")
      )
      if len(soln_blocks) > 0: # possible solution
        if len(src_blocks) == 0:
          ind.innerText = "Puzzle solved!"
          mark_solved(widget, solution)
        else:
          ind.innerText = "No errors so far; use all blocks to solve puzzle."
      else: # empty bucket -> default message
        ind.innerText = (
          "Click 'check' to run the code... (drag some code to the right side "
        + "first)"
        )

  else:
    # Widget has tests, so report success/failure

    passed = [r for r in results if r["passed"] == True]
    if error != None:
      ind.innerText = "? / {} tests passed (error running code)".format(
        len(results)
      )
    elif pretest_error != None:
      ind.innerText = (
        "? / {} tests passed (Error preparing tests. Your code itself does "
      + "not have an error, but we could not set up for the tests, so your "
      + "solution is probably not correct.)"
      ).format(len(results))
    else:
      ind.innerText = "{} / {} tests passed".format(len(passed), len(results))
      if len(passed) == len(results):
        mark_solved(widget, solution)
        ind.innerText += " (puzzle solved!)"
      if "test_elements" in widget:
        # report pass/fail for individual tests
        for i, r in enumerate(results):
          tnode = widget["test_elements"][i]
          test = widget["puzzle"]["tests"][i]
          tval = tnode.querySelector(".test_value")
          texp = tnode.querySelector(".test_expected")

          # Mark as passed/failed
          log("Test #{}: {}".format(i, r))
          if r["passed"]:
            add_class(tnode, "passed")
          else:
            add_class(tnode, "failed")

          # Add result values and/or exceptions:
          if "expect_error" in test: # we are expecting an exception
            if test["expect_error"] == None: # we were expecting no exception
              if r["exception"] != None:
                tval.innerText = "<error>"
                attach_error_mesage_to_code(tval, r["exception"])
              else:
                tval.innerText = r["<no error>"]

              if r["exp_exception"] != None:
                texp.innerText = "<no error>"
                attach_error_mesage_to_code(texp, r["exp_exception"])
              else:
                texp.innerText = "<no error>"
                if r["expected"] != None:
                  attach_error_mesage_to_code(texp, r["expected"])

            else: # we were expecting a specific exception

              if r["exception"] != None:
                tval.innerText = "<expected error>"
                attach_error_mesage_to_code(tval, r["exception"])
              else:
                tval.innerText = r["result"]

              if r["exp_exception"] != None:
                texp.innerText = "<error trying to figure out expected error>"
                attach_error_mesage_to_code(texp, r["exp_exception"])
                error(
                  "Exception trying to evaluate expected exception:\n{}".format(
                    format_error(test["exp_exception"])
                  )
                )
              else:
                texp.innerText = "<specific error>"
                if r["expected"] != None:
                  attach_error_mesage_to_code(texp, r["expected"])
                else:
                  error(
                    "Expected was None while expect_error was not:\n{}".format(
                      test["expect_error"]
                    )
                  )
                  texp.innerText = "<specific error (missing)>"

          else: # We weren't expecting an exception:
            if r["exception"] != None:
              tval.innerText = "<error>"
              attach_error_mesage_to_code(tval, r["exception"])
            else:
              tval.innerText = r["result"]

            if r["exp_exception"] != None:
              texp.innerText = "<error trying to figure out expected value>"
              attach_error_mesage_to_code(texp, r["exp_exception"])
            else:
              texp.innerText = str(r["expected"])

def mark_solved(widget, solution):
  """
  Marks a widget as solved and remembers the solution as the last-discovered
  solution.
  """
  widget["solved"] = True
  widget["last_solution"] = solution
  add_class(widget["node"], "solved")
  # TODO: report solution more directly?

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
    tests (optional):
      A list of test dictionaries, which determine whether the puzzle is solved
      or not. If no tests are given, any non-empty code that doesn't generate
      an error will count as a solution. Each test must have the following
      keys:

        label: A string that describes what is tested
        expression: The expression to evaluate as a code string
        expected: The correct value of the expression, also as a string to be
          evaluated.
        expect_error: A code string that evaluates to an Exception object.
          If this is present, 'expected' is ignored, and the test passes only
          if it raises an equivalent exception (in terms of type and message).
          This is optional. It may also be supplied as None, in which case the
          test passes as long as no error is generated (and again "expected"
          will be ignored). So expect_error being None is *not* the same as the
          key being missing.
        abstract: This key is optional; if the value is truthy, the test
          expression and value won't be shown, but the label will be.
        hidden: This key is optional; if the value is truthy, the test won't be
          shown at all, but it will still be counted.

      Instead of a test object with keys, a test may instead be specified using
      a tuple, where the first element is a string expression to evaluate and
      the second is the expected value. These tests will be given an automatic
      label based on their expression.

    pretest (optional):
      A string of code to be executed before testing blocks.
    instructions (optional):
      An HTML string to be displayed to the user that describes the goal of the
      puzzle. Default instructions are displayed if none are given.
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
        error(format_error(trap_exception(e)))

  setup_base_puzzle(node, puzzle) # accepts None puzzle and defaults

  # Set up event handlers on this widget
  node.addEventListener("dragstart", drag_start, False)
  node.addEventListener("dragend", drag_end, False)
  node.addEventListener("dragover", drag_over, False)
  node.addEventListener("dragenter", drag_enter, False)
  node.addEventListener("dragenter", drag_enter, False)
  node.addEventListener("dragleave", drag_leave, False)
  node.addEventListener("drop", drag_drop, False)

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

def setup_base_puzzle(node, puzzle):
  """
  Sets up a basic two-column puzzle where you drag blocks from the left into
  blank space on the right.
  """
  if puzzle == None:
    puzzle = { # default puzzle:
      "code": [
        "a = 3",
        "b = 4",
        "c = a*b",
        "a += 5",
        "b = a + 1",
        "c = c + a"
      ],
      "pretest": "",
      "tests": [
        ['a', '8'], # note: both sides will be evaluated
        ['b', '9'],
        ['c', '20'],
      ]
    }
    # (default instructions will be added below)

  # Add default instructions if they're missing:
  if "instructions" not in puzzle:
    if "tests" in puzzle:
      puzzle["instructions"] = (
        "Drag the code on the left into the box on the right and arrange it "
      + "so that all of the tests pass."
      )
    else:
      puzzle["instructions"] = (
        "Drag the code on the left into the box on the right and arrange it "
      + "so that there are no errors."
      )

  w = {
    "puzzle": puzzle,
    "node": node
  } # the widget object
  node.__widget__ = w # attach it to the DOM

  code_blocks = puzzle["code"]
  if isinstance(code_blocks, str):
    code_blocks = blocks_from_lines(code_blocks)

  w["code_blocks"] = code_blocks

  # instructions div
  w["instructions"] = document.createElement("div")
  add_class(w["instructions"], "instructions")
  w["instructions"].innerHTML = puzzle["instructions"]
  node.appendChild(w["instructions"])

  # bucket for source blocks
  w["source_bucket"] = document.createElement("div")
  add_class(w["source_bucket"], "code_bucket", "code_source")
  node.appendChild(w["source_bucket"])

  # Shuffle the code blocks
  # TODO: random seeding?
  seed = puzzle["seed"] if "seed" in puzzle else 1712873
  random.seed(seed)
  random.shuffle(code_blocks)

  # Add each code block to our source div:
  for block in code_blocks:
    add_code_block_to_bucket(w["source_bucket"], block)

  # bucket for solution blocks
  w["soln_bucket"] = document.createElement("div")
  add_class(w["soln_bucket"], "code_bucket", "soln_list")
  node.appendChild(w["soln_bucket"])

  # Create evaluate button in solution bucket:
  eb = document.createElement("input")
  add_class(eb, "eval-button")
  eb.type = "button"
  eb.value = "check"
  eb.__bucket__ = w["soln_bucket"]
  eb.addEventListener("click", eval_button_handler)
  w["soln_bucket"].appendChild(eb)

  if "tests" in puzzle:
    # tests div
    w["test_div"] = document.createElement("details")
    add_class(w["test_div"], "tests")

    # We've got tests but they need to be hidden
    w["test_indicator"] = document.createElement("summary")
    add_class(w["test_indicator"], "test_indicator")
    w["test_indicator"].innerText = "? / {} tests passed".format(
      len(puzzle["tests"])
    )
    w["test_div"].appendChild(w["test_indicator"])
    # Display tests:
    w["test_elements"] = []
    hidden_count = 0
    for test in puzzle["tests"]:
      test = full_test(test)
      tnode = document.createElement("div")
      add_class(tnode, "test_feedback")
      if test.get("hidden"):
        add_class(tnode, "hidden")
        hidden_count += 1
      if test.get("abstract"):
        add_class(tnode, "abstract")

      # Test status
      tstatus = document.createElement("span")
      add_class(tstatus, "test_status")
      tstatus.innerText = "" # CSS :after fills this in
      tnode.appendChild(tstatus)

      # Label for the entire test
      tlabel = document.createElement("span")
      add_class(tlabel, "test_label")
      tlabel.innerHTML = test["label"]
      tnode.appendChild(tlabel)

      # Test expression label
      texpr_label = document.createElement("span")
      add_class(texpr_label, "field_label")
      texpr_label.innerText = "Expression:"
      tnode.appendChild(texpr_label)

      # Test expression
      texpr = document.createElement("code")
      w["test_elements"].append(tnode) # same order as tests
      add_class(texpr, "test_expr", "test_code")
      add_class(texpr, "language-python")
      texpr.innerText = test["expression"]
      texpr.__code__ = test["expression"]
      browser.window.Prism.highlightElement(texpr)
      tnode.appendChild(texpr)

      # Value label
      tval_label = document.createElement("span")
      add_class(tval_label, "field_label")
      tval_label.innerText = "Value:"
      tnode.appendChild(tval_label)

      # Value of the expression
      tval = document.createElement("code")
      add_class(tval, "test_value", "test_code")
      tval.innerText = "?"
      if "expect_error" in test:
        tval.__code__ = test["expect_error"]
      else:
        tval.__code__ = test["expected"]
      tnode.appendChild(tval)

      # Expected label
      texp_label = document.createElement("span")
      add_class(texp_label, "field_label")
      texp_label.innerText = "Expected:"
      tnode.appendChild(texp_label)

      # Expected value
      texp = document.createElement("code")
      add_class(texp, "test_expected", "test_code")
      if "expect_error" in test:
        texp.innerText = test["expect_error"]
        texp.__code__ = test["expect_error"]
        tnode.appendChild(texp)
      else:
        texp.innerText = test["expected"]
        texp.__code__ = test["expected"]
      tnode.appendChild(texp)

      w["test_div"].appendChild(tnode)

    # Add note about hidden tests
    if hidden_count == len(puzzle["tests"]):
      note = document.createTextNode("(all tests are secret)")
      w["test_div"].appendChild(note)
    elif hidden_count > 0:
      note = document.createTextNode(
        "(plus {} secret tests)".format(hidden_count)
      )
      w["test_div"].appendChild(note)

  else: # solution = error-free arrangement of all blocks
    # tests div
    w["test_div"] = document.createElement("div")
    add_class(w["test_div"], "tests")

    w["test_indicator"] = document.createElement("span")
    add_class(w["test_indicator"], "test_indicator", "boolean")
    w["test_indicator"].innerText = "Click 'check' to run the code..."
    w["test_div"].appendChild(w["test_indicator"])

  # Add tests block to widget node:
  node.appendChild(w["test_div"])

def full_test(test):
  """
  Converts a potentially abbreviated test into a full test.
  """
  if isinstance(test, dict):
    result = test
  elif isinstance(test, javascript.JSObject):
    result = test.to_dict()
  elif isinstance(test, [list, tuple]):
    result = {
      "label": "Value of '{}'".format(test[0]),
      "expression": test[0],
      "expected": test[1]
    }
  else:
    error("Invalid test type ({}):\n{}".format(type(test), test))
    return test
  for key in ["label", "expression", "expected"]:
    if key not in result:
      error("Full test without {}:\n{}".format(key, test))
  return result

def sequence_puzzles(widget, puzzles):
  """
  Takes a list of puzzle objects and presents them one at a time through the
  given widget, displaying a new puzzle when the current one is solved.
  """
  #log(puzzles[0])
  setup_widget(widget, puzzles[0])
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
  base = window.location.href
  path = '/'.join(base.split('/')[:-1])
  dpath = path + "/" + url

  # Load asynchronously
  def catch(req):
    if req.status == 200 or (req.status == 0 and dpath.startswith("file://")):
      try:
        # Using Python's json module here is horrifically slow
        obj = browser.window.JSON.parse(req.text)
      except Exception as e:
        error("Malformed JSON from '{}':\n{}".format(dpath, req.text))
        error(format_error(trap_exception(e)))
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
    error(format_error(trap_exception(e)))

def init_procedural_widgets():
  """
  Selects all procedural_widget divs and creates elements inside each one to
  play a Parson's puzzle.
  """

  # Collect each widget:
  widgets = document.querySelectorAll(".procedural_widget")

  # Set up each widget automatically:
  for widget in widgets:
    setup_widget(widget)

# Call this when script is run:
init_procedural_widgets()
