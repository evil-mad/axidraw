#!/usr/bin/env python
# -*- encoding: utf-8 -#-

'''
interactive_xy.py

Demonstrate use of axidraw module in "interactive" mode.

Run this demo by calling: python interactive_xy.py


(There is also a separate "plot" mode, which can be used for plotting an
SVG file, rather than moving to various points upon command.)

AxiDraw python API documentation is hosted at: https://axidraw.com/doc/py_api/

'''


'''
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



Copyright 2020 Windell H. Oskay, Evil Mad Scientist Laboratories

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






'''

Interactive mode is a mode of use, designed for plotting individual motion
segments upon request. It is a complement to the usual plotting modes, which
take an SVG document as input.

So long as the AxiDraw is started in the home corner, moves are limit checked,
and constrained to be within the safe travel range of the AxiDraw.



Recommended usage:

ad = axidraw.AxiDraw() # Initialize class
ad.interactive()            # Enter interactive mode

[Optional: Apply custom settings]

ad.connect()                # Open serial port to AxiDraw 

[One or more motion commands]
[Optional: Update settings, followed by calling update().]

ad.disconnect()             # Close connection to AxiDraw


The motion commands are as follows:

goto(x,y)    # Absolute XY move to new location
moveto(x,y)  # Absolute XY pen-up move. Lift pen before moving, if it is down.
lineto(x,y)  # Absolute XY pen-down move. Lower pen before moving, if it is up.

go(x,y)      # XY relative move.
move(x,y)    # XY relative pen-up move. Lift pen before moving, if it is down.
line(x,y)    # XY relative pen-down move. Lower pen before moving, if it is up.

penup()      # lift pen
pendown()    # lower pen


Utility commands:

interactive()   # Enter interactive mode
connect()       # Open serial connection to AxiDraw. Returns True if connected successfully.
update()        # Apply changes to options
disable()       # Disable XY motors, for example to manually move carriage to home position. 
disconnect()    # Terminate serial session to AxiDraw. (Required.)




The available options are as follows:

options.speed_pendown   # Range: 1-110 (percent). 
options.speed_penup     # Range: 1-110 (percent). 
options.accel           # Range: 1-100 (percent). 
options.pen_pos_down    # Range: 0-100 (percent). 
options.pen_pos_up      # Range: 0-100 (percent).
options.pen_rate_lower  # Range: 1-100 (percent).
options.pen_rate_raise  # Range: 1-100 (percent).
options.pen_delay_down  # Range: -500 - 500 (ms).
options.pen_delay_up    # Range: -500 - 500 (ms).
options.const_speed     # True or False. Default: False
options.units	        # Range: 0-1.  0: Inches (default), 1: cm
options.model           # Range: 1-3.   1: AxiDraw V2 or V3 ( Default)
                        #               2: AxiDraw V3/A3
                        #               3: AxiDraw V3 XLX
options.port            # String: Port name or USB nickname
options.port_config     # Range: 0-1.   0: Plot to first unit found, unless port specified. (Default)
                        #               1: Plot to first unit found

One or more options can be set after the interactive() call, and before connect() 
for example as:

ad.options.speed_pendown = 75



All options except port and port_config can be changed after connect(). However,
you must call update() after changing the options and before calling any
additional motion commands.


'''

import sys

from pyaxidraw import axidraw

ad = axidraw.AxiDraw() # Initialize class

ad.interactive()            # Enter interactive mode
connected = ad.connect()    # Open serial port to AxiDraw 

if not connected:
    sys.exit() # end script
    
    
# Draw square, using "moveto/lineto" (absolute move) syntax:

ad.moveto(1,1)              # Absolute pen-up move, to (1 inch, 1 inch)
ad.lineto(2,1)              # Absolute pen-down move, to (2 inches, 1 inch)
ad.lineto(2,2)              
ad.lineto(1,2) 
ad.lineto(1,1)              # Finish drawing square
ad.moveto(0,0)              # Absolute pen-up move, back to origin.


# Change some options:
ad.options.units = 1        # set working units to cm.
ad.options.speed_pendown = 10     # set pen-down speed to slow
ad.update()                 # Process changes to options 


# Draw an "X" through the square, using "move/line" (relative move) syntax:
# Note that we have just changed the units to be in  cm.

ad.move(5.08,5.08)          # Relative move to (2 inches,2 inches), in cm
ad.line(-2.54,-2.54)        # Relative move 2.54 cm in X and Y
ad.move(0,2.54)
ad.line(2.54,-2.54)         # Relative move 2.54 cm in X and Y

ad.moveto(0,0)              # Return home


# Change some options, just to show how we do so:
ad.options.units = 0        # set working units back to inches.
ad.options.speed_pendown = 75     # set pen-down speed to fast
ad.options.pen_rate_lower = 10 # Set pen down very slowly
ad.update()                 # Process changes to options 


# Draw a "+" through the square, using "go/goto" commands,
# which do not automatically set the pen up or down:

ad.goto(1.5,1.0)
ad.pendown()
ad.go(0,1)
ad.penup()
ad.goto(1.0,1.5)
ad.pendown()
ad.go(1,0)
ad.penup()

ad.goto(0,0)                # Return home


ad.disconnect()             # Close serial port to AxiDraw