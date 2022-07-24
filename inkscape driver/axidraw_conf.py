# axidraw_conf.py
# Part of the AxiDraw driver software
# 
# https://github.com/evil-mad/axidraw
# Version 3.4.0, dated 2022-07-22.
#
# Copyright 2022 Windell H. Oskay, Evil Mad Scientist Laboratories
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

const_speed = False     # Use constant velocity mode when pen is down
report_time = False     # Report time elapsed
default_layer = 1       # Layer(s) selected for layers mode (1-1000)

copies = 1              # Copies to plot, or 0 for continuous plotting. Default: 1
page_delay = 15         # Optional delay between copies (s).

preview = False         # Preview mode; simulate plotting only.
rendering = 3           # Preview mode rendering option (0-3):
                            # 0: Do not render previews
                            # 1: Render only pen-down movement
                            # 2: Render only pen-up movement
                            # 3: Render all movement (Default)

model = 1               # AxiDraw Model (1-6)
                            # 1: AxiDraw V2 or V3 (Default). 2: AxiDraw V3/A3 or SE/A3.
                            # 3: AxiDraw V3 XLX. 4: AxiDraw MiniKit.
                            # 5: AxiDraw SE/A1.  6: AxiDraw SE/A2.
                            
port = None             # Serial port or named AxiDraw to use
                            # None (Default) will plot to first unit located

port_config = 0         # Serial port behavior option (0-2)
                            # 0: Plot to first unit found, unless port is specified (Default)
                            # 1: Plot to first AxiDraw unit located
                            # 2: Plot to a specific AxiDraw only, given by port

auto_rotate = True      # Auto-select portrait vs landscape orientation
                            # Default: True

reordering = 0          # Plot optimization option (0-4; 3 is deprecated)
                            # 0: Least; Only connect adjoining paths (Default)
                            # 1: Basic; Also reorder paths for speed
                            # 2: Full; Also allow path reversal
                            # 4: None; Strictly preserve file order

random_start = False    # Randomize start locations of closed paths. (Default: False)

resolution = 1          # Resolution: (1-2):
                            # 1: High resolution (smoother, slightly slower) (Default)
                            # 2: Low resolution (coarser, slightly faster)

digest = 0              # Plot digest output option. (Do NOT enable if using within Inkscape.)
                            # 0: Disabled; No change to behavior or output (Default)
                            # 1: Output "plob" digest, not full SVG, when saving file
                            # 2: Disable plots and previews; generate digest only

webhook = False         # Enable webhook alerts
                            # Default: False

webhook_url = None      # URL for webhook alerts


# Effective motor resolution is approx. 1437 or 2874 steps per inch, in the two modes respectively.
# Note that these resolutions are defined along the native axes of the machine (X+Y) and (X-Y),
# not along the XY axes of the machine. This parameter chooses 8X or 16X motor microstepping.

'''
Additional user-adjustable control parameters:

Values below this point are configured only in this file, not through the user interface(s).
'''

servo_timeout = 60000   # Time, ms, for servo motor to power down 
                        #   after last movement command  (default: 60000)
                        #   This feature requires EBB v 2.5 hardware (with USB
                        #   micro not USB mini connector) and firmware version
                        #   2.6.0 or newer

check_updates = True    # If True, allow AxiDraw Control to check online to see
                        #    what the current software version is, when you
                        #    query the version. Set to False to disable. Note that
                        #    this is the only internet-enabled function in the
                        #    AxiDraw software.

use_b3_out = False      # If True, enable digital output pin B3, which will be high (3.3V)
                        #   when the pen is down, and low otherwise. Can be used to control
                        #   external devices like valves, relays, or lasers.

auto_rotate_ccw = True  # If True (default), auto-rotate is counter-clockwise when active.
                        #   If False, auto-rotate direction is clockwise.

options_message = True  # If True (default), display an advisory message if Apply is clicked
                        #   in the AxiDraw Control GUI, while in tabs that have no effect.
                        #   (Clicking Apply on these tabs has no effect other than the message.)
                        #   This message can prevent the situation where one clicks Apply on the
                        #   Options tab and then waits a few minutes before realizing that
                        #   no plot has been initiated.

report_lifts = False    # Report number of pen lifts when reporting plot duration (Default: False)

auto_clip_lift = True   # Option applicable to the Interactive Python API only.
                        #   If True (default), keep pen up when motion is clipped by travel bounds.

# Colors used to represent pen-up and pen-down travel in preview mode:
preview_color_up = 'LightPink' # Pen-up travel color. Default: LightPink; rgb(255, 182, 193)
preview_color_down = 'Blue'    # Pen-up travel color. Default: Blue; rgb(0, 0, 255)

skip_voltage_check = False  # Set to True to disable EBB input power voltage checks. Default: False

clip_to_page = True  # Clip plotting area to SVG document size. Default: True

min_gap = 0.008     # Automatic path joining threshold, inches. Default: 0.008
                    # If greater than zero, pen-up moves shorter than this distance
                    #   will be replaced by pen-down moves. Set negative to disable.
                    # Setting reordering to 4 (strict) will also disable path joining.

'''
Secondary control parameters:

Values below this point are configured only in this file, not through the user interface(s).
These values have been carefully chosen, and generally do not need to be adjusted in everyday use.
And, you can easily change these values such that things will not work as you expect them to.
That said, proceed with caution, and keep a backup copy.
'''

# Travel area limits typically do not need to be changed. 
# For each model, there is an X travel and Y travel limit, given in inches.

