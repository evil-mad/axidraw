#!/usr/bin/env python

'''
low_level_usb.py

Demonstrate advanced features of axidraw python module in "interactive" mode.


This demo file shows off the "usb_command" and "usb_query" features of
the interactive API. Interaction through these two commands essentially bypass
all software counters, speed, position, and limit checks that otherwise
ensure safe operations.

While these two "low-level USB" serial interface functions are very direct, they are also
powerful and potentially dangerous. They should be used with reluctance and caution,
since improper use is capable of causing damage of an unpredictable nature.

The serial protocol is documented at:
http://evil-mad.github.io/EggBot/ebb.html


This particular example file demonstrates:
* Moving the carriage away from the home position via moveto
* Querying and printing the firmware version via usb_query
* Querying and printing the step position via usb_query
* Returning to the home position via usb_command


The functions demonstrated here require that the AxiDraw has at least
firmware version 2.6.2. Visit http://axidraw.com/fw for information
about firmware updates.

Run this demo by calling: python low_level_usb.py


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

ad.moveto(2,1)                  # Absolute pen-up move, to (2 inch, 1 inch)

version = ad.usb_query("V\r") # Query firmware version
print("Firmware version data: " + version)

step_pos = ad.usb_query("QS\r") # Query step position
print("Step pos: " + step_pos)

ad.usb_command("HM,3200\r")    # Return home at a rate of 3200 steps per second

ad.disconnect()             # Close serial port to AxiDraw
