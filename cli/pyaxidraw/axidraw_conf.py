# axidraw_conf.py
# Part of the AxiDraw driver software
# 
# https://github.com/evil-mad/axidraw
# Version 2.5.0, dated 2019-05-13.
#
# Copyright 2019 Windell H. Oskay, Evil Mad Scientist Laboratories
#
# https://github.com/evil-mad/AxiDraw
#
# "Change numbers here, not there." :)


'''
Primary user-adjustable control parameters:

We encourage you to freely tune these values as needed to match the
 behavior and performance of your AxiDraw to your application and taste.

These parameters are used as defaults when using AxiDraw with the command-
 line interface (CLI) or with the python library. With the CLI, you can
 make copies of this configuration file and specify a configuration file.

If you are operating the AxiDraw from within Inkscape, please set your
 preferences within Inkscape, using the AxiDraw Control dialog.
 Most values listed here are ignored when running within Inkscape.
 
Similarly, values set within Inkscape are ignored when using the CLI or
 python library.

'''

# DEFAULT VALUES

speed_pendown = 25      # Maximum plotting speed, when pen is down (1-100)
speed_penup = 75        # Maximum transit speed, when pen is up (1-100)
accel = 75              # Acceleration rate factor (1-100)

pen_pos_up = 60         # Height of pen when raised (0-100)
pen_pos_down = 30       # Height of pen when lowered (0-100)

pen_rate_raise = 75     # Rate of raising pen (1-100)
pen_rate_lower = 50     # Rate of lowering pen (1-100)

pen_delay_up = 0        # Optional delay after pen is raised (ms)
pen_delay_down = 0      # Optional delay after pen is lowered (ms)

const_speed = False     # Use constant velocity mode when pen is down.
report_time = False     # Report time elapsed.
default_layer = 1       # Layer(s) selected for layers mode (1-1000).

copies = 1              # Copies to plot, or 0 for continuous plotting. Default: 1
page_delay = 15         # Optional delay between copies (s).

preview = False         # Preview mode; simulate plotting only.
rendering = 3           # Preview mode rendering option (0-3):
                            # 0: Do not render layers
                            # 1: Render only pen-down movement
                            # 2: Render only pen-up movement
                            # 3: Render all movement (Default)

model = 1               # AxiDraw Model (1-3). 
                            # 1: AxiDraw V2 or V3 (Default).
                            # 2: AxiDraw V3/A3 or SE/A3.
                            # 3: AxiDraw V3 XLX.
                            
port = None             # Serial port or named AxiDraw to use. 
                            # None (Default) will plot to first unit located.

port_config = 0         # Serial port behavior option (0-2)
                            # 0: Plot to first unit found, unless port is specified (Default),
                            # 1: Plot to first AxiDraw unit located
                            # 2: Plot to a specific AxiDraw only, given by port.

auto_rotate = True      # Auto-select portrait vs landscape orientation
                            # Default: True

reordering = 0          # Plot optimization option for how groups are handled
                            # 0: Preserve order of objects given in SVG file (Default).
                            # 1: Reorder objects, preserving groups
                            # 2: Reorder objects, reordering within each group
                            # 3: Reorder all objects, breaking apart groups

resolution = 1          # Resolution: (1-2):
                            # 1: High resolution (smoother, slightly slower) (Default)
                            # 2: Low resolution (coarser, slightly faster)

'''
Additional user-adjustable control parameters:

These parameters are adjustable only from the command line, and are not
visible from within the Inkscape GUI.

'''

check_updates = True  # If True, allow AxiDraw Control to check online to see
                      #    what the current software version is, when you
                      #    query the version. Set to False to disable. Note that
                      #    this is the only internet-enabled function in the
                      #    AxiDraw software.

smoothness = 10.0     # Curve smoothing (default: 10.0)

cornering = 10.0      # Cornering speed factor (default: 10.0)


# Effective motor resolution is approx. 1437 or 2874 steps per inch, in the two modes respectively.
# Note that these resolutions are defined along the native axes of the machine (X+Y) and (X-Y),
# not along the XY axes of the machine. This parameter chooses 8X or 16X microstepping on the motors.


'''
Secondary control parameters:

Values below this point are configured only in this file, not through the user interface(s).
Please note that these values have been carefully chosen, and generally do not need to be 
adjusted in everyday use. That said, proceed with caution, and keep a backup copy.
'''

# Page size values typically do not need to be changed. They primarily affect viewpoint and centering.
# Measured in page pixelssteps.  Default printable area for AxiDraw is 300 x 218 mm

