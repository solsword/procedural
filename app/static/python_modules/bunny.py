# Fall 2017 PS02
# Sohie Lee 
# bunny.py
# Provides bunny pattern for PS02 Tasks 2 and 3
#
# [lyn, 2018/09/11] Modified to export a makeBunny function rather than a
# bunny layer. This avoids sharing that layer between runs in Codder testing.

from cs1graphics import *

def makeBunny():

    bunny = Layer()

    leftEar = Ellipse(40,100,Point(-25,-55))
    leftEar.setFillColor('white')
    leftEar.rotate(-10)
    bunny.add(leftEar)

    rightEar = Ellipse(40,100,Point(25,-55))
    rightEar.setFillColor('white')
    rightEar.rotate(10)
    bunny.add(rightEar)

    leftInnerEar = Ellipse(20,80, Point(-25,-55))
    leftInnerEar.setFillColor('pink')
    leftInnerEar.rotate(-10)
    bunny.add(leftInnerEar)

    rightInnerEar = Ellipse(20,80, Point(25,-55))
    rightInnerEar.setFillColor('pink')
    rightInnerEar.rotate(10)
    bunny.add(rightInnerEar)

    face = Ellipse(105, 95, Point(0,25))
    face.setFillColor('white')
    bunny.add(face)

    nose = Polygon(Point(2,51), Point(-2,51), Point(-10,41), Point(-9, 40), Point(8,40), Point(10, 42))
    nose.setBorderColor('grey')
    nose.setFillColor('grey')
    bunny.add(nose)

    leftEye = Circle(7, Point(-20,15))
    leftEye.setFillColor('lightblue')
    leftEye.setBorderColor('lightblue')
    rightEye = Circle(7, Point(20, 15))
    rightEye.setFillColor('lightblue')
    rightEye.setBorderColor('lightblue')
    bunny.add(leftEye)
    bunny.add(rightEye)

    return bunny 

# done with bunny now
