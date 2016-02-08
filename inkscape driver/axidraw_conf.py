# axidraw_conf.py
# Part of the AxiDraw driver for Inkscape
# Version 1.0.0, dated January 31, 2015.
#
# https://github.com/evil-mad/AxiDraw
#
# "Change numbers here, not there." :)



# Page size values typically do not need to be changed. They primarily affect viewpoint and centering.
# Measured in page pixelssteps.  Default printable area for AxiDraw is 300 x 218 mm

N_PAGE_HEIGHT = 8.58     # Default page height in inches 	218 mm = about 8.58 inches
N_PAGE_WIDTH = 11.81      # Default page width in inches 	300 mm = about 11.81 inches


#Machine resolution: Used in converting drawing size to motor steps.
DPI_16X = 2032       #DPI ("dots per inch") @ 16X microstepping.  Standard value: 2032, or 80 steps per mm.  

StartPos_X = 0   #parking position, in pixels. Default: 0
StartPos_Y = 0      #parking position, in pixels. Default: 0

Speed_Scale = 25000    #Default maximum (100%) speed, in steps per second . If value is 20000 (default), 50% speed will be 10000 steps/s.

ACCEL_TIME = 1.0    #Number of seconds of acceleration required to reach full speed



# Servo Setup:
SERVO_MAX = 28000  #Highest allowed position; "100%" on the scale
SERVO_MIN = 7500   #Lowest allowed position; "0%" on the scale