x_travel_default = 11.81  # AxiDraw V2 and AxiDraw V3: X Carriage travel in inches.     Default: 300 mm = about 11.81 inches
y_travel_default = 8.58   # AxiDraw V2 and AxiDraw V3: Y Carriage travel in inches.     Default: 218 mm = about 8.58 inches

x_travel_V3A3 = 16.93     # AxiDraw V3/A3: X Carriage travel in inches.                 Default: 430 mm = about 16.93 inches
y_travel_V3A3 = 11.69     # AxiDraw V3/A3: Y Carriage travel in inches.                 Default: 297 mm = about 11.69 inches

x_travel_V3XLX = 23.42    # AxiDraw V3 XLX: X Carriage travel in inches.                Default: 595 mm = about 23.42 inches
y_travel_V3XLX = 8.58     # AxiDraw V3 XLX: Y Carriage travel in inches.                Default: 218 mm = about 8.58 inches

native_res_factor = 1016.0  # Motor resolution calculation factor, steps per inch, and used in conversions. Default: 1016.0
# Note that resolution is defined along native (not X or Y) axes.
# Resolution is native_res_factor * sqrt(2) steps per inch in Low Resolution  (Approx 1437 steps per inch)
#       and 2 * native_res_factor * sqrt(2) steps per inch in High Resolution (Approx 2874 steps per inch)

max_step_rate = 24.995  # Maximum allowed motor step rate, in steps per millisecond.
# Note that 25 kHz is the absolute maximum step rate for the EBB.
# Movement commands faster than this are ignored; may result in a crash (loss of position control).
# We use a conservative value, to help prevent errors due to rounding.
# This value is normally used _for speed limit checking only_.

speed_lim_xy_lr = 15.000  # Maximum XY speed allowed when in Low Resolution mode, in inches per second.  Default: 15.000 Max: 17.3958
speed_lim_xy_hr = 8.6979  # Maximum XY speed allowed when in High Resolution mode, in inches per second. Default: 8.6979, Max: 8.6979
# Do not increase these values above Max; they are derived from max_step_rate and the resolution.

max_step_dist_lr = 0.000696  # Maximum distance covered by 1 step in Low Res mode, rounded up, in inches. ~1/(1016 sqrt(2))
max_step_dist_hr = 0.000348  # Maximum distance covered by 1 step in Hi Res mode, rounded up, in inches.  ~1/(2032 sqrt(2))
# In planning trajectories, we skip movements shorter than these distances, likely to be < 1 step.

const_speed_factor_lr = 0.25  # When in constant-speed mode, multiply the pen-down speed by this factor. Default: 0.25 for Low Res mode
const_speed_factor_hr = 0.4  # When in constant-speed mode, multiply the pen-down speed by this factor. Default: 0.4 for Hi Res mode

start_pos_x = 0  # Parking position, inches. Default: 0
start_pos_y = 0  # Parking position, inches. Default: 0

# Acceleration & Deceleration rates:
accel_rate = 40.0    # Standard acceleration rate, inches per second squared
accel_rate_pu = 60.0  # Pen-up acceleration rate, inches per second squared

time_slice = 0.025  # Interval, in seconds, of when to update the motors. Default: time_slice = 0.025 (25 ms)

bounds_tolerance = 0.003  # Suppress warnings if bounds are exceeded by less than this distance (inches).

# Allow sufficiently short pen-up moves to be substituted with a pen-down move:
min_gap = 0.008  # Distance Threshold (inches). Default value: 0.008 inches; smaller than most pen lines.

# Servo motion limits, in units of (1/12 MHz), about 83 ns:
servo_max = 27831  # Highest allowed position; "100%" on the scale.    Default value: 25200 units, or 2.31 ms.
servo_min = 9855   # Lowest allowed position; "0%" on the scale.        Default value: 10800 units, or 0.818 ms.

# Note that previous versions of this configuration file used a wider range, 7500 - 28000, corresponding to a range of 625 us - 2333 us.
# The new limiting values are equivalent to 16%, 86% on that prior scale, giving a little less vertical range, but higher resolution.
# More importantly, it constrains the servo to within the travel ranges that they are typically calibrated, following best practice.

skip_voltage_check = False  # Set to True if you would like to disable EBB input power voltage checks. Default: False

clip_to_page = True  # Clip plotting area to SVG document size. Default: True

bezier_segmentation_tolerance = 0.02 / smoothness # the tolerance for determining when the bezier has been segmented enough to plot
segment_supersample_tolerance = bezier_segmentation_tolerance / 16 # the tolerance for determining which segments can be merged
