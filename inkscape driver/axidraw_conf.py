# axidraw_conf.py
# Part of the AxiDraw driver software
#
# https://github.com/evil-mad/axidraw
# Version 3.9.0, dated 2023-05-11.
#
# Copyright 2023 Windell H. Oskay, Evil Mad Scientist Laboratories
#
# https://github.com/evil-mad/AxiDraw
#
# "Change numbers here, not there." :)


'''
Primary user-adjustable control parameters:

We encourage you to freely tune these values as needed to match the
 behavior and performance of your AxiDraw to your application and taste.

These parameters are used as defaults when using AxiDraw with the command-
 line interface (CLI) or with the python API. With the CLI, you can make
 copies of this configuration file and specify one as a configuration file.
 When using the Python API, override individual settings within your script.

 If you are operating the AxiDraw from within Inkscape, please set your
  preferences within Inkscape, using the AxiDraw Control dialog. Settings
  that appear both here and in AxiDraw Control will be ignored; those
  from AxiDraw Control will be used. Other settings can be configured here.

Settings within Inkscape only affect use within Inkscape, and do not affect
 the behavior of the AxiDraw CLI or Python APIs.

'''

# DEFAULT VALUES

mode = 'plot'           # Operational mode or GUI tab. Default: 'plot'

speed_pendown = 25      # Maximum plotting speed, when pen is down (1-100). Default 25
speed_penup = 75        # Maximum transit speed, when pen is up (1-100). Default 75
accel = 75              # Acceleration rate factor (1-100). Default 75

pen_pos_up = 60         # Height of pen when raised (0-100). Default 60
pen_pos_down = 30       # Height of pen when lowered (0-100). Default 30

pen_rate_raise = 75     # Rate of raising pen (1-100). Default 75
pen_rate_lower = 50     # Rate of lowering pen (1-100). Default 50

pen_delay_up = 0        # Optional delay after pen is raised (ms). Default 0
pen_delay_down = 0      # Optional delay after pen is lowered (ms). Default 0

const_speed = False     # Use constant velocity mode when pen is down. Default False
report_time = False     # Report time elapsed. Default False

default_layer = 1       # Layer(s) selected for layers mode (1-1000). Default 1

manual_cmd = 'fw_version'   # Manual command to execute when in manual mode.
                            # Default 'fw_version'

dist = 1.0              # Distance to walk in "walking" manual commands or changing
                            # resume position in the APIs. Variable units. Default 1.0

copies = 1              # Copies to plot, or 0 for continuous plotting. Default: 1
page_delay = 15         # Optional delay between copies (s). Default 15

preview = False         # Preview mode; simulate plotting only. Default False
rendering = 3           # Preview mode rendering option (0-3):
                            # 0: Do not render previews
                            # 1: Render only pen-down movement
                            # 2: Render only pen-up movement
                            # 3: Render all movement (Default)

model = 1               # AxiDraw Model (1-6).
                            # 1: AxiDraw V2 or V3 (Default). 2: AxiDraw V3/A3 or SE/A3.
                            # 3: AxiDraw V3 XLX. 4: AxiDraw MiniKit.
                            # 5: AxiDraw SE/A1.  6: AxiDraw SE/A2.

penlift = 1             # pen lift servo configuration (1-3).
                            # 1: Default for AxiDraw model
                            # 2: Standard servo (lowest connector position)
                            # 3: Narrow-band brushless servo (3rd position up)

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

random_start = False    # Randomize start locations of closed paths. Default False

hiding = False          # Hidden-line removal. Default: False

webhook = False         # Enable webhook alerts when True
                            # Default False

webhook_url = None      # URL for webhook alerts. Default None

digest = 0              # Plot digest output option. (NOT supported in Inkscape context.)
                            # 0: Disabled; No change to behavior or output (Default)
                            # 1: Output "plob" digest, not full SVG, when saving file
                            # 2: Disable plots and previews; generate digest only

progress = False        # Enable progress bar display in AxiDraw CLI, when True
                            # Default False
                            # This option has no effect in Inkscape or Python API contexts.

resolution = 1          # Resolution: (1-2):
                            # 1: High resolution (smoother, slightly slower) (Default)
                            # 2: Low resolution (coarser, slightly faster)

# Effective motor resolution is approx. 1437 or 2874 steps per inch, in the two modes respectively.
# Note that these resolutions are defined along the native axes of the machine (X+Y) and (X-Y),
# not along the XY axes of the machine. This parameter chooses 8X or 16X motor microstepping.

'''
Additional user-adjustable control parameters.
Values below this point are configured only in this file, not through the user interface(s).
'''

servo_timeout = 60000   # Time, ms, for servo motor to power down after last movement command
                        #   (default: 60000). This feature requires EBB v 2.5 hardware (with USB
                        #   micro not USB mini connector), firmware version 2.6.0, and
                        #   servo_pin set to 1 (only).

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

auto_clip_lift = True   # Option applicable only to XY movements in the Interactive Python API.
                        #   If True (default), keep pen up when motion is clipped by travel bounds.

# Colors used to represent pen-up and pen-down travel in preview mode:
preview_color_up = 'LightPink' # Pen-up travel color. Default: LightPink; rgb(255, 182, 193)
preview_color_down = 'Blue'    # Pen-up travel color. Default: Blue; rgb(0, 0, 255)

skip_voltage_check = False  # Set to True to disable EBB input power voltage checks. Default: False

clip_to_page = True  # Clip plotting area to SVG document size. Default: True

