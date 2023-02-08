# coding=utf-8
#
# Copyright 2023 Windell H. Oskay, Evil Mad Scientist Laboratories
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

'''
pen_handling.py

Classes for managing AxiDraw pen vertical motion and status, plus keeping track
of overall XYZ pen position.

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

The classes defined by this module are:

* PenPosition: Data storage class to hold XYZ pen position

* PenHandler: Main class for managing pen lifting, lowering, and status

* PenHeight: Manage pen-down height settings and keep timing up to date

* PenLiftTiming: Class to calculate and store pen lift timing settings

* PenStatus: Data storage class for pen lift status variables

'''
import time
from axidrawinternal.plot_utils_import import from_dependency_import # plotink
plot_utils = from_dependency_import('plotink.plot_utils')
ebb_serial = from_dependency_import('plotink.ebb_serial')  # https://github.com/evil-mad/plotink
ebb_motion = from_dependency_import('plotink.ebb_motion')
# inkex = from_dependency_import('ink_extensions.inkex')


class PenPosition:
    ''' PenPosition: Class to store XYZ position of pen '''

    def __init__(self):
        self.xpos = 0 # X coordinate
        self.ypos = 0 # Y coordinate
        self.z_up = None # Initialize as None: state unknown.

    def reset(self):
        ''' Reset XYZ positions to default. '''
        self.xpos = 0
        self.ypos = 0
        self.z_up = None

    def reset_z(self):
        ''' Reset Z position only. '''
        self.z_up = None


class PenHeight:
    '''
    PenHeight: Class to manage pen-down height settings.
    Calculate timing for transiting between pen-up and pen-down states.
    '''

    def __init__(self):
        self.pen_pos_down = None # Initial values must be set by update().
        self.use_temp_pen_height = False # Boolean set true while using temporary value
        self.narrow_band = False    # If true, use narrow band servo configuration.
        self.times = PenLiftTiming()

    def update(self, ad_ref):
        '''
        Set initial/default values of options, after __init__.
        Call this function after changing option values to update pen height settings.
        '''
        if not self.use_temp_pen_height:
            self.pen_pos_down = ad_ref.options.pen_pos_down
        self.times.update(ad_ref, self.narrow_band, self.pen_pos_down)

    def set_temp_height(self, ad_ref, temp_height):
        '''
        Begin using temporary pen height position. Return True if the position has changed.
        '''
        self.use_temp_pen_height = True
        if self.pen_pos_down == temp_height:
            return False
        self.pen_pos_down = temp_height

        self.times.update(ad_ref, self.narrow_band, temp_height)
        return True

    def end_temp_height(self, ad_ref):
        '''
        End using temporary pen height position. Return True if the position has changed.
        '''
        self.use_temp_pen_height = False
        if self.pen_pos_down == ad_ref.options.pen_pos_down:
            return False
        self.pen_pos_down = ad_ref.options.pen_pos_down
        self.times.update(ad_ref, self.narrow_band, self.pen_pos_down)
        return True


class PenLiftTiming: # pylint: disable=too-few-public-methods
    '''
    PenTiming: Class to calculate and store time required for pen to lift and lower
    '''

    def __init__(self):
        self.raise_time = None
        self.lower_time = None

    def update(self, ad_ref, narrow_band, pen_down_pos):
        '''
        Compute travel time needed for raising and lowering the pen.

        Call this function after changing option values to update pen timing settings.

        Servo travel time is estimated as the 4th power average (a smooth blend between):
          (A) Servo transit time for fast servo sweeps (t = slope * v_dist + min) and
          (B) Sweep time for slow sweeps (t = v_dist * full_scale_sweep_time / sweep_rate)
        '''
        v_dist = abs(float(ad_ref.options.pen_pos_up - pen_down_pos))

        if narrow_band:
            servo_move_slope = ad_ref.params.nb_servo_move_slope
            servo_move_min = ad_ref.params.nb_servo_move_min
            servo_sweep_time = ad_ref.params.nb_servo_sweep_time
        else:
            servo_move_slope = ad_ref.params.servo_move_slope
            servo_move_min = ad_ref.params.servo_move_min
            servo_sweep_time = ad_ref.params.servo_sweep_time

        # Raising time:
        v_time = int(((servo_move_slope * v_dist + servo_move_min) ** 4 +
            (servo_sweep_time * v_dist / ad_ref.options.pen_rate_raise) ** 4) ** 0.25)
        if v_dist < 0.9:  # If up and down positions are equal, no initial delay
            v_time = 0

        v_time += ad_ref.options.pen_delay_up
        v_time = max(0, v_time)  # Do not allow negative total delay time
        self.raise_time = v_time

        # Lowering time:
        v_time = int(((servo_move_slope * v_dist + servo_move_min) ** 4 +
            (servo_sweep_time * v_dist / ad_ref.options.pen_rate_lower) ** 4) ** 0.25)
        if v_dist < 0.9:  # If up and down positions are equal, no initial delay
            v_time = 0
        v_time += ad_ref.options.pen_delay_down
        v_time = max(0, v_time)  # Do not allow negative total delay time
        self.lower_time = v_time


