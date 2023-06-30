#!/usr/bin/env python

'''
interactive_draw_path.py

Demonstrate use of axidraw module in "interactive" mode, drawing continuous
paths using the draw_path function.

Run this demo by calling: python interactive_draw_path.py


---------------------------------------------------------------------

About the interactive API:

Interactive mode is a mode of use, designed for plotting individual motion
segments upon request, using direct XY control. It is a complement to the
usual plotting modes, which take an SVG document as input.

So long as the AxiDraw is started in the home corner, moves are limit checked,
and constrained to be within the safe travel range of the AxiDraw.


AxiDraw python API documentation is hosted at: https://axidraw.com/doc/py_api/

---------------------------------------------------------------------

About this software:

The AxiDraw writing and drawing machine is a product of Evil Mad Scientist
Laboratories. https://axidraw.com   https://shop.evilmadscientist.com

This open source software is written and maintained by Evil Mad Scientist
to support AxiDraw users across a wide range of applications. Please help
support Evil Mad Scientist and open source software development by purchasing
genuine AxiDraw hardware.

AxiDraw software development is hosted at https://github.com/evil-mad/axidraw

Additional AxiDraw documentation is available at http://axidraw.com/docs

AxiDraw owners may request technical support for this software through our
github issues page, support forums, or by contacting us directly at:
https://shop.evilmadscientist.com/contact

---------------------------------------------------------------------

Copyright 2022 Windell H. Oskay, Evil Mad Scientist Laboratories

The MIT License (MIT)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''

import sys
import math
import time
from pyaxidraw import axidraw

ad = axidraw.AxiDraw() # Initialize class

def print_position():
    '''
    Query, report, and print position and pen state
    '''
    turtle_position = ad.turtle_pos()
    current_position = ad.current_pos()
    print(f"Turtle position: {turtle_position[0]:0.3f}, {turtle_position[1]:0.3f}")
    print(f"Actual position: {current_position[0]:0.3f}, {current_position[1]:0.3f}\n")

ad.interactive()            # Enter interactive mode
connected = ad.connect()    # Open serial port to AxiDraw

if not connected:
    sys.exit() # end script

ad.options.speed_pendown = 10       # set pen-down speed to slow
ad.update()                         # Process changes to options

# Create a path that moves the turtle out of bounds and back:
# Default units are in inches.
vertex_list_1 = [[0,1], [1,1], [3,-1], [5,1]]

print("Draw a path that takes us out of bounds and back:\n")
print("vertex list: " + str(vertex_list_1) + "\n")


ad.draw_path(vertex_list_1) # Plot the path
print("Finished first vertex list, working in inch units. Final pen position:\n")
print_position()
print("Set cm units and repeat with same vertex list, but smaller:\n")


ad.options.units = 1 # Switch to cm units
ad.update() # Process changes to options
ad.draw_path(vertex_list_1) # Plot the path
print_position()

print("Set mm units and draw the same vertex list, even smaller:\n")

ad.options.units = 2 # Switch to cm units
ad.update() # Process changes to options
ad.draw_path(vertex_list_1) # Plot the path
print_position()


ad.options.units = 0 # Switch to inch units
ad.update()                         # Process changes to options


print("Draw a path that takes us out of bounds:\n")

vertex_list_1 = [[0,1], [1,1], [3,-1]]
print("vertex list: " + str(vertex_list_1) + "\n")

ad.draw_path(vertex_list_1) # Plot the path

print("Note that the turtle position and physical position do not agree:\n")
print_position()
time.sleep(1)


print("Increase speed, draw a hexagon:\n")

ad.options.speed_pendown = 20       # set pen-down speed to slow
ad.update()                         # Process changes to options

vertex_list_2 = []
CENTER_X = 1
CENTER_Y = 2
RADIUS = 1
VERTICES = 6

for angle in range(VERTICES + 1):
    x_position = CENTER_X + RADIUS * math.cos(math.tau * angle / VERTICES)
    y_position = CENTER_Y + RADIUS * math.sin(math.tau * angle / VERTICES)
    vertex_list_2.append([x_position, y_position])

ad.draw_path(vertex_list_2) # Plot the path

print("Switching to mm units.\n")

ad.options.units = 2 # Switch to mm units
ad.update() # Process changes to options

print("Draw a circumscribed circle around the hexagon, with 120 segments:\n")

vertex_list_3 = []
CENTER_X = 25.4
CENTER_Y = 50.8
RADIUS = 25.4
VERTICES = 120

for angle in range(VERTICES + 1):
    x_position = CENTER_X + RADIUS * math.cos(math.tau * angle / VERTICES)
    y_position = CENTER_Y + RADIUS * math.sin(math.tau * angle / VERTICES)
    vertex_list_3.append([x_position, y_position])

ad.draw_path(vertex_list_3) # Plot the path


print("Finally, draw some quick squiggles...\n")

ad.options.speed_pendown = 50       # Turn up speed
ad.update()                         # Process changes to options

vertex_list_4 = []
VERTICES = 120
START_X = 75
START_Y = 50.8
Y_RADIUS = 20
X_RADIUS = 4
VERTICES = 400

for vertex in range(VERTICES + 1):
    x_position = START_X + vertex / 10 + X_RADIUS * math.sin(20 * math.tau * vertex / VERTICES)
    y_position = START_Y + Y_RADIUS * math.sin(10 * math.tau * vertex / VERTICES)
    vertex_list_4.append([x_position, y_position])

ad.draw_path(vertex_list_4) # Plot the path
print("And finish back at home.\n")
ad.moveto(0,0)              # Pen-up return home

ad.disconnect()             # Close serial port to AxiDraw
