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

    preview_pen_state: pen state for preview rendering. 0: down, 1: up, -1: changed
    lifts: Counter; keeps track of the number of times the pen is lifted
    config: List of last [pen_pos_up, pen_pos_down, narrow_band]
    '''

    def __init__(self):
        self.preview_pen_state = -1 # Will be moved to preview.py in the future
        self.lifts = 0
        self.config = [-1, -1, False] # [pen_pos_up, pen_pos_down, narrow_band]

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
                ["manual", "align", "cycle"]):
                time.sleep(float(v_time - 30) / 1000.0) # pause before issuing next command
            if ad_ref.params.use_b3_out: # I/O Pin B3 output: low
                ebb_motion.PBOutValue( ad_ref.plot_status.port, 3, 0, False)
        self.phys.z_up = True


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
                ["manual", "align", "cycle"]):
                time.sleep(float(v_time - 30) / 1000.0) # pause before issuing next command
            if ad_ref.params.use_b3_out: # I/O Pin B3 output: high
                ebb_motion.PBOutValue( ad_ref.plot_status.port, 3, 1, False)
        self.phys.z_up = False

    def cycle(self, ad_ref):
        '''
        Toggle the pen down and then up, with a 1/2 second delay.
        Call only after servo_init(), which lowers the pen when initializing.
        This function should only be used as a setup utility.
        '''
        ebb_motion.doTimedPause(ad_ref.plot_status.port, 500)
        self.pen_raise(ad_ref)

    def set_temp_height(self, ad_ref, temp_height):
        '''Begin using temporary pen height position'''
        if self.heights.set_temp_height(ad_ref, temp_height):
            self.servo_init(ad_ref)

    def end_temp_height(self, ad_ref):
        '''End use of temporary pen height position'''
        if self.heights.end_temp_height(ad_ref):
            self.servo_init(ad_ref)

    def find_pen_state(self, ad_ref):
        '''
        Determine if physical pen state is initialized, and if so, if it is up or down.
        If this program has already determined it to be up or down, self.phys.z_up
            will be True or False, not None.
        If the hardware position has been set the EBBLV will store a code representing
            the pen-up position and whether that's a narrow-band position or not.
            Check to see if that has been set, and if so, use it to set self.phys.z_up
        If (and only if) z_up was None, but now we trust it to be reliable, then also set the
            config value to reflect the current settings. If it was not None (if the servo
            init routine was already run), leave the config settings alone to detect changes.
        Add special cases to handle setup functions that initially lower the pen.
        Return "layer code" and "servo config list"
        '''

        if self.heights.narrow_band:
            layer_code = 71 + ad_ref.options.pen_pos_up // 2 # Possible range 71-121.
        else:
            layer_code = 1 + ad_ref.options.pen_pos_up // 2 # Possible range 1 - 51.

        config = [ad_ref.options.pen_pos_up,\
                        self.heights.pen_pos_down, self.heights.narrow_band]

        if self.phys.z_up is not None: # Pen status _has_ already been set in software.
            return layer_code, config

        ebblv = ebb_motion.queryEBBLV(ad_ref.plot_status.port, False)
        ebb_pen_up = ebb_motion.QueryPenUp(ad_ref.plot_status.port, False)

        # Special case: The pen should go *down* when first initialized
        if (ad_ref.options.mode =="manual" and ad_ref.options.manual_cmd =="lower_pen") or\
                (ad_ref.options.mode =="toggle" and ebb_pen_up) or\
                ad_ref.options.mode =="cycle":
            self.phys.z_up = False  # Flag to initialize state "with pen down."
            self.status.config[1] = -1 # Flag to require sending new pen-lower command.
            return layer_code, config

        if ad_ref.options.mode =="toggle" or\
            (ad_ref.options.mode =="manual" and ad_ref.options.manual_cmd =="raise_pen"):
            self.phys.z_up = True   # Flag to initialize state "with pen up."
            self.status.config[0] = -1 # Flag to require sending new pen-raise command.
            return layer_code, config

        if bool(ebblv): # If ebblv is not 0 or None...
            if int(ebblv) == layer_code:
                self.phys.z_up = ebb_pen_up
                if self.phys.z_up is True: # Set config to skip initial pen raising:
                    self.status.config = [ad_ref.options.pen_pos_up,\
                        self.heights.pen_pos_down, self.heights.narrow_band]
        return layer_code, config

    def servo_init(self, ad_ref):
        '''
        Utility function, used for setting or updating the various parameters that control
        the pen-lift servo motor. Function replaces servo_setup_wrapper() and servo_setup()
        in prior versions.

        Actions:
        1. If current pen up/down state is not yet known, query EBB to see if it has
            been initialized, or whether it is still in its default power-on state.
        2. Send EBB commands to set servo positions, lifting/lowering speeds,
            PWM channel count, timeout, and standard or narrow-band servo output.
        3. Put the servo into a known state, if necessary, by sending a pen-lift or
            lower command.

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

        QueryPenUp _does not_ confirm that the pen is at the *requested* pen-up position, or
        that it was set to use the correct output pin. We encode the approximate pen-up height
        and narrow-band setting, and store that in EBBLV. At software start up, we read out EBBLV,
        to verify that the current PEN UP position is correct, and that we can skip the initial
        pen-raising movement if (1) the software does not yet know what the pen state is,
        but (2) the AxiDraw confirms that the pen height has been set, the pen is up, and that
        the pen-up height already matches what we were going to set it to.

        For changes after initialization, we use a list that] encodes the pen-up, pen-down and
        narrow-band settings. If (e.g.,) the pen-down height has changed while the pen is down,
        (e.g., Python interactive API update(), move to the new position.
        '''

        if ad_ref.options.penlift == 3:
            self.heights.narrow_band = True
            servo_max = ad_ref.params.nb_servo_max
            servo_min = ad_ref.params.nb_servo_min
            servo_sweep_time = ad_ref.params.nb_servo_sweep_time
            pwm_period = 0.03 # Units are "ms / 100", since pen_rate_raise is a %.
            servo_pin = ad_ref.params.nb_servo_pin
        else:
            self.heights.narrow_band = False
            servo_max = ad_ref.params.servo_max
            servo_min = ad_ref.params.servo_min
            servo_sweep_time = ad_ref.params.servo_sweep_time
            pwm_period = 0.24 # 24 ms: 8 channels at 3 ms each (divided by 100 as above)
            servo_pin = ad_ref.params.servo_pin

        self.heights.update(ad_ref) # Ensure heights and transit times are known

        if ad_ref.options.preview:
            self.phys.z_up = True
        if ad_ref.options.preview or ad_ref.plot_status.port is None:
            return

        layer_code, new_config = self.find_pen_state(ad_ref)

        servo_range = servo_max - servo_min
        servo_slope = float(servo_range) / 100.0

        ebb_motion.setPenUpPos(ad_ref.plot_status.port,\
            int(round(servo_min + servo_slope * ad_ref.options.pen_pos_up)), False)
        ebb_motion.setPenDownPos(ad_ref.plot_status.port,\
            int(round(servo_min + servo_slope * self.heights.pen_pos_down)), False)

        servo_rate_scale = float(servo_range) * pwm_period / servo_sweep_time

        ebb_motion.setPenUpRate(ad_ref.plot_status.port,\
            int(round(servo_rate_scale * ad_ref.options.pen_rate_raise)), False)
        ebb_motion.setPenDownRate(ad_ref.plot_status.port,\
            int(round(servo_rate_scale * ad_ref.options.pen_rate_lower)), False)

        if ad_ref.params.use_b3_out:  # Configure I/O Pin B3 for use
            ebb_motion.PBOutConfig(ad_ref.plot_status.port, 3, 0, False) # output, low

        if self.phys.z_up is not None and (self.status.config == new_config):
            return # Servo is initialized. No changes to height or I/O pin are needed.

        # If pen-up or pen-down position has changed while up/down, make that change.
        if (self.phys.z_up is False) and ((self.status.config[1] != new_config[1]) or\
                    (self.status.config[2] != new_config[2])):
            v_time = self.heights.times.lower_time
            ebb_motion.sendPenDown(ad_ref.plot_status.port, v_time, servo_pin, False)
            if ad_ref.params.use_b3_out: # I/O Pin B3 output: high
                ebb_motion.PBOutValue( ad_ref.plot_status.port, 3, 1, False)
        if (self.phys.z_up is not False) and ((self.status.config[0] != new_config[0]) or\
                (self.status.config[2] != new_config[2])):
            v_time = self.heights.times.raise_time
            ebb_motion.sendPenUp(ad_ref.plot_status.port, v_time, servo_pin, False)
            if ad_ref.params.use_b3_out: # I/O Pin B3 output: low
                ebb_motion.PBOutValue( ad_ref.plot_status.port, 3, 0, False)
            self.phys.z_up = True

        self.status.config = new_config
        ebb_motion.setEBBLV(ad_ref.plot_status.port, layer_code, False)

        if self.heights.narrow_band:
            ebb_serial.command(ad_ref.plot_status.port, 'SC,8,1\r') # 1 channel of servo PWM
        else:
            ebb_serial.command(ad_ref.plot_status.port, 'SC,8,8\r') # 8 channels of servo PWM
            ebb_motion.servo_timeout(ad_ref.plot_status.port, ad_ref.params.servo_timeout,\
                None, False) # Power timeout is only applicable to standard servo
