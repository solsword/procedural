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

# TODO: Path, Text, Image, and Color
