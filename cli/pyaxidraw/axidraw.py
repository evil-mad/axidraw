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
pyaxidraw/axidraw.py

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

Requires Python 3.7 or newer and Pyserial 3.5 or newer.
"""

import sys
import math
import gettext
import copy
import logging
import threading
import signal

from lxml import etree

from axidrawinternal import axidraw

from axidrawinternal.plot_utils_import import from_dependency_import # plotink
from axidrawinternal import boundsclip
inkex = from_dependency_import('ink_extensions.inkex')
ebb_motion = from_dependency_import('plotink.ebb_motion')
ebb_serial = from_dependency_import('plotink.ebb_serial')
plot_utils = from_dependency_import('plotink.plot_utils')
path_objects = from_dependency_import('axidrawinternal.path_objects')

logger = logging.getLogger(__name__)


class ErrConfig:
    '''Configure error reporting options for AxiDraw Python API'''
    def __init__(self):
        self.connect = False # Raise error on failure to connect to AxiDraw
        self.button = False # Raise error on pause by button press
        self.keyboard = False # Raise error on pause by keyboard interrupt
        self.disconnect = False # Raise error on loss of USB connectivity
        self.code = 0 # Error code. 0 (default) indicates no error.


class AxiDraw(axidraw.AxiDraw):
    """ Extend AxiDraw class with Python API functions """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.turtle_x = 0
        self.turtle_y = 0
        self.turtle_pen_up = True
        self.turtle_pen_up = True
        self.document = None
        self.original_document = None

        self.time_estimate = 0
        self.distance_pendown = 0
        self.distance_total = 0
        self.pen_lifts = 0
        self.software_initiated_pause_event = None
        self.fw_version_string = None
        self.keyboard_pause = False
        self.errors = ErrConfig()
        self._interrupted = False # Duplicate flag for keyboard interrupt for special cases.

    def set_up_pause_transmitter(self):
        """ intercept ctrl-C (keyboard interrupt) and redefine as "pause" command """
        if self.keyboard_pause: # only enable when explicitly directed to
            signal.signal(signal.SIGINT, self.transmit_pause_request)
        self.software_initiated_pause_event = threading.Event()
        self._interrupted = False

    def transmit_pause_request(self, *args):
        """ Transmit a software-requested pause event """
        self.software_initiated_pause_event.set()
        self._interrupted = True

    def clear_pause_request(self):
        """ Clear a software-requested pause event """
        if self.keyboard_pause: # only when enabled
            self.software_initiated_pause_event.clear()
        self._interrupted = False

    def connect(self):
        '''Python Interactive context: Open connection to AxiDraw'''
        if not self._verify_interactive():
            return None

        self.set_up_pause_transmitter()

        self.serial_connect() # Open USB serial session
        if self.plot_status.port is None:
            if self.errors.connect:
                raise RuntimeError("Failed to connected to AxiDraw")
            return False

        self.query_ebb_voltage()
        self.update_options() # Apply general settings

        if self.start_x is not None:    # Set initial XY Position:
            self.f_curr_x = self.start_x
        else:
            self.f_curr_x = self.params.start_pos_x
        if self.start_y is not None:
            self.f_curr_y = self.start_y
        else:
            self.f_curr_y = self.params.start_pos_y

        self.pt_first = (self.f_curr_x, self.f_curr_y)
        self.turtle_x = self.f_curr_x # Set turtle position to (0,0)
        self.turtle_y = self.f_curr_y
        self.turtle_pen_up = True

        # Query if button pressed, to clear the result:
        ebb_motion.QueryPRGButton(self.plot_status.port)
        self.pen.servo_setup_wrapper(self.options, self.params, self.plot_status)
        self.pen.pen_raise(self.options, self.params, self.plot_status) # Raise pen
        self.enable_motors()         # Set plot resolution & speed & enable motors
        return True

    def plot_setup(self, svg_input=None, argstrings=None):
        """Python module plot context: Begin plot context & parse SVG file"""
        file_ok = False
        inkex.localize()
        self.getoptions([] if argstrings is None else argstrings)

        if svg_input is None:
            svg_input = plot_utils.trivial_svg
        try: # Parse input file or SVG string
            file_ref = open(svg_input, encoding='utf8')
            parse_ref = etree.XMLParser(huge_tree=True)
            self.document = etree.parse(file_ref, parser=parse_ref)
            self.original_document = copy.deepcopy(self.document)
            file_ref.close()
            file_ok = True
        except IOError:
            pass # It wasn't a file; was it a string?
        if not file_ok:
            try:
                svg_string = svg_input.encode('utf8') # Need consistent encoding.
                parse_ref = etree.XMLParser(huge_tree=True, encoding='utf8')
                self.document = etree.ElementTree(etree.fromstring(svg_string, parser=parse_ref))
                self.original_document = copy.deepcopy(self.document)
                file_ok = True
            except:
                logger.error("Unable to open SVG input file.")
                raise RuntimeError("Unable to open SVG input file.")
        if file_ok:
            self.getdocids()
        # self.suppress_standard_output_stream()

    def plot_run(self, output=False):
        '''Python module plot context: Plot document'''

        self.set_up_pause_transmitter()

        if self.document is None:
            logger.error("No SVG input provided.")
            logger.error("Use plot_setup(svg_input) before plot_run().")
            raise RuntimeError("No SVG input provided.")
        self.set_defaults() # Re-initialize some items normally set at __init__
        self.set_up_pause_receiver(self.software_initiated_pause_event)
        self.effect()
        self.clear_pause_request()
        #self.fw_version_string is a public string made available to Python API:
        self.fw_version_string = self.plot_status.fw_version

        self.handle_errors()

        self.time_estimate = self.plot_status.stats.pt_estimate / 1000.0
        self.distance_pendown = 0.0254 * self.plot_status.stats.down_travel_inch
        self.distance_total = self.distance_pendown +\
            0.0254 * self.plot_status.stats.up_travel_inch
        self.pen_lifts = self.pen.status.lifts

        for warning_message in self.warnings.return_text_list():
            self.user_message_fun(warning_message)
        if output:
            return self.get_output()
        return None

    def interactive(self):
        '''Python module: Begin interactive context and Initialize options'''
        inkex.localize()
        self.getoptions([])
        self.options.units = 0 # inches, by default
        self.options.preview = False
        self.options.mode = "interactive"
        self.Secondary = False
        self.pen.update(self.options, self.params)

    def _verify_interactive(self, verify_connection=False):
        '''
            Check that we are in interactive API context.
            Optionally, check if we are connected as well, and throw an error if not.
        '''
        interactive = False
        try:
            if self.options.mode == "interactive":
                interactive = True
        except AttributeError:
            self.user_message_fun(gettext.gettext("Function only available in interactive mode.\n"))
        if not interactive:
            return False
        if verify_connection:
            try:
                if self.connected:
                    return True
            except AttributeError:
                pass
            self.handle_errors() # Raise specific error if thus configured
            raise RuntimeError("Not connected to AxiDraw")
        return True

    def update(self):
        '''Python Interactive context: Apply optional parameters'''
        if not self._verify_interactive(True):
            return
        self.update_options()
        self.pen.servo_setup(self.options, self.params, self.plot_status)
        if self.plot_status.port:
            self.enable_motors()  # Set plotting resolution & speed

    def delay(self, time_ms):
        '''Interactive context: Execute timed delay'''
        if not self._verify_interactive(True):
            return
        if time_ms is None:
            self.user_message_fun(gettext.gettext("No delay time given.\n"))
            return
        time_ms = int(time_ms)
        if time_ms > 0:
            ebb_serial.command(self.plot_status.port, f'SM,{time_ms},0,0\r')

    def _xy_plot_segment(self, relative, x_value, y_value):
        """
        Perform movements for interactive context XY movement commands.
        Internal function; uses inch units.
        Maintains record of "turtle" position, and directs the carriage to
        move from the last turtle position to the new turtle position,
        clipping that movement segment to the allowed bounds of movement.
        Commands directing movement outside of the bounds are clipped
        with pen up.
        """
        if not self._verify_interactive(True):
            return

        if self.options.units == 1 : # If using centimeter units
            x_value = x_value / 2.54
            y_value = y_value / 2.54
        if self.options.units == 2: # If using millimeter units
            x_value = x_value / 25.4
            y_value = y_value / 25.4
        if relative:
            x_value = self.turtle_x + x_value
            y_value = self.turtle_y + y_value

        # Snap interactive movement to travel bounds, with modest tolerance:
        if math.isclose(x_value, self.x_bounds_min, abs_tol=1e-9):
            x_value = self.x_bounds_min
        if math.isclose(x_value, self.x_bounds_max, abs_tol=1e-9):
            x_value = self.x_bounds_max
        if math.isclose(y_value, self.y_bounds_min, abs_tol=1e-9):
            y_value = self.y_bounds_min
        if math.isclose(y_value, self.y_bounds_max, abs_tol=1e-9):
            y_value = self.y_bounds_max

        turtle = [self.turtle_x, self.turtle_y]
        target = [x_value, y_value]
        segment = [turtle, target]
        accept, seg = plot_utils.clip_segment(segment, self.bounds)

        if accept and self.plot_status.port: # Segment is at least partially within bounds
            if not plot_utils.points_near(seg[0], turtle, 1e-9): # if initial point clipped
                if self.params.auto_clip_lift and not self.turtle_pen_up:
                    self.pen.pen_raise(self.options, self.params, self.plot_status)
                    # Pen-up move to initial position
                    self.turtle_pen_up = False # Keep track of intended state
                self.plot_seg_with_v(seg[0][0], seg[0][1], 0, 0) # move to start
            if not self.turtle_pen_up:
                self.pen.pen_lower(self.options, self.params, self.plot_status)
            self.plot_seg_with_v(seg[1][0], seg[1][1], 0, 0) # Draw clipped segment
            if not plot_utils.points_near(seg[1], target, 1e-9) and\
                    self.params.auto_clip_lift and not self.turtle_pen_up:
                self.pen.pen_raise(self.options, self.params, self.plot_status)
                # Segment end was clipped; this end is out of bounds.
                self.turtle_pen_up = False # Keep track of intended state
        self.turtle_x = x_value
        self.turtle_y = y_value

        self.handle_errors()

    def draw_path(self, vertex_list):
        '''
        Interactive context function to plot path data.
        Given a list of coordinates, pathdata, plot that path:
        * Move to first coordinate and lower pen
        * Move along the path
        * Raise pen
        Input pathdata is an iterable of at least two 2-element items,
            typically a list of 2-element lists or tuples.
        Motion is clipped at hardware travel bounds; no document bounds are
            defined in interactive context. The auto_clip_lift parameter is
            ignored; draw_path always raises the pen at the edges of travel.
        '''
        if not self._verify_interactive(True):
            return
        if len(vertex_list) < 2:
            return # At least two vertices are required.
        if self.plot_status.stopped: # If this plot is already stopped
            return
        if self.options.units == 1 : # Centimeter units
            scaled_vertices = [[vertex[0] / 2.54, vertex[1] / 2.54] for vertex in vertex_list]
        elif self.options.units == 2: # Millimeter units
            scaled_vertices = [[vertex[0] / 25.4, vertex[1] / 25.4] for vertex in vertex_list]
        else: # Assume self.options.units == 0; use default inch units
            scaled_vertices = vertex_list
        new_path = path_objects.PathItem()
        new_path.item_id = "draw_path_item"
        new_path.stroke = 'Black'
        new_path.subpaths = [scaled_vertices]
        new_turtle = new_path.last_point() # Final turtle position, if allowed to finish

        new_layer = path_objects.LayerItem()
        new_layer.paths.append(new_path)
        digest = path_objects.DocDigest()
        digest.layers.append(new_layer)
        digest.flat = True

        # Clip at physical travel. Interactive mode does not define a document size.
        boundsclip.clip_at_bounds(digest, self.bounds, self.bounds,\
            self.params.bounds_tolerance, doc_clip=False)

        for path_item in digest.layers[0].paths:
            if self.plot_status.stopped:
                break
            self.plot_polyline(path_item.subpaths[0])
            self.handle_errors()
            self.penup()

        if self.plot_status.stopped:
            new_turtle = self.f_curr_x, self.f_curr_y
        self.turtle_x, self.turtle_y = new_turtle
        self.turtle_pen_up = True

    def handle_errors(self):
        '''Raise keyboard interrupts and runtime errors if thus configured'''

        self.errors.code = self.plot_status.stopped
        if self.errors.code == 101:
            if self.errors.connect:
                raise RuntimeError("Failed to connected to AxiDraw")
        if self.errors.code == 102:
            if self.errors.button:
                self.disconnect()
                raise RuntimeError("Stopped by pause button press")
        if self.errors.code == 103:
            if self.errors.keyboard:
                self.disconnect()
                raise RuntimeError("Stopped by keyboard interrupt")
        if self.errors.code == 104:
            if self.errors.disconnect:
                raise RuntimeError("Lost USB connectivity")

        if self._interrupted: # Fallback; catch interrupts not flagged in main axidraw module.
            if self.errors.code == 0:
                self.plot_status.stopped = -103 # Assert keyboard interrupt

    def goto(self,x_target,y_target):
        '''Interactive context: absolute position move'''
        self._xy_plot_segment(False,x_target, y_target)

    def moveto(self,x_target,y_target):
        '''Interactive context: absolute position move, pen-up'''
        if not self._verify_interactive(True):
            return
        self.pen.pen_raise(self.options, self.params, self.plot_status)
        self.turtle_pen_up = True
        self._xy_plot_segment(False,x_target, y_target)

    def lineto(self,x_target,y_target):
        '''Interactive context: absolute position move, pen-down'''
        self.turtle_pen_up = False
        self._xy_plot_segment(False,x_target, y_target)

    def go(self,x_delta,y_delta):
        '''Interactive context: relative position move'''
        self._xy_plot_segment(True,x_delta, y_delta)

    def move(self,x_delta,y_delta):
        '''Interactive context: relative position move, pen-up'''
        if not self._verify_interactive(True):
            return
        self.pen.pen_raise(self.options, self.params, self.plot_status)
        self.turtle_pen_up = True
        self._xy_plot_segment(True,x_delta, y_delta)

    def line(self,x_delta,y_delta):
        '''Interactive context: relative position move, pen-down'''
        self.turtle_pen_up = False
        self._xy_plot_segment(True,x_delta, y_delta)

    def penup(self):
        '''Interactive context: raise pen'''
        if not self._verify_interactive(True):
            return
        self.pen.pen_raise(self.options, self.params, self.plot_status)
        self.turtle_pen_up = True

    def pendown(self):
        '''Interactive context: lower pen'''
        if not self._verify_interactive(True):
            return
        self.turtle_pen_up = False
        if self.params.auto_clip_lift and not\
                plot_utils.point_in_bounds([self.turtle_x, self.turtle_y], self.bounds):
            return # Skip out-of-bounds pen lowering
        self.pen.pen_lower(self.options, self.params, self.plot_status)

    def usb_query(self, query):
        '''Interactive context: Low-level USB query'''
        if not self._verify_interactive(True):
            return None
        return ebb_serial.query(self.plot_status.port, query).strip()

    def usb_command(self, command):
        '''Interactive context: Low-level USB command; use with great care '''
        if not self._verify_interactive(True):
            return
        ebb_serial.command(self.plot_status.port, command)

    def turtle_pos(self):
        '''Interactive context: Report last known "turtle" position'''
        return plot_utils.position_scale(self.turtle_x, self.turtle_y, self.options.units)

    def turtle_pen(self):
        '''Interactive context: Report last known "turtle" pen state'''
        return self.turtle_pen_up

    def current_pos(self):
        '''Interactive context: Report last known physical position '''
        self._verify_interactive(True)
        return plot_utils.position_scale(self.f_curr_x, self.f_curr_y, self.options.units)

    def current_pen(self):
        '''Interactive context: Report last known physical pen state '''
        return self.pen.status.pen_up
