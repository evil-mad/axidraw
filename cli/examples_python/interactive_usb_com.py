#!/usr/bin/env python
# -*- encoding: utf-8 -#-
from __future__ import print_function

'''
interactive_usb_com.py

This demonstration toggles a hobby servo motor, connected to I/O B3.

In doing so, it demonstrates the following "advanced" topics:
* Issuing a "low level" direct EBB USB command
* Querying values of additional configuration parameters

https://axidraw.com/doc/py_api/#usb_command-usb_query
http://evil-mad.github.io/EggBot/ebb.html
https://axidraw.com/doc/py_api/#additional-parameters


* This script will run continuously until interrupted. *


Hardware setup:

The pen-lift servo on an AxiDraw V3 is normally connected to output B1,
the *lowest* set of three pins on the AxiDraw's EBB control board, with the
black wire (ground) towards the back of the machine. 

To try this demo, connect a hobby servo motor to pins B3, which is the 
*highest* set of three pins on the AxiDraw's EBB control board, three positions
above the standard servo motor position. You can disconnect the servo motor
connection from the lowest three pins and moving it to the highest three pins,
keeping the black wire towards the back of the machine.

'''

import sys
import time

from pyaxidraw import axidraw


pen_up_percent = 75         # Percent height that we will use for pen up
pen_down_percent = 25       # Percent height that we will use for pen down
wait_time_s = 3             # Time, in seconds, before switching to next position
port_pin = 6                # Logical pin RP6 drives the output labeled "B3", from
                            #    docs at: http://evil-mad.github.io/EggBot/ebb.html#S2


ad = axidraw.AxiDraw() # Initialize class

ad.interactive()            # Enter interactive mode
connected = ad.connect()    # Open serial port to AxiDraw 

if not connected:
    sys.exit() # end script

pen_is_up = False       # Initial value of pen state


# Lowest allowed position; "0%" on the scale. Default value: 10800 units, or 0.818 ms.
servo_min = ad.params.servo_min

# Highest allowed position; "100%" on the scale. Default value: 25200 units, or 2.31 ms.
servo_max = ad.params.servo_max  

# Optional debug statements:
print("servo_min: " + str(servo_min))
print("servo_max: " + str(servo_max))


servo_range = servo_max - servo_min

pen_up_pos = int (pen_up_percent * servo_range / 100 + servo_min)
pen_down_pos = int (pen_down_percent * servo_range / 100 + servo_min)

try:
    while True: # Repeat until interrupted

        if pen_is_up:
            position = pen_down_pos
            pen_is_up = False
        else:
            position = pen_up_pos
            pen_is_up = True
    
        command = "S2," + str(position) + ',' + str(port_pin) + "\r"
    
        # Optional debug statements:
        if pen_is_up:
            print("Raising pen")
        else:
            print("Lowering pen")
        print("New servo position: " + str(position))
        print("command: " + command)
    
        ad.usb_command(command + "\r") 
    
        time.sleep(wait_time_s) 

except KeyboardInterrupt:
    ad.disconnect()             # Close serial port to AxiDraw

