# coding=utf-8
#
# Copyright 2022 Windell H. Oskay, Evil Mad Scientist Laboratories
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

"""
pen_handling.py

Classes for managing AxiDraw pen vertical motion and status

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

The classes defined by this module are:

* PenHandler: Main class for managing pen lifting, lowering, and status

* PenHeight: Manage pen-down height settings and keep timing up to date

* PenLiftTiming: Class to calculate and store pen lift timing settings

* PenStatus: Data storage class for pen lift status variables

"""

import time
from axidrawinternal.plot_utils_import import from_dependency_import # plotink
plot_utils = from_dependency_import('plotink.plot_utils')
ebb_serial = from_dependency_import('plotink.ebb_serial')  # https://github.com/evil-mad/plotink
ebb_motion = from_dependency_import('plotink.ebb_motion')
# inkex = from_dependency_import('ink_extensions.inkex')


class PenHeight:
    """
    PenHeight: Class to manage pen-down height settings.
    Calculate timing for transiting between pen-up and pen-down states.
    """

    def __init__(self):
        self.pen_pos_down = None # Initial values must be set by update().
        self.use_temp_pen_height = False # Boolean set true while using temporary value
        self.times = PenLiftTiming()

    def update(self, options, params):
        '''
        Set initial/default values of options, after __init__.
        Call this function after changing option values to update pen height settings.
        '''
        if not self.use_temp_pen_height:
            self.pen_pos_down = options.pen_pos_down
        self.times.update(options, params, self.pen_pos_down)

    def set_temp_height(self, options, params, temp_height):
        '''
        Begin using temporary pen height position. Return True if the position has changed.
        '''
        self.use_temp_pen_height = True
        if self.pen_pos_down == temp_height:
            return False
        self.pen_pos_down = temp_height

        self.times.update(options, params, temp_height)
        return True

    def end_temp_height(self, options, params):
        '''
        End using temporary pen height position. Return True if the position has changed.
        '''
        self.use_temp_pen_height = False
        if self.pen_pos_down == options.pen_pos_down:
            return False
        self.pen_pos_down = options.pen_pos_down
        self.times.update(options, params, self.pen_pos_down)
        return True


class PenLiftTiming: # pylint: disable=too-few-public-methods
    """
    PenTiming: Class to calculate and store time required for pen to lift and lower
    """

    def __init__(self):
        self.raise_time = None
        self.lower_time = None

    def update(self, options, params, pen_down_pos):
        '''
        Compute travel time needed for raising and lowering the pen.

        Call this function after changing option values to update pen timing settings.

        Servo travel time is estimated as the 4th power average (a smooth blend between):
          (A) Servo transit time for fast servo sweeps (t = slope * v_dist + min) and
          (B) Sweep time for slow sweeps (t = v_dist * full_scale_sweep_time / sweep_rate)
        '''
        v_dist = abs(float(options.pen_pos_up - pen_down_pos))

        # Raising time:
        v_time = int(((params.servo_move_slope * v_dist + params.servo_move_min) ** 4 +
            (params.servo_sweep_time * v_dist / options.pen_rate_raise) ** 4) ** 0.25)
        if v_dist < 0.9:  # If up and down positions are equal, no initial delay
            v_time = 0

        v_time += options.pen_delay_up
        v_time = max(0, v_time)  # Do not allow negative total delay time
        self.raise_time = v_time

        # Lowering time:
        v_time = int(((params.servo_move_slope * v_dist + params.servo_move_min) ** 4 +
            (params.servo_sweep_time * v_dist / options.pen_rate_raise) ** 4) ** 0.25)
        if v_dist < 0.9:  # If up and down positions are equal, no initial delay
            v_time = 0
        v_time += options.pen_delay_down
        v_time = max(0, v_time)  # Do not allow negative total delay time
        self.lower_time = v_time


