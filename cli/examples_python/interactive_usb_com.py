#!/usr/bin/env python

'''
interactive_usb_com.py

This demonstration toggles a hobby servo motor, connected to I/O B3,
using advanced features of the AxiDraw Python API.

In doing so, it demonstrates the following "advanced" topics:
* Issuing a "low level" direct EBB USB command
* Querying values of additional configuration parameters

https://axidraw.com/doc/py_api/#usb_command-usb_query
http://evil-mad.github.io/EggBot/ebb.html
https://axidraw.com/doc/py_api/#additional-parameters

Hardware setup (important!):

The pen-lift servo on an AxiDraw V3 is normally connected to output B1,
the *lowest* set of three pins on the AxiDraw's EBB control board, with the
black wire (ground) towards the back of the machine.

To try this demo, connect a hobby servo motor to pins B3, which is the
*highest* set of three pins on the AxiDraw's EBB control board, three positions
above the standard servo motor position. You can disconnect the servo motor
connection from the lowest three pins and moving it to the highest three pins,
keeping the black wire towards the back of the machine.


Note that this example file assumes that a *standard* servo, not a
narrow-band servo is being used for the servo control signal values.


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


import sys
import time

from pyaxidraw import axidraw

PEN_UP_PERCENT = 75         # Percent height that we will use for pen up
PEN_DOWN_PERCENT = 25       # Percent height that we will use for pen down
WAIT_TIME_S = 3             # Time, in seconds, before switching to next position
PORT_PIN = 6                # Logical pin RP6 drives the output labeled "B3", from
                            #    docs at: http://evil-mad.github.io/EggBot/ebb.html#S2

ad = axidraw.AxiDraw() # Initialize class

ad.interactive()            # Enter interactive mode
connected = ad.connect()    # Open serial port to AxiDraw

if not connected:
    sys.exit() # end script

PEN_IS_UP = False       # Initial value of pen state


# Lowest allowed position; "0%" on the scale. Default value: 10800 units, or 0.818 ms.
servo_min = ad.params.servo_min

# Highest allowed position; "100%" on the scale. Default value: 25200 units, or 2.31 ms.
servo_max = ad.params.servo_max

# Optional debug statements:
print("servo_min: " + str(servo_min))
print("servo_max: " + str(servo_max))


servo_range = servo_max - servo_min

pen_up_pos = int (PEN_UP_PERCENT * servo_range / 100 + servo_min)
pen_down_pos = int (PEN_DOWN_PERCENT * servo_range / 100 + servo_min)

index = 0

try:
    while index < 20: # Repeat many times (unless interrupted)

        if PEN_IS_UP:
            position = pen_down_pos
            PEN_IS_UP = False
        else:
            position = pen_up_pos
            PEN_IS_UP = True

        COMMAND = "S2," + str(position) + ',' + str(PORT_PIN) + "\r"

        # Optional debug statements:
        if PEN_IS_UP:
            print("Raising pen")
        else:
            print("Lowering pen")
        print("New servo position: " + str(position))
        print("command: " + COMMAND)

        ad.usb_command(COMMAND + "\r")

        time.sleep(WAIT_TIME_S)
        index += 1

except KeyboardInterrupt:
    ad.disconnect()             # Close serial port to AxiDraw

ad.disconnect()             # Close serial port to AxiDraw in any case.