class PenStatus:
    '''
    PenTiming: Data storage class for pen lift status variables

    pen_up: physical pen up/down state (boolean)
    preview_pen_state: pen state for preview rendering. 0: down, 1: up, -1: changed
    ebblv_set: Boolean; set to True after the pen is physically raised once
    lifts: Counter; keeps track of the number of times the pen is lifted
    '''

    def __init__(self):
        # self.pen_up = None # Initial state: Pen status is unknown.
        self.preview_pen_state = -1 # Will be moved to preview.py in the future
        self.ebblv_set = False
        self.lifts = 0

    def reset(self):
        ''' Clear preview pen state and lift count; Resetting them for a new plot. '''
        self.preview_pen_state = -1  # Will be moved to preview.py in the future
        self.lifts = 0

    def report(self, ad_ref, message_fun):
        ''' report: Print pen lift statistics '''
        if not (ad_ref.options.report_time and ad_ref.params.report_lifts):
            return
        message_fun(f"Number of pen lifts: {self.lifts}\n")


class PenHandler:
    '''
    PenHandler: Main class for managing pen lifting, lowering, and status,
    plus keeping track of XYZ pen position.
    '''

    def __init__(self):
        self.heights = PenHeight()
        self.status  = PenStatus()
        self.phys    = PenPosition() # Physical XYZ pen position
        self.turtle  = PenPosition() # turtle XYZ pen position, for interactive control

    def update(self, ad_ref):
        ''' Function to apply new settings after changing options directly '''
        self.heights.update(ad_ref)

    def reset(self):
        '''
        Reset certain defaults for a new plot:
        Clear pen height and lift count; clear temporary pen height flag.
        These are the defaults that can be set even before options are set.
        '''
        self.status.reset()
        self.heights.use_temp_pen_height = False

    def pen_raise(self, ad_ref):
        ''' Raise the pen '''

        self.status.preview_pen_state = -1 # For preview rendering use

        # Skip if physical pen is already up:
        if self.phys.z_up:
            return

        self.status.lifts += 1

        v_time = self.heights.times.raise_time
        if self.heights.narrow_band:
            servo_pin = ad_ref.params.nb_servo_pin
        else:
            servo_pin = ad_ref.params.servo_pin

        if ad_ref.options.preview:
            ad_ref.preview.v_chart.rest(ad_ref, v_time)
        else:
            ebb_motion.sendPenUp(ad_ref.plot_status.port, v_time, servo_pin, False)
            if (v_time > 50) and (ad_ref.options.mode not in\
                ["manual", "align", "toggle", "cycle"]):
                time.sleep(float(v_time - 30) / 1000.0) # pause before issuing next command
            if ad_ref.params.use_b3_out: # I/O Pin B3 output: low
                ebb_motion.PBOutValue( ad_ref.plot_status.port, 3, 0, False)
        self.phys.z_up = True
        if not self.status.ebblv_set:
            layer_code = 1 + ad_ref.options.pen_pos_up // 2
            if self.heights.narrow_band:
                layer_code += 70
            ebb_motion.setEBBLV(ad_ref.plot_status.port, layer_code, False)
            self.status.ebblv_set = True


    def pen_lower(self, ad_ref):
        ''' Lower the pen '''

        self.status.preview_pen_state = -1  # For preview rendering use

        if self.phys.z_up is not None:
            if not self.phys.z_up:
                return # skip if pen is state is _known_ and is down

        # Skip if stopped:
        if ad_ref.plot_status.stopped:
            return

        v_time = self.heights.times.lower_time

        if self.heights.narrow_band:
            servo_pin = ad_ref.params.nb_servo_pin
        else:
            servo_pin = ad_ref.params.servo_pin

        if ad_ref.options.preview:
            ad_ref.preview.v_chart.rest(ad_ref, v_time)
        else:
            ebb_motion.sendPenDown(ad_ref.plot_status.port, v_time, servo_pin, False)
            if (v_time > 50) and (ad_ref.options.mode not in\
                ["manual", "align", "toggle", "cycle"]):
                time.sleep(float(v_time - 30) / 1000.0) # pause before issuing next command
            if ad_ref.params.use_b3_out: # I/O Pin B3 output: high
                ebb_motion.PBOutValue( ad_ref.plot_status.port, 3, 1, False)
        self.phys.z_up = False


    def toggle(self, ad_ref):
        '''
        Toggle the pen from up to down or vice versa, after determining which state it
        is initially in. Call only after servo_setup_wrapper().
        This function should only be used as a setup utility.
        '''
        if self.phys.z_up:
            self.pen_lower(ad_ref)
        else:
            self.pen_raise(ad_ref)


    def cycle(self, ad_ref):
        '''
        Toggle the pen down and then up, with a 1/2 second delay.
        Call only after servo_setup_wrapper().
        This function should only be used as a setup utility.
        '''
        self.pen_lower(ad_ref)
        ebb_motion.doTimedPause(ad_ref.plot_status.port, 500)
        self.pen_raise(ad_ref)

    def set_temp_height(self, ad_ref, temp_height):
        '''Begin using temporary pen height position'''
        if self.heights.set_temp_height(ad_ref, temp_height):
            self.servo_setup(ad_ref)

    def end_temp_height(self, ad_ref):
        '''End use of temporary pen height position'''
        if self.heights.end_temp_height(ad_ref):
            self.servo_setup(ad_ref)


    def servo_setup_wrapper(self, ad_ref):
        '''
        Utility wrapper for servo_setup(), used for the first time that we address the
        pen-lift servo motor. It is used in manual and setup modes, as well as in various
        plotting modes for initial pen raising/lowering.

        Actions:
        1. Configure servo up & down positions and lifting/lowering speeds.
        2. If current pen up/down state has not yet been set in the status, query EBB to see
            if it knows whether it's in the up or down state. (If so, set our status.)

        Methods:
        When the EBB is reset, it goes to its default "pen up" position. QueryPenUp
        will tell us that the in the pen-up state. However, its actual position is the
        default, not the pen-up position that we've requested.

        To fix this, we could manually command the pen to either the pen-up or pen-down
        position. HOWEVER, that may take as much as five seconds in the very slowest
        speeds, and we want to skip that delay if the pen is already in the right place,
        for example if we're plotting after raising the pen, or plotting twice in a row.

        Solution: Use an otherwise unused EBB firmware variable (EBBLV), which is set to
        zero upon reset. If we set that value to be nonzero, and later find that it's still
        nonzero, we know that the servo position has been set (at least once) since reset.

        Knowing that the pen is up _does not_ confirm that the pen is at the *requested*
        pen-up position, or that it was set to the correct output pin. We encode the
        approximate pen-up height floor(options.pen_pos_up / 2) and whether or not we're
        set for narrow-band servo and store the result in EBBLV, to verify that the current
        position is correct, and that we can skip extra pen-up/pen-down movements.

        We do not _set_ the current correct pen-up value of EBBLV until the pen is raised.
        '''

        self.servo_setup(ad_ref) # Set pen-up/down heights

        if self.phys.z_up is not None:
            return # Pen status is already known; no need to proceed.

        # What follows is code to determine if the initial pen state is known.
        if ad_ref.options.preview:
            self.phys.z_up = True
            return

        if ad_ref.plot_status.port is None:
            return

        # Need to figure out if we're in the pen-up or pen-down state, or indeterminate:
        value = ebb_motion.queryEBBLV(ad_ref.plot_status.port, False)
        if value is None:
            return

        layer_code = 1 + ad_ref.options.pen_pos_up // 2 # Possible range 1 - 51.
        if self.heights.narrow_band: # Possible range for narrow band: 71-121
            layer_code += 70

        if int(value) != layer_code:
            # See "Methods" above for what's going on here.
            ebb_motion.setEBBLV(ad_ref.plot_status.port, 0, False)
            self.status.ebblv_set = False

        else:   # EEBLV has already been set; we can trust the value from QueryPenUp:
                # Note, however, that this does not ensure that the current
                #    Z position matches that in the settings.
            self.status.ebblv_set = True
            if ebb_motion.QueryPenUp(ad_ref.plot_status.port, False):
                self.phys.z_up = True
            else:
                self.phys.z_up = False


    def servo_setup(self, ad_ref):
        '''
        Set servo up/down positions, raising/lowering rates, and power timeout.

        Pen position units range from 0% to 100%, which correspond to a typical timing range of
        9855 - 27831 in units of 83.3 ns (1/(12 MHz)), giving a timing range of 0.82 - 2.32 ms.

        Servo rate options (pen_rate_raise, pen_rate_lower) range from 1% to 100%.
        The EBB servo rate values are in units of 83.3 ns steps per 24 ms.
        Our servo sweep at 100% rate sweeps over 100% range in servo_sweep_time ms.
        '''

        if ad_ref.options.penlift == 3: # (No current models have narrow_band servos by default)
            self.heights.narrow_band = True
        else:
            self.heights.narrow_band = False

        self.heights.update(ad_ref) # Ensure heights and transit times are known
        if ad_ref.options.preview or ad_ref.plot_status.port is None:
            return

        if self.heights.narrow_band:
            servo_max = ad_ref.params.nb_servo_max
            servo_min = ad_ref.params.nb_servo_min
            servo_sweep_time = ad_ref.params.nb_servo_sweep_time
            ebb_serial.command(ad_ref.plot_status.port, 'SC,8,1\r') # 1 channel of servo PWM
            pwm_period = 0.03 # Units are "ms / 100", since pen_rate_raise is a %.
        else:
            servo_max = ad_ref.params.servo_max
            servo_min = ad_ref.params.servo_min
            servo_sweep_time = ad_ref.params.servo_sweep_time
            ebb_serial.command(ad_ref.plot_status.port, 'SC,8,8\r') # 8 channels of servo PWM
            pwm_period = 0.24 # 24 ms: 8 channels at 3 ms each (divided by 100 as above)

        servo_range = servo_max - servo_min
        servo_slope = float(servo_range) / 100.0

        int_temp = int(round(servo_min + servo_slope * ad_ref.options.pen_pos_up))
        ebb_motion.setPenUpPos(ad_ref.plot_status.port, int_temp, False)
        int_temp = int(round(servo_min + servo_slope * self.heights.pen_pos_down))
        ebb_motion.setPenDownPos(ad_ref.plot_status.port, int_temp, False)

        servo_rate_scale = float(servo_range) * pwm_period / servo_sweep_time

        int_temp = int(round(servo_rate_scale * ad_ref.options.pen_rate_raise))
        ebb_motion.setPenUpRate(ad_ref.plot_status.port, int_temp, False)

        int_temp = int(round(servo_rate_scale * ad_ref.options.pen_rate_lower))
        ebb_motion.setPenDownRate(ad_ref.plot_status.port, int_temp, False)

        ebb_motion.servo_timeout(ad_ref.plot_status.port, ad_ref.params.servo_timeout, None, False)

        if ad_ref.params.use_b3_out:  # Configure I/O Pin B3 for use
            ebb_motion.PBOutConfig(ad_ref.plot_status.port, 3, 0, False) # output, low