x_travel_default = 11.81 # AxiDraw V2, V3, SE/A4: X.    Default: 11.81 in (300 mm)
y_travel_default = 8.58  # AxiDraw V2, V3, SE/A4: Y.    Default:  8.58 in (218 mm)

x_travel_V3A3 = 16.93    # V3/A3 and SE/A3: X           Default: 16.93 in (430 mm)
y_travel_V3A3 = 11.69    # V3/A3 and SE/A3: Y           Default: 11.69 in (297 mm)

x_travel_V3XLX = 23.42   # AxiDraw V3 XLX: X            Default: 23.42 in (595 mm)
y_travel_V3XLX = 8.58    # AxiDraw V3 XLX: Y            Default:  8.58 in (218 mm)

x_travel_MiniKit = 6.30  # AxiDraw MiniKit: X           Default:  6.30 in (160 mm)
y_travel_MiniKit = 4.00  # AxiDraw MiniKit: Y           Default:  4.00 in (101.6 mm)

x_travel_SEA1 = 34.02    # AxiDraw SE/A1: X             Default: 34.02 in (864 mm)
y_travel_SEA1 = 23.39    # AxiDraw SE/A1: Y             Default: 23.39 in (594 mm)

x_travel_SEA2 = 23.39    # AxiDraw SE/A2: X             Default: 23.39 in (594 mm)
y_travel_SEA2 = 17.01    # AxiDraw SE/A2: Y             Default: 17.01 in (432 mm )

x_travel_V3B6 = 7.48     # AxiDraw V3/B6: X             Default: 7.48 in (190 mm)
y_travel_V3B6 = 5.51     # AxiDraw V3/B6: Y             Default: 5.51 in (140 mm)


native_res_factor = 1016.0  # Motor resolution factor, steps per inch. Default: 1016.0
# Note that resolution is defined along native (not X or Y) axes.
# Resolution is native_res_factor * sqrt(2) steps per inch in Low Resolution  (Approx 1437 steps per inch)
#       and 2 * native_res_factor * sqrt(2) steps per inch in High Resolution (Approx 2874 steps per inch)

max_step_rate = 24.995  # Maximum allowed motor step rate, in steps per millisecond.
# Note that 25 kHz is the absolute maximum step rate for the EBB.
# Movement commands faster than this are ignored; may result in a crash (loss of position control).
# We use a conservative value, to help prevent errors due to rounding.
# This value is normally used _for speed limit checking only_.

speed_lim_xy_lr = 15.000  # Maximum XY speed allowed when in Low Resolution mode, inches/second.  Default: 15.000 Max: 17.3958
speed_lim_xy_hr = 8.6979  # Maximum XY speed allowed when in High Resolution mode, inches/second. Default: 8.6979, Max: 8.6979
# Do not increase these values above Max; they are derived from max_step_rate and the resolution.

max_step_dist_lr = 0.000696  # Maximum distance covered by 1 step in Low Res mode, rounded up, in inches. ~1/(1016 sqrt(2))
max_step_dist_hr = 0.000348  # Maximum distance covered by 1 step in Hi Res mode, rounded up, in inches.  ~1/(2032 sqrt(2))
# In planning trajectories, we skip movements shorter than these distances, likely to be < 1 step.

const_speed_factor_lr = 0.25 # In constant-speed mode, multiply pen-down speed by this factor. Default: 0.25 for Low Res mode
const_speed_factor_hr = 0.4  # In constant-speed mode, multiply pen-down speed by this factor. Default: 0.4 for Hi Res mode

start_pos_x = 0  # Parking position, inches. Default: 0
start_pos_y = 0  # Parking position, inches. Default: 0

# Acceleration & Deceleration rates:
accel_rate = 40.0    # Standard acceleration rate, inches per second squared
accel_rate_pu = 60.0  # Pen-up acceleration rate, inches per second squared

time_slice = 0.025  # Interval, in seconds, of when to update the motors. Default: time_slice = 0.025 (25 ms)

bounds_tolerance = 0.003  # Suppress warnings if bounds are exceeded by less than this distance (inches).

# Servo motion limits, in units of (1/12 MHz), about 83.3 ns:
servo_max = 27831  # Highest allowed position; "100%" on the scale.  Default: 27831 units, or 2.32 ms.
servo_min = 9855   # Lowest allowed position; "0%" on the scale.     Default: 9855 units,  or 0.82 ms.

# Time for servo control signal to sweep over full 0-100% range, at 100% pen lift/lower rates:
servo_sweep_time = 200 # Duration, ms, to sweep servo control signal over 100% range. Default: 200

# Time for pen lift servo to physically move. Time = slope * distance + min, when using a fast sweep.
servo_move_min = 45      # Minimum time, ms, for pen lift/lower of non-zero distance.    Default: 45
servo_move_slope = 2.69  # Additional time, ms, per percentage point of vertical travel. Default: 2.69

smoothness = 10.0       # Curve smoothing (default: 10.0)

cornering = 10.0        # Cornering speed factor (default: 10.0)

# the tolerance for determining when the bezier has been segmented enough to plot:
bezier_segmentation_tolerance = 0.02 / smoothness

# Tolerance for merging nearby vertices:
#  Larger values of segment_supersample_tolerance give smoother plotting along paths that
#  were created with too many vertices. A value of 0 will disable supersampling.
segment_supersample_tolerance = bezier_segmentation_tolerance / 16