class PenStatus: # pylint: disable=too-few-public-methods
    """
    PenTiming: Data storage class for pen lift status variables

    pen_up: physical pen up/down state (boolean)
    preview_pen_state: pen state for preview rendering. 0: down, 1: up, -1: changed
    virtual_pen_up: Theoretical state while stepping through a plot to resume
    ebblv_set: Boolean; set to True after the pen is physically raised once
    lifts: Counter; keeps track of the number of times the pen is lifted
    """

    def __init__(self):
        self.pen_up = None # Initial state: Pen status is unknown.
        self.preview_pen_state = -1
        self.virtual_pen_up = False
        self.ebblv_set = False
        self.lifts = 0

    def reset(self):
        """ Clear virtual state and lift count; Resetting them for a new plot. """
        self.preview_pen_state = -1
        self.virtual_pen_up = False
        self.lifts = 0

    def report(self, params, message_fun):
        """ report: Print pen lift statistics """
        if not params.report_lifts:
            return
        message_fun(f"Number of pen lifts: {self.lifts}\n")

class PenHandler:
    """
    PenHandler: Main class for managing pen lifting, lowering, and status
    """

    def __init__(self):
        self.heights = PenHeight()
        self.status = PenStatus()

    def update(self, options, params):
        """ Function to apply new settings after changing options directly """
        self.heights.update(options, params)

    def reset(self):
        """
        Reset certain defaults for a new plot:
        Clear virtual states and lift count; clear temporary pen height flag.
        These are the defaults that can be set even before options are set.
        """
        self.status.reset()
        self.heights.use_temp_pen_height = False


    def pen_raise(self, options, params, plot_status):
        """ Raise the pen; return duration in ms """
        self.status.virtual_pen_up = True # Virtual pen tracks state for resuming plotting.
        self.status.preview_pen_state = -1 # For preview rendering use

        # Skip if pen is already up, or if resuming:
        if plot_status.resume.resume_mode or self.status.pen_up:
            return 0

        self.status.lifts += 1

        v_time = self.heights.times.raise_time
        if not options.preview:
            ebb_motion.sendPenUp(plot_status.port, v_time, params.servo_pin, False)
            if params.use_b3_out:
                ebb_motion.PBOutValue( plot_status.port, 3, 0, False) # I/O Pin B3 output: low
            if (v_time > 50) and (options.mode not in ["manual", "align", "toggle", "cycle"]):
                time.sleep(float(v_time - 30) / 1000.0) # pause before issuing next command
        self.status.pen_up = True
        if not self.status.ebblv_set:
            ebb_motion.setEBBLV(plot_status.port, options.pen_pos_up + 1, False)
            self.status.ebblv_set = True
        return v_time


    def pen_lower(self, options, params, plot_status):
        """ Lower the pen; return duration in ms """
        self.status.virtual_pen_up = False # Virtual pen keeps track of state for resuming plotting.
        self.status.preview_pen_state = -1  # For preview rendering use

        if self.status.pen_up is not None:
            if not self.status.pen_up:
                return 0 # skip if pen is state is _known_ and is down

        # Skip if stopped, or if resuming:
        if plot_status.resume.resume_mode or plot_status.stopped:
            return 0

        v_time = self.heights.times.lower_time

        if not options.preview:
            ebb_motion.sendPenDown(plot_status.port, v_time, params.servo_pin, False)
            if params.use_b3_out:
                ebb_motion.PBOutValue( plot_status.port, 3, 1, False) # I/O Pin B3 output: high
            if (v_time > 50) and (options.mode not in ["manual", "align", "toggle", "cycle"]):
                time.sleep(float(v_time - 30) / 1000.0) # pause before issuing next command
        self.status.pen_up = False
        return v_time


    def toggle(self, options, params, plot_status):
        """
        Toggle the pen from up to down or vice versa, after determining which state it
        is initially in. Call only after servo_setup_wrapper().
        This function should only be used as a setup utility.
        """

        if self.status.pen_up:
            self.pen_lower(options, params, plot_status)
        else:
            self.pen_raise(options, params, plot_status)


    def cycle(self, options, params, plot_status):
        """
        Toggle the pen down and then up, with a 1/2 second delay.
        Call only after servo_setup_wrapper().
        This function should only be used as a setup utility.
        """
        self.pen_lower(options, params, plot_status)
        ebb_serial.command(plot_status.port, 'SM,500,0,0\r')
        self.pen_raise(options, params, plot_status)


    def set_temp_height(self, options, params, temp_height, status):
        '''Begin using temporary pen height position'''
        if self.heights.set_temp_height(options, params, temp_height):
            self.servo_setup(options, params, status)

    def end_temp_height(self, options, params, status):
        '''End use of temporary pen height position'''
        if self.heights.end_temp_height(options, params):
            self.servo_setup(options, params, status)


    def servo_setup_wrapper(self, options, params, status):
        '''
        Utility wrapper for servo_setup(), used for the first time that we address the
        pen-lift servo motor. It is used in manual and setup modes, as well as in various
        ploting modes for initial pen raising/lowering.

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
        pen-up position. We can store (options.pen_pos_up + 1), with possible values
        in the range 1 - 101 in EBBLV, to verify that the current position is correct, and
        that we can skip extra pen-up/pen-down movements.

        We do not _set_ the current correct pen-up value of EBBLV until the pen is raised.
        '''

        self.servo_setup(options, params, status) # Set pen-up/down heights

        if self.status.pen_up is not None:
            return # Pen status is already known; no need to proceed.

        # What follows is code to determine if the initial pen state is known.
        if options.preview:
            self.status.pen_up = True  # A fine assumption when in preview mode
            self.status.virtual_pen_up = True
            return

        if status.port is None:
            return

        # Need to figure out if we're in the pen-up or pen-down state, or indeterminate:
        value = ebb_motion.queryEBBLV(status.port, False)
        if value is None:
            return
        if int(value) != options.pen_pos_up + 1:
            # See "Methods" above for what's going on here.
            ebb_motion.setEBBLV(status.port, 0, False)
            self.status.ebblv_set = False
            self.status.virtual_pen_up = False

        else:   # EEBLV has already been set; we can trust the value from QueryPenUp:
                # Note, however, that this does not ensure that the current
                #    Z position matches that in the settings.
            self.status.ebblv_set = True
            if ebb_motion.QueryPenUp(status.port, False):
                self.status.pen_up = True
                self.status.virtual_pen_up = True
            else:
                self.status.pen_up = False
                self.status.virtual_pen_up = False


    def servo_setup(self, options, params, status):
        '''
        Set servo up/down positions, raising/lowering rates, and power timeout.

        Pen position units range from 0% to 100%, which correspond to a typical timing range of
        9855 - 27831 in units of 83.3 ns (1/(12 MHz)), giving a timing range of 0.82 - 2.32 ms.

        Servo rate options (pen_rate_raise, pen_rate_lower) range from 1% to 100%.
        The EBB servo rate values are in units of 83.3 ns steps per 24 ms.
        Our servo sweep at 100% rate sweeps over 100% range in servo_sweep_time ms.
        '''

        if options.preview or status.resume.resume_mode or status.port is None:
            return

        self.heights.update(options, params) # Ensure heights and transit times are known
        servo_range = params.servo_max - params.servo_min
        servo_slope = float(servo_range) / 100.0

        int_temp = int(round(params.servo_min + servo_slope * options.pen_pos_up))
        ebb_motion.setPenUpPos(status.port, int_temp, False)
        int_temp = int(round(params.servo_min + servo_slope * self.heights.pen_pos_down))
        ebb_motion.setPenDownPos(status.port, int_temp, False)

        servo_rate_scale = float(servo_range) * 0.24 / params.servo_sweep_time
        int_temp = int(round(servo_rate_scale * options.pen_rate_raise))
        ebb_motion.setPenUpRate(status.port, int_temp, False)

        int_temp = int(round(servo_rate_scale * options.pen_rate_lower))
        ebb_motion.setPenDownRate(status.port, int_temp, False)
        ebb_motion.servo_timeout(status.port, params.servo_timeout, None, False)
