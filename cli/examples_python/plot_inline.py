#!/usr/bin/env python

'''
plot_inline.py

Demonstrate use of axidraw module in "plot" mode, to plot SVG without
using a separate SVG file.

Run this demo by calling: python plot_inline.py


This is a short example to show how one can:
* Import the AxiDraw module
* Compose a string containing SVG -- what would be an SVG file *if* we saved it.
* Plot that SVG string with the AxiDraw.

---------------------------------------------------------------------

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

Copyright 2023 Windell H. Oskay, Evil Mad Scientist Laboratories

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


import random
from pyaxidraw import axidraw

ad = axidraw.AxiDraw()             # Create class instance

"""
Compose an SVG document as a string.

The head and tail are "boilerplate" for an A4 size page, 297 x 210 mm
in landscape format.

We will add to the document a circle, rectangle, and two paths, hardcoded

We will also add a random ellipse, that will be different each time that
you run the script

"""

SVG_HEAD = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
    <svg
        xmlns:dc="http://purl.org/dc/elements/1.1/"
        xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        xmlns:svg="http://www.w3.org/2000/svg"
        xmlns="http://www.w3.org/2000/svg"
        version="1.1"
        id="plot_inline_example"
        viewBox="0 0 297 210"
        height="210mm"
        width="297mm">
    """

SVG_TAIL = "</svg>"

# Add a circle at X = 40 mm, Y = 30 mm, r = 10 mm
SVG_BODY = """<circle
        r="10"
        cy="30"
        cx="40"
        id="circle1" />
        """

# Add a rectangle at X = 10 mm, Y = 10 mm, width = 50 mm, height = 10 mm
SVG_BODY += """<rect
        x="10"
        y="10"
        width="50"
        height="10"
        id="rect1" />
        """

# Add a path starting at 70,40, using absolute Moveto (M) and absolute Lineto (L) commands.
#   Additional coordinate pairs following L X,Y are additional lineto coordinates.
SVG_BODY += """<path
        d="M 70,40 L 70,30 80,30 80,40 90,40 90,30 100,30 100,40 M 110,40 L 110,30 120,30 120,40 130,40 130,30 140,30 140,40"
        id="path1" />
        """

# Add a similar path starting at 70,70, using relative moveto (m) and relative lineto (l) commands.
#   (except for the first absolute move)

SVG_BODY += """<path
        d="M 70,70 l0,-10 10,0 0,10 10,0 0,-10 10,0 0,10 m10,0 l0,-10 10,0 0,10 10,0 0,-10 10,0 0,10"
        id="path2" />
        """

# Add a programmatic ellipse, with randomly generated size and position.
# This will be different every time that you run this script.

cx = 20 + 80 * random.random()
cy = 20 + 40 * random.random()
rx = 20 * random.random()
ry = 20 * random.random()

RANDOM_ELLIPSE = '<ellipse rx="{:f}" ry="{:f}" cx="{:f}" cy="{:f}" id="rand" />'
RANDOM_ELLIPSE = RANDOM_ELLIPSE.format( rx, ry, cx, cy)

SVG_BODY += RANDOM_ELLIPSE


SVG = SVG_HEAD + SVG_BODY + SVG_TAIL

ad.plot_setup(SVG)    # Parse the SVG

ad.options.speed_pendown = 50 # Set maximum pen-down speed to 50%


'''
See documentation for a description of additional options and their allowed values:
https://axidraw.com/doc/py_api/

'''

ad.plot_run()   # plot the document
