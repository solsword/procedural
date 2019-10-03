# Your name: Peter Mawhorter
# Your username: pmwh
# CS111 PS04 Task 2 Supporting Code
# maze.py
# Created: 2019/09/23

# time module for waiting to control animation speed
import time

# for the randomMove function
import random

# cs1graphics for drawing the maze state
from cs1graphics import *

########################################
# Constants and other global variables #
########################################

# Maximum number of steps allowed
# 400 is 20 squared, so up to a bit more than a 20x20 maze should be fine
DEFAULT_MAX_STEPS = 400

# Speed in Hertz (updates per second):
# Use 0 to print as quickly as possible
DEFAULT_SPEED = 1.5

# These values are used to determine directions, and should be returned by
# agent functions.
FORWARD = 0
RIGHT = 1
BACKWARD = 2
LEFT = 3

# Several different mazes of varying difficulty:
MAZE0 = """\
######
#>  G#
######\
"""

MAZE1 = """\
########
#    #G#
# ## # #
# #> # #
# #### #
#      #
########\
"""

MAZE2 = """\
#######
#     #
# ### #
#  <# #
##### #
#G    #
#######\
"""

MAZE3 = """\
#########
#v#   #G#
# # # # #
# # # # #
#   #   #
#########\
"""

MAZE4 = """\
#########
# # #G# #
# # # # #
# # # # #
#   <   #
#########\
"""

MAZE5 = """\
#########
# # #G# #
# # # # #
# # # # #
#   >   #
#########\
"""

MAZE6 = """\
#########
# #     #
#   # # #
# ### ###
# ^#   G#
#########\
"""

MAZE7 = """\
##################
#v#     #   ##   #
# # ###   #    # #
#     ##### # ## #
# ### #     #  ###
#   ### ######   #
# # ##   #   ### #
# # G# # # #     #
##################\
"""

MAZE8 = """\
#########
#       #
# #G v# #
#       #
#########\
"""

MAZE9 = """\
#########
#       #
# G# v# #
#       #
#########\
"""

MAZE10 = """\
##########
#        #
#    v#  #
# G#     #
#        #
##########\
"""

MAZE11 = """\
#######
#     #
#     #
#  G  #
#     #
#^    #
#######\
"""

MAZE12 = """\
#########
#>      #
#       #
##     ##
###   ###
### G ###
###   ###
#########\
"""

MAZE13 = """\
#########
###   ###
### G ###
###   ###
##     ##
#       #
#>      #
#########\
"""

####################
# Helper functions #
####################

def rightOf(direction):
  """
  Returns the direction that's to the right of the given direction.
  """
  return (direction + 1) % 4

def leftOf(direction):
  """
  Returns the direction that's to the left of the given direction.
  """
  return (direction + 3) % 4

def reverseOf(direction):
  """
  Returns the direction that's the reverse of the given direction.
  """
  return (direction + 2) % 4

def randomDirection():
  """
  Returns a random direction.
  """
  return random.randint(0, 3)

def coordsInDirection(x, y, d):
  """
  Accepts x/y coordinates and a direction and returns the coordinates of
  the tile that's in that direction from the given coordinates.
  """
  if d == FORWARD:
    return [x, y-1]
  elif d == RIGHT:
    return [x+1, y]
  elif d == BACKWARD:
    return [x, y+1]
  elif d == LEFT:
    return [x-1, y]
  else:
    raise ValueError("Invalid direction: " + repr(d))

def isCompleted(maze):
  """
  A maze is completed if it has the 'S' for success character anywhere
  inside.
  """
  return 'S' in maze

def robotFacing(direction):
  """
  Returns the character which represents a robot facing the given
  direction.
  """
  if direction == FORWARD:
    return '^'
  elif direction == RIGHT:
    return '>'
  elif direction == BACKWARD:
    return 'v'
  elif direction == LEFT:
    return '<'

############################
# Complex helper functions #
############################

def getSurroundings(maze):
  """
  Looks at the give maze and finds the robot in it using
  getRobotPositionAndFacing. Then figures out what tiles are situated on
  all sides of the robot, and returns the tiles to the front, right,
  back, and left of the robot in that order.
  """
  x, y, f = getRobotPositionAndFacing(maze)

  # Get tiles from each direction relative to robot
  frontX, frontY = coordsInDirection(x, y, f)
  inFront = getMazeTileAt(maze, frontX, frontY)

  leftX, leftY = coordsInDirection(x, y, leftOf(f))
  atLeft = getMazeTileAt(maze, leftX, leftY)

  rightX, rightY = coordsInDirection(x, y, rightOf(f))
  atRight = getMazeTileAt(maze, rightX, rightY)

  behindX, behindY = coordsInDirection(x, y, reverseOf(f))
  inBack = getMazeTileAt(maze, behindX, behindY)

  return [ inFront, atRight, inBack, atLeft ]

