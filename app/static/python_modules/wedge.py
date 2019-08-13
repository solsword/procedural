# Fall 2017 PS02
# Sohie Lee 
# wedge.py
# Provides wedge pattern for PS02 Tasks 2 and 3
#
# [lyn, 2018/09/11] Modified to export a makeWedge function rather than a
# bunny layer. This avoids sharing that layer between runs in Codder testing.

from cs1graphics import *

def makeWedge():
    wedge = Polygon(Point(0,0), Point(0,200), Point(300,0))
    wedge.setFillColor('orange')
    return wedge
