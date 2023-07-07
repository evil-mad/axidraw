#!/usr/bin/env python

'''
interactive_xy.py

Demonstrate use of axidraw module in "interactive" mode.

Run this demo by calling: python interactive_xy.py


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

from pyaxidraw import axidraw

ad = axidraw.AxiDraw() # Initialize class

ad.interactive()            # Enter interactive mode
connected = ad.connect()    # Open serial port to AxiDraw

if not connected:
    sys.exit() # end script

# Draw square, using "moveto/lineto" (absolute move) syntax:

ad.moveto(1, 1)              # Absolute pen-up move, to (1 inch, 1 inch)
ad.lineto(2, 1)              # Absolute pen-down move, to (2 inches, 1 inch)
ad.lineto(2, 2)
ad.lineto(1, 2)
ad.lineto(1, 1)              # Finish drawing square
ad.moveto(0, 0)              # Absolute pen-up move, back to origin.

ad.delay(2000)              # Delay 2 seconds

# Change some options:
ad.options.units = 1              # set working units to cm.
ad.options.speed_pendown = 10     # set pen-down speed to slow
ad.options.pen_pos_up = 90        # select a large range for the pen up/down swing
ad.options.pen_pos_down = 10

ad.update()                 # Process changes to options

# Draw an "X" through the square, using "move/line" (relative move) syntax:
# Note that we have just changed the units to be in cm.

ad.move(5.08, 5.08)          # Relative move to (2 inches,2 inches), in cm
ad.line(-2.54, -2.54)        # Relative move 2.54 cm in X and Y
ad.move(0, 2.54)
ad.line(2.54, -2.54)         # Relative move 2.54 cm in X and Y

ad.moveto(0, 0)              # Return home


# Change some options, just to show how we do so:
ad.options.units = 0        # set working units back to inches.
ad.options.speed_pendown = 75     # set pen-down speed to fast
ad.options.pen_rate_lower = 10 # Set pen down very slowly
ad.update()                 # Process changes to options


# Draw a "+" through the square, using "go/goto" commands,
# which do not automatically set the pen up or down:

ad.goto(1.5, 1.0)
ad.pendown()
ad.go(0,1)
ad.penup()
ad.goto(1.0, 1.5)
ad.pendown()
ad.go(1,0)
ad.penup()

ad.goto(0, 0)                # Return home

ad.disconnect()             # Close serial port to AxiDraw