def getMazeTileAt(maze, x, y):
  """
  Gets the tile from a maze at specific x/y coordinates.
  """
  rows = maze.split('\n')
  if 0 <= y < len(rows):
    row = rows[y]
    if 0 <= x <= len(row):
      return row[x]
    else:
      return '#'
  else:
    return '#' # tiles outside the maze are walls

def getRobotPositionAndFacing(maze):
  """
  Looks at a maze and finds a robot in it, returning the coordinates and
  facing of the robot.
  """
  rows = maze.split('\n')
  for y, row in enumerate(rows):
    for x, char in enumerate(row):
      if char == '^':
        return [x, y, FORWARD]
      elif char == '>':
        return [x, y, RIGHT]
      elif char == 'v':
        return [x, y, BACKWARD]
      elif char == '<':
        return [x, y, LEFT]
      # else continue searching for the robot in the maze
  # Unable to find robot?!?!
  raise ValueError("No robot in the maze!")

##################
# Core functions #
##################

def showMaze(maze, step=None):
  """
  Displays a maze by printing it, and if a step value is supplied also
  prints that.
  """
  print('-'*80)
  if step != None:
    print("Step " + str(step))
  print(maze)
  print('-'*80)

def animateAgent(maze, agent, speed=DEFAULT_SPEED, maxSteps=DEFAULT_MAX_STEPS):
  """
  Draws repeated frames of the maze state as the given agent moves
  through the maze. The speed parameter controls how fast the frames are
  drawn, in frames drawn per second. Use 0 for speed to draw as quickly
  as possible. The maxSteps parameter controls when to cut the agent off.
  A message will be printed if the agent takes too long.
  """
  for step in range(maxSteps):
    showMaze(maze, step)
    if speed > 0:
      time.sleep(1/float(speed))
    oldMaze = maze
    maze = nextMazeState(maze, agent)
    if isCompleted(maze):
      showMaze(maze, step+1)
      print("Found the goal! Hooray!")
      break
    #elif oldMaze == maze:
    #  # TODO: less aggressive about this in the future?
    #  showMaze(maze, step+1)
    #  print("Got stuck (nothing changed)!")
    #  break

  if not isCompleted(maze):
    print("Ran out of steps.")

def testAgent(maze, agent, maxSteps=DEFAULT_MAX_STEPS):
  """
  Tests whether an agent can make it to the goal within a specified
  number of steps. Works like animateAgent, but just returns True (if the
  agent makes it to the goal) or False (if not) without printing
  anything.
  """
  for step in range(maxSteps + 1): # +1 so that maxSteps = 1 tests after 1 step
    if isCompleted(maze):
      return True
    maze = nextMazeState(maze, agent)

  return False # ran out of steps

def nextMazeState(maze, agent):
  """
  This function takes a maze with a robot at a particular position and
  returns a new maze where that robot has moved once. The given agent
  function determines how the robot moves: it will be called with the
  front, right, back, and left characters adjacent to the robot, and
  should return one of the directional constants maze.FORWARD,
  maze.RIGHT, maze.BACKWARD, or maze.LEFT. The robot will turn to face
  the given direction and move one square in that direction, or stay
  still if there is a wall in that direction.
  """
  # Get robot position, facing, and surrounding tiles:
  x, y, f = getRobotPositionAndFacing(maze)
  ft, rt, bk, lt = getSurroundings(maze)

  action = agent(ft, rt, bk, lt)

  # figure out new facing based on agent action:
  if action == FORWARD:
    newF = f
  elif action == RIGHT:
    newF = rightOf(f)
  elif action == BACKWARD:
    newF = reverseOf(f)
  elif action == LEFT:
    newF = leftOf(f)
  else:
    raise ValueError(
      "Invalid action: " + repr(action) + """
(the action returned by an agent must be one of maze.FORWARD, maze.RIGHT,
maze.BACKWARD, or maze.LEFT)"""
    )

  # compute new position and figure out what's there
  newX, newY = coordsInDirection(x, y, newF)
  atNew = getMazeTileAt(maze, newX, newY)

  if atNew == '#': # a wall: turn, but don't move
    return mazeWithUpdate(maze, x, y, robotFacing(newF))
  elif atNew == 'G': # the goal: turn into an S for success
    return mazeWithUpdate(mazeWithUpdate(maze, x, y, '.'), newX, newY, 'S')
  else: # an empty spot: move there
    rob = robotFacing(newF)
    return mazeWithUpdate(mazeWithUpdate(maze, x, y, '.'), newX, newY, rob)

def mazeWithUpdate(maze, x, y, newTile):
  """
  Accepts a maze and returns a new maze where the tile at the given x/y
  coordinates has been replaced with the given new tile. Makes no change
  if the location is outside the maze.
  """
  rows = maze.split('\n')
  result = ''
  for rowY, row in enumerate(rows):
    for tileX, tile in enumerate(row):
      if rowY == y and tileX == x:
        result = result + newTile
      else:
        result = result + tile
    # After every full cycle of the inner loop (except the last), we add
    # a newline to our result
    if rowY < len(rows) - 1:
      result = result + '\n'

  return result
