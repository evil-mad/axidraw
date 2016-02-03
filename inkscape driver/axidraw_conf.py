# axidraw_conf.py
# Part of the AxiDraw driver for Inkscape
# Version 1.0.0, dated January 31, 2015.
#
# https://github.com/evil-mad/AxiDraw
#
# "Change numbers here, not there." :)



# Page size values typically do not need to be changed. They primarily affect viewpoint and centering.
# Measured in page pixelssteps.  Default printable area for AxiDraw is 300 x 218 mm

N_PAGE_HEIGHT = 773     # Default page height in pixels (@ 90 px/inch) 	218 mm = about 8.58 inches
N_PAGE_WIDTH = 1063      # Default page width in pixels (@ 90 px/inch) 	300 mm = about 11.81 inches


#Machine resolution: Used in converting drawing size to motor steps.
F_DPI_16X = 2032       #DPI @ 16X microstepping.  Standard value: 2032, or 80 steps per mm.  

F_StartPos_X = 0   #parking position, in pixels. Default: 0
F_StartPos_Y = 0      #parking position, in pixels. Default: 0

F_Speed_Scale = 20000    #Default 100% speed, in steps per ms . If value is 500 (default), 100% speed will be 5000 steps/s.


# Servo Setup:
SERVO_MAX = 28000  #Highest allowed position; "100%" on the scale
SERVO_MIN = 7500   #Lowest allowed position; "0%" on the scale



