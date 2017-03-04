# axidraw_conf.py
# Part of the AxiDraw driver for Inkscape
# Version 1.3, dated March 2, 2017.
#
# https://github.com/evil-mad/AxiDraw
#
# "Change numbers here, not there." :)



#Primary default values, normally set via GUI:
PenUpPos = 60			# Default pen-up position
PenDownPos = 40		# Default pen-down position

PenUpSpeed = 75
PenDownSpeed = 25

PenLowerDelay = 0		# added delay (ms) for the pen to go down before the next move
PenRaiseDelay = 0		# added delay (ms) for the pen to go up before the next move

PenRaiseRate = 150		# Default pen-lift servo speed 
PenLowerRate = 150		# Default pen-lift servo speed when lowering
DefaultLayer = 1		# Default inkscape layer


#Command-line defaults: Not visible from within Inkscape GUI.
fileOutput = False		# If True: Output updated contents of SVG on stdout. 



# Values below this point generally do not need to be changed in everyday use. Proceed with caution.

# Page size values typically do not need to be changed. They primarily affect viewpoint and centering.
# Measured in page pixelssteps.  Default printable area for AxiDraw is 300 x 218 mm

PageWidthIn = 11.81		# Default page width in inches 	300 mm = about 11.81 inches
PageHeightIn = 8.58		# Default page height in inches 	218 mm = about 8.58 inches


#Machine resolution: Used in converting drawing size to motor steps.
DPI_16X = 2032			#DPI ("dots per inch") @ 16X microstepping.  Standard value: 2032, or 80 steps per mm.  

SpeedScale = 24950		#Maximum (110%) speed, in steps per second. 
						# Note that 25 kHz is the absolute maximum speed (steps per second) for the EBB.

StartPosX = 0			#parking position, in pixels. Default: 0
StartPosY = 0			#parking position, in pixels. Default: 0


#Perhaps these should have been made editable in the main GUI. Perhaps not. :3
AccelTime = .2			#Seconds of acceleration to reach full speed WITH PEN DOWN
AccelTimePU = .5		#Seconds of acceleration to reach full speed WITH PEN UP.
AccelTimePUHR = .15		#Seconds of acceleration to reach full speed WITH PEN UP in slower high-res mode.

#Short-move pen-up distance threshold, below which we use the faster pen-down acceleration rate:
ShortThreshold = 1.0	#Distance Threshold (inches)


#Skip pen-up moves shorter than this distance, when possible:
MinGap = 0.010			#Distance Threshold (inches)


# Servo Setup:
ServoMax = 28000		#Highest allowed position; "100%" on the scale
ServoMin = 7500			#Lowest allowed position; "0%" on the scale

TimeSlice = 0.025		#Interval, in seconds, of when to update the motors.
