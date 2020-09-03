#!/usr/bin/env python
# -*- encoding: utf-8 -#-

'''
interactive_penheights.py

Demonstrate use of axidraw module in "interactive" mode.

Set pen to different heights.

Run this demo by calling: python interactive_penheights.py

'''

import sys
import time

from pyaxidraw import axidraw

ad = axidraw.AxiDraw() # Initialize class

ad.interactive()            # Enter interactive mode
connected = ad.connect()    # Open serial port to AxiDraw 

if not connected:
    sys.exit() # end script
    
ad.penup()

# Change some options, just to show how we do so:

ad.options.pen_pos_down = 40
ad.options.pen_pos_up = 60
ad.update()                 # Process changes to options 

ad.pendown()
time.sleep(1.0) 
ad.penup()
time.sleep(1.0) 

ad.options.pen_pos_down = 0
ad.options.pen_pos_up = 100

ad.update()                 # Process changes to options 

ad.pendown()
time.sleep(1.0) 
ad.penup()

ad.disconnect()             # Close serial port to AxiDraw