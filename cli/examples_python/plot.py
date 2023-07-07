#!/usr/bin/env python

'''
plot.py

Demonstrate use of axidraw module in "plot" mode, to plot an SVG file.

Run this demo by calling: python plot.py


This is a minimal example to show how one can import the AxiDraw module
and use it to plot an SVG file with the AxiDraw.

(There is also a separate "interactive" mode, which can be used for moving
the AxiDraw to various points upon command, rather than plotting an SVG file.)

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
import os.path
from pyaxidraw import axidraw

ad = axidraw.AxiDraw()             # Create class instance

'''
Try a few different possible locations for our file,
so that this can be called from either the root or examples_python directory,
or if you're in the same directory with the file.
'''

LOCATION1 = "test/assets/AxiDraw_trivial.svg"
LOCATION2 = "../test/assets/AxiDraw_trivial.svg"
LOCATION3 = "AxiDraw_trivial.svg"

FILE = None

if os.path.exists(LOCATION1):
    FILE = LOCATION1
if os.path.exists(LOCATION2):
    FILE = LOCATION2
if os.path.exists(LOCATION3):
    FILE = LOCATION3

if FILE:
    print("Example file located at: " + FILE)
    ad.plot_setup(FILE)    # Parse the input file
else:
    print("Unable to locate example file; exiting.")
    sys.exit() # end script

# The above code, starting with "LOCATION1" can all be replaced by a single line
# if you already know where the file is. This can be as simple as:
# ad.plot_setup("AxiDraw_trivial.svg")

ad.options.speed_pendown = 50 # Set maximum pen-down speed to 50%

'''
See documentation for a description of additional options and their allowed values:
https://axidraw.com/doc/py_api/
'''

ad.plot_run()   # plot the document
