"""
cs1graphics.py

Fake cs1graphics implementation that just creates and tracks object positions
and containment, to be used for automatic testing. Doesn't draw anything.
"""

import copy

class Gobj:
  def __init__(self, info):
    self._info = info
    self.fillColor = "transparent"
    self.borderColor = "black"
    self.borderWidth = 1
    self.rotation = 0
    self.size = 1
    self.depth = 50

    for (key, val) in info.items():
      setattr(self, key, val)

    self.offset = [0, 0]
    if hasattr(self, "center"):
      self.reference = [self.center.x, self.center.y]
    elif self.type == "Polygon":
      self.reference = [self.points[0].x, self.points[0].y]
    else:
      self.reference = [0, 0]

  def setFillColor(self, color):
    self.fillColor = color

  def setBorderColor(self, color):
    self.borderColor = color

  def setBorderWidth(self, width):
    self.borderWidth = width

  def rotate(self, rotation):
    self.rotation += rotation

  def scale(self, factor):
    self.size *= factor

  def moveTo(self, x, y):
    self.offset[0] = x - self.reference[0]
    self.offset[1] = y - self.reference[1]

  def move(self, dx, dy):
    self.offset[0] += dx
    self.offset[1] += dy

  def setDepth(self, depth):
    self.depth = depth

  def get_location(self):
    return [
      self.reference[0] + self.offset[0],
      self.reference[1] + self.offset[1]
    ]

class Layer(Gobj):
  def __init__(self):
    super(Layer, self).__init__({"type": "Layer"})
    self.contents = []

  def add(self, item):
    item._parent = self
    self.contents.append(item)

  def clone(self):
    return copy.deepcopy(self)

class Canvas(Layer):
  def __init__(
    self,
    width=200,
    height=200,
    bgColor="white",
    title="Graphics canvas"
  ):
    super(Canvas, self).__init__()
    self.type = "Canvas"
    self.width = width
    self.height = height
    self.bgColor = bgColor
    self.title = title

def Polygon(*points):
  return Gobj({ "type": "Polygon", "points": points })

def Point(x=0, y=0):
  return Gobj({ "type": "Point", "x": x, "y": y })

def Circle(radius=10, center=Point(0, 0)):
  return Gobj({ "type": "Circle", "radius": radius, "center": center })

def Ellipse(width=10, height=10, center=Point(0, 0)):
  return Gobj(
    { "type": "Ellipse", "width": width, "height": height, "center": center }
  )

def Rectangle(width=10, height=10, center=Point(0, 0)):
  return Gobj(
    { "type": "Rectangle", "width": width, "height": height, "center": center }
  )

def Path(*points):
  return Gobj(
    { "type": "Path", "points": points }
  )

# TODO: Text, Image, and Color

def ultimate_ancestor(obj):
  """
  Returns the Canvas or Layer that the given object resides on, tracing across
  multiple containing objects. Returns the object itself if it has never been
  added to a Canvas or Layer.
  """
  result = obj
  while hasatr(result, "_parent"):
    result = result._parent
  return result

def order_chain(obj):
  """
  Returns a list containing the order in which this object appears in its
  parent's contents list, for each parent or ancestor, starting with the
  ultimate ancestor and continuing deeper towards the given object.
  """
  result = []
  here = obj
  while hasattr(here, "_parent"):
    result.insert(0, here._parent.contents.index(here))
    here = here._parent
  return result

def drawn_over(on_top, on_bottom):
  """
  Returns True if the first fake graphics object will be drawn on top of the
  second. An object on a Canvas or Layer counts as being drawn over that Canvas
  or Layer. Always returns False if the two objects are not ultimately on a
  common Layer or Canvas.
  """
  if ultimate_ancestor(on_top) != ultimate_ancestor(on_bottom):
    return False
  if on_top.depth == on_bottom.depth:
    top_oc = order_chain(on_top)
    bottom_oc = order_chain(on_bottom)
    if len(top_oc) == 0 and len(bottom_oc) > 0:
      return False
    elif len(top_oc) > 0 and len(bottom_oc) == 0:
      return True
    else:
      while len(top_oc) > 0 and len(bottom_oc) > 0:
        top_o = top_oc.pop(0)
        bottom_o = bottom_oc.pop(0)
        if top_o < bottom_o: # top was added earlier
          return False
        elif top_o > bottom_o: # top was added later
          return True
        # else continue while loop with next layer
      # At least one order chain has been exhausted the deeper object wins:
      return len(top_o) > len(bottom_o)
  else:
    return on_top.depth < on_bottom.depth
