# axidraw_conf.py
# Part of the AxiDraw driver for Inkscape
# Version 1.0.2, dated January 31, 2015.
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

Speed_Scale = 24950    #Maximum (110%) speed, in steps per second. 
						# Note that 25 kHz is the absolute maximum speed (steps per second) for the EBB.

StartPos_X = 0   #parking position, in pixels. Default: 0
StartPos_Y = 0      #parking position, in pixels. Default: 0


#Perhaps these should have been made editable in the main GUI. Perhaps not. :3
ACCEL_TIME = .25    #Seconds of acceleration to reach full speed WITH PEN DOWN
ACCEL_TIME_PU = 1.0  #Seconds of acceleration to reach full speed WITH PEN UP.

#Short-move pen-up distance threshold, below which we use the faster pen-down acceleration rate:
SHORT_THRESHOLD = 1.0  #Distance Threshold (inches)

#Skip pen-up moves shorter than this distance, when possible:
MIN_GAP = 0.010  #Distance Threshold (inches)


# Servo Setup:
SERVO_MAX = 28000  #Highest allowed position; "100%" on the scale
SERVO_MIN = 7500   #Lowest allowed position; "0%" on the scale

TIME_SLICE = 0.030  #Interval, in seconds, of when to update the motors.

