#script(python)

import sys
import random
import json

import clingo

CONSTANTS = [1, 2, 3, 5, 7, 11, 13, 17, 23]

VARNAMES = [ "horses", "angle", "branches", "length", "tea" ]

BINOPS = {
  "plus": ("+", lambda a, b: a + b),
  "minus": ("-", lambda a, b: a - b),
  "times": ("*", lambda a, b: a * b),
  "divide": ("/", lambda a, b: a / b),
  "intdiv": ("//", lambda a, b: a // b),
  "modulo": ("%", lambda a, b: a % b),
  "exp": ("**", lambda a, b: a ** b),
# TODO: Reintroduce these?
#  "compare": ("==", lambda a, b: a == b),
#  "and": ("and", lambda a, b: a and b),
#  "or": ("or", lambda a, b: a or b),
}

ASGOPS = [
  "plus", "minus", "times", "divide", "modulo",
# TODO: Restore these
#  "intdiv", "exp"
]

UNOPS = {
  "neg": ("-", lambda x: -x),
# TODO: Reintroduce this?
#  "nt": ("not", lambda x: not x),
}

def pick_line_count(min, max):
  """
  Selects the number of lines to use in the puzzle.
  """
  return random.randint(min.number, max.number)

VARNAME_COUNTER = 0
def next_var_name():
  """
  Picks out and returns the next variable name.
  """
  global VARNAME_COUNTER
  next = VARNAMES[VARNAME_COUNTER]
  VARNAME_COUNTER = (VARNAME_COUNTER + 1) % len(VARNAMES)
  if VARNAME_COUNTER == 0: # we wrapped
    print("Warning: out of variable names!", file=sys.stderr)
  return next

def reset_variable_names():
  """
  Resets the variable name assignment system.
  """
  global VARNAMES
  global VARNAME_COUNTER
  random.shuffle(VARNAMES)
  VARNAME_COUNTER = 0

def random_constant():
  """
  Selects a random constant value.
  """
  base = CONSTANTS
  full = base + [1, 2, 3]*5 + [1, 2]*3 + [1]*2 + [5, 7, 11]*2 + [5, 7]*2
  return random.choice(full)

def random_binop():
  """
  Selects a random binary operator.
  """
  base = list(BINOPS.keys())
  full = base + base + ["plus", "minus"]*4 + ["times", "divide"]*2
  return random.choice(full)

def random_unop():
  """
  Selects a random unary operator.
  """
  base = list(UNOPS.keys())
  full = base + ["neg"]*2
  return random.choice(full)

def random_asgop():
  """
  Selects a random assignment operator.
  """
  base = ASGOPS
  full = base + ["plus", "minus"]*4 + ["times"]
  return random.choice(full)

def concrete_expression(expression, memo=None):
  """
  Takes an expression predicate which includes placeholders for constants
  and/or operators and randomly inserts values to make it concrete.
  """
  if memo == None:
    memo = {}

  name = expression.name
  args = expression.arguments

  if name == "binop":
    if args[0].name == "_binop_":
      left = concrete_expression(args[1], memo)
      right = concrete_expression(args[2], memo)
      return clingo.Function(
        "binop",
        [
          clingo.Function(random_binop(), []),
          left,
          right
        ]
      )
    else:
      left = concrete_expression(args[1], memo)
      right = concrete_expression(args[2], memo)
      return clingo.Function("binop", [args[1], left, right])
  elif name == "unop":
    if args[0].name == "_unop_":
      sub = concrete_expression(args[1], memo)
      return clingo.Function(
        "unop",
        [
          clingo.Function(random_unop(), []),
          sub
        ]
      )
    else:
      sub = concrete_expression(args[1], memo)
      return clingo.Function("unop", [args[0], sub])
  elif name in ("dot", "index", "assign"):
    left = concrete_expression(args[0], memo)
    right = concrete_expression(args[1], memo)
    return clingo.Function(name, [left, right])
  elif name == "augassign":
    if args[0].name == "_asgop_":
      left = concrete_expression(args[1], memo)
      right = concrete_expression(args[2], memo)
      return clingo.Function(
        name,
        [
          clingo.Function(random_asgop(), []),
          left,
          right
        ]
      )
    else:
      left = concrete_expression(args[1], memo)
      right = concrete_expression(args[2], memo)
      return clingo.Function(name, [args[0], left, right])
  else: # must be a constant or number
    if name == "_const_":
      return clingo.Number(random_constant())
    elif expression.type == clingo.SymbolType.Function:
      if name.startswith("_var") and name.endswith("_"):
        if name not in memo:
          memo[name] = next_var_name()
        return clingo.Function(memo[name], args)
    else:
      return expression # unchanged

def expr_as_string(expression):
  """
  Converts an expression from predicate form to a code string.
  """
  name = expression.name
  args = expression.arguments
  if name == "binop":
    left = expr_as_string(args[1])
    right = expr_as_string(args[2])
    if args[1].name in ("binop", "unop"):
      left = '(' + left + ')'
    if args[2].name in ("binop", "unop"):
      right = '(' + right + ')'
    return "{} {} {}".format(
      left,
      BINOPS[args[0].name][0],
      right
    )
  elif name == "unop":
    op = UNOPS[args[0].name][0]
    if op != '-':
      op += ' '
    return "{}{}".format(op, expr_as_string(args[1]))
  elif name == "dot":
    return "{}.{}".format(expr_as_string(args[0]), expr_as_string(args[1]))
  elif name == "index":
    return "{}[{}]".format(expr_as_string(args[0]), expr_as_string(args[1]))
  elif name == "assign":
    return "{} = {}".format(expr_as_string(args[0]), expr_as_string(args[1]))
  elif name == "augassign":
    return "{} {}= {}".format(
      expr_as_string(args[1]),
      BINOPS[args[0].name][0],
      expr_as_string(args[2])
    )
  else: # must be a variable name or a number
    # TODO: does this handle numbers correctly?
    # TODO: Handle quoted strings!
    if expression.type == clingo.SymbolType.Function:
      return name
    elif expression.type == clingo.SymbolType.Number:
      return expression.number
    elif expression.type == clingo.SymbolType.String:
      return repr(expression.string)
    else:
      print(
        "Error: invalid predicate type: '{}'".format(expression.type),
        file=sys.stderr
      )
      return None

def eval_expr(expression, ctx):
  """
  Evaluates an expresssion in the given context. Returns None if the expression
  results in an error. If the expression is an assignment, this modifies the
  context as a side effect, and returns None.
  """
  name = expression.name
  args = expression.arguments
  try:
    if name == "binop":
      return BINOPS[args[0].name][1](
        eval_expr(args[1], ctx),
        eval_expr(args[2], ctx)
      )
    elif name == "unop":
      return UNOPS[args[0].name][1](eval_expr(args[1], ctx))
    elif name == "dot":
      return getattr(eval_expr(args[0], ctx), eval_expr(args[1], ctx))
    elif name == "index":
      return eval_expr(args[0], ctx).__getitem__(eval_expr(args[1], ctx))
    elif name == "assign":
      var = args[0].name
      val = eval_expr(args[1], ctx)
      ctx[var] = val
      return None # value of an assignment is None
    elif name == "augassign":
      var = args[1].name
      oldval = ctx[var]
      val = eval_expr(args[2], ctx)
      ctx[var] = BINOPS[args[0].name][1](oldval, val)
      return None
    else: # must be a variable name or a number
      if expression.type == clingo.SymbolType.Function:
        # TODO: Warn about non-zero-arg functions?
        return ctx[name]
      elif expression.type == clingo.SymbolType.Number:
        return expression.number
      elif expression.type == clingo.SymbolType.String:
        return expression.string
      else:
        print(
          "Error: invalid predicate type: '{}'".format(expression.type),
          file=sys.stderr
        )
        return None
  except:
    return None

def extract_code_lines(model):
  """
  Extracts lines of code as a string from the given model.
  """
  lines = {}
  indents = {}
  varnames = {}
  for atom in model.symbols(atoms=True):
    if atom.name == "code_line":
      line_id, expression = atom.arguments
      id = line_id.number
      concrete = concrete_expression(expression, memo=varnames)
      lines[id] = expr_as_string(concrete)
    elif atom.name == "code_indent":
      line_id, levels = atom.arguments
      id = line_id.number
      indents[id] = '\t'*levels.number
    elif atom.name == "message":
      print('\n'*2 + str(atom) + '\n'*2, file=sys.stderr)

  # Put lines together into a result string:
  result = ""
  for id in sorted(lines):
    result += indents[id] + lines[id] + '\n'

  return result

def observe_solutions(solgen):
  """
  Converts models to JSON objects and writes them to stdout.
  """
  puzzles = []
  for sol in solgen:
    reset_variable_names()
    puzzle = {}
    puzzle["code"] = extract_code_lines(sol)
    puzzle["extra"] = ""
    puzzles.append(puzzle)
    #sys.stdout.write('\n'*4)
    #sys.stdout.write(puzzle["code"])
    #sys.stdout.write('\n'*4)
    sys.stderr.write(
      "Found {} puzzles so far...\r".format(len(puzzles))
    )
    if len(puzzles) % 1000 == 0:
      sys.stderr.flush()
  sys.stderr.write("Found {} puzzles in total.\n".format(len(puzzles)))
  sys.stderr.flush()
  sys.stdout.write(json.dumps(puzzles))

def main(prg):
  """
  Main program called automatically by clingo.
  """
  # Set seed from clingo seed (see Makefile)
  random.seed(prg.configuration.solver.seed)

  # Configuration
  prg.configuration.solve.models = 0 # keep generating solutions forever
  # Note: this is how to figure out what configuration keys are available
  #print(prg.configuration.solver.keys)

  # Lots of randomness:
  prg.configuration.solver.rand_freq = 0.8
  prg.configuration.solver.restart_on_model = 1

  # Loading extra files
  prg.load("gen.lp") # program 'gen'
  prg.load("vars.lp") # program 'vars'

  # Grounding and solving
  prg.ground([("gen",[]), ("vars",[])])
  solgen = prg.solve(yield_=True)
  sys.stderr.write(
    "Use ^C at any time to cut off solving and print solutions found so far.\n"
  )
  sys.stderr.flush()
  observe_solutions(solgen)
#end.