min_gap = 0.006     # Automatic path joining threshold, inches. Default: 0.006
                    # If greater than zero, pen-up moves shorter than this distance
                    #   will be replaced by pen-down moves. Set negative to disable.
                    # Setting reordering to 4 (strict) will also disable path joining.

'''
Secondary control parameters:

Values below this point are configured only in this file, not through the user interface(s).
These values are carefully chosen, and generally do not need to be adjusted in everyday use.
Be aware that one can easily change these values such that things will not work properly,
or at least not how you expect them to. Edit with caution, and keep a backup copy.
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


''' Configuration for standard pen-lift servo motor '''
servo_pin = 1           # EBB I/O pin number (port B) to control the pen-lift servo motor.
                        #   Default: 1 (pin RB1).

# Servo motion limits, in units of (1/12 MHz), about 83.3 ns:
servo_max = 27831       # Up at "100%" position. Default: 27831 83.3 ns units, or 2.32 ms.
servo_min = 9855        # Down at "0%" position. Default: 9855 83.3 ns units,  or 0.82 ms.

# Time for servo control signal to sweep over full 0-100% range, at 100% pen lift/lower rates:
servo_sweep_time = 200 # Duration, ms, to sweep control signal over 100% range. Default: 200

# Time (for pen lift servo to physically move) = slope * distance + min, with a full speed sweep.
servo_move_min = 45      # Minimum time, ms, for pen lift/lower of non-zero distance. Default: 45
servo_move_slope = 2.69  # Additional time, ms, per % of vertical travel.    Default: 2.69

''' Configuration for narrow-band brushless pen-lift servo motor '''
nb_servo_pin = 2        # EBB I/O pin number (port B) to control the pen-lift servo motor.
                        #   Default:2 (pin RB2, two positions above the standard servo output pins).

# Servo motion limits, in units of (1/12 MHz), about 83.3 ns:
nb_servo_max = 12600    # Up at "100%" position. Default: 12600 83.3 ns units, or 1.05 ms.
nb_servo_min = 5400     # Down at "0%" position. Default: 5400 83.3 ns units,  or 0.45 ms.

# Time for servo control signal to sweep over full 0-100% range, at 100% pen lift/lower rates:
nb_servo_sweep_time = 70 # Duration, ms, to sweep control signal over 100% range. Default: 70

# Time (for pen lift servo to physically move) = slope * distance + min, with a full speed sweep.
nb_servo_move_min = 20      # Minimum time, ms, for pen lift/lower of non-zero distance. Default: 20
nb_servo_move_slope = 1.28  # Additional time, ms, per % of vertical travel.    Default: 1.28


''' Additional Secondary control parameters: '''

native_res_factor = 1016.0  # Motor resolution factor, steps per inch. Default: 1016.0
# Note that resolution is defined along native (not X or Y) axes.
# Resolution is native_res_factor * sqrt(2) steps/inch in Low Resolution  (Approx 1437 steps/in)
#       and 2 * native_res_factor * sqrt(2) steps/inch in High Resolution (Approx 2874 steps/in)

max_step_rate = 24.995  # Maximum allowed motor step rate, in steps per millisecond.
# Note that 25 kHz is the absolute maximum step rate for the EBB.
# Movement commands faster than this are ignored; may result in a crash (loss of position control).
# We use a conservative value, to help prevent errors due to rounding.
# This value is normally used _for speed limit checking only_.

speed_lim_xy_lr = 15.000  # Max XY speed allowed when in Low Resolution mode, in/s.  Default: 15.000 Max: 17.3958
speed_lim_xy_hr = 8.6979  # Max XY speed allowed when in High Resolution mode, in/s. Default: 8.6979, Max: 8.6979
# Do not increase these values above Max; they are derived from max_step_rate and the resolution.

max_step_dist_lr = 0.000696  # Max distance covered by 1 step in Low Res mode, rounded up, in inches. ~1/(1016 sqrt(2))
max_step_dist_hr = 0.000348  # Max distance covered by 1 step in Hi Res mode, rounded up, in inches.  ~1/(2032 sqrt(2))
# In planning trajectories, we skip movements shorter than these distances, likely to be < 1 step.

const_speed_factor_lr = 0.25 # In constant-speed mode, multiply pen-down speed by this factor. Default: 0.25 for Low Res mode
const_speed_factor_hr = 0.4  # In constant-speed mode, multiply pen-down speed by this factor. Default: 0.4 for Hi Res mode

start_pos_x = 0  # Parking position, inches. Default: 0
start_pos_y = 0  # Parking position, inches. Default: 0

# Acceleration & Deceleration rates:
accel_rate = 40.0    # Standard acceleration rate, inches per second squared
accel_rate_pu = 60.0  # Pen-up acceleration rate, inches per second squared

time_slice = 0.025  # Interval, in seconds, of when to update the motors. Default: 0.025 (25 ms)

button_interval = 0.05  # Minimum interval (s), for polling pause button. Default: 0.05 (50 ms)

bounds_tolerance = 0.003  # Suppress warnings if bounds are exceeded by less than this distance (inches).

cornering = 10.0        # Cornering speed factor (default: 10.0)

# Maximum allowed deviation of path segments from that given by the original Bezier curves
curve_tolerance = 0.002 # Curve representation tolerance, inches. Default: 0.002 (0.05 mm)

# Tolerance for merging nearby vertices:
#  Larger values of segment_supersample_tolerance give smoother plotting along paths that
#  were created with too many vertices. A value of 0 will disable supersampling.
segment_supersample_tolerance = curve_tolerance / 10 # default: curve_tolerance / 10
