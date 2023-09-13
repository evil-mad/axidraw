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

"""
pyaxidraw/axidraw.py

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

Requires Python 3.7 or newer and Pyserial 3.5 or newer.
"""
__version__ = '3.9.4'  # Dated 2023-09-09

import math
import gettext
import copy
import logging
import threading
import signal

from lxml import etree

from axidrawinternal import axidraw

from axidrawinternal.plot_utils_import import from_dependency_import # plotink
from axidrawinternal import boundsclip, serial_utils
inkex = from_dependency_import('ink_extensions.inkex')
ebb_motion = from_dependency_import('plotink.ebb_motion')
ebb_serial = from_dependency_import('plotink.ebb_serial')
plot_utils = from_dependency_import('plotink.plot_utils')
path_objects = from_dependency_import('axidrawinternal.path_objects')
from axicli import utils as axicli_utils

logger = logging.getLogger(__name__)


class ErrConfig: # pylint: disable=too-few-public-methods
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

        self.pen.turtle = copy.copy(self.pen.phys)
        self.pen.turtle.z_up = True # Theoretical pen starts UP.

        # Query if button pressed, to clear the result:
        ebb_motion.QueryPRGButton(self.plot_status.port)
        self.pen.servo_init(self)
        self.pen.pen_raise(self) # Raise pen
        self.enable_motors()         # Set plot resolution & speed & enable motors
        return True

    def plot_setup(self, svg_input=None, argstrings=None):
        """Python module plot context: Begin plot context & parse SVG file"""
        file_ok = False
        inkex.localize()
        self.getoptions([] if argstrings is None else argstrings)

        self.original_dist = self.options.dist # Remove in v 4.0
        self.old_walk_dist = None # Remove in v 4.0

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


        ### THIS SECTION: SLATED FOR REMOVAL IN AXIDRAW SOFTWARE 4.0 ###
        # Backwards compatibility for user scripts including `walk_dist`,
        #   the deprecated predecessor to `dist`
        #
        # If the script specifies walk_dist (deprecated version of dist), then that
        #   value overrides the value of dist in the config file (axidraw_conf.py).
        # But, if the script gives a value of dist different from that in the config file,
        # then that value overrides both the config file and any value of walk_dist.
        #
        # i.e., if this script has not changed the value of "dist" versus the default
        #   given in the config file, AND there is a walk_dist value given,
        #   then accept that walk_dist as the correct value to use.

        # First, handle special case: Multiple walks in a row, with walk_dist set at least once
        if self.old_walk_dist is not None:
            if self.options.dist != self.old_walk_dist and\
                self.options.dist != self.original_dist: # Thus, *dist* has now been set; use it.
                self.old_walk_dist = None
            else: # Otherwise, continue using walk_dist, which may have an updated value:
                self.options.dist = self.options.walk_dist
                self.old_walk_dist = self.options.walk_dist
        elif self.options.dist == self.original_dist:
            try:
                self.options.walk_dist
            except AttributeError:
                pass # No worries; we don't need walk_dist to be defined. :)
            else:
                self.options.dist = self.options.walk_dist
                self.old_walk_dist = self.options.walk_dist

        ### END SECTION FOR REMOVAL IN 4.0 ###

        self.set_defaults() # Re-initialize some items normally set at __init__
        self.set_up_pause_receiver(self.software_initiated_pause_event)
        self.effect()
        self.clear_pause_request()
        #self.fw_version_string is a public string made available to Python API:
        self.fw_version_string = self.plot_status.fw_version

        self.handle_errors()

        if self.options.mode in ("plot", "layers", "res_plot"):
            ''' Timing & distance variables only available in modes that plot '''
            if self.options.preview:
                self.time_estimate = self.plot_status.stats.pt_estimate / 1000.0
            else:
                self.time_estimate = self.time_elapsed
            self.distance_pendown = 0.0254 * self.plot_status.stats.down_travel_tot
            self.distance_total = self.distance_pendown +\
                0.0254 * self.plot_status.stats.up_travel_tot
            self.pen_lifts = self.pen.status.lifts

        for warning_message in self.warnings.return_text_list():
            self.user_message_fun(warning_message)
        if output:
            return self.get_output()
        return None

    def load_config(self, config_ref):
        '''
        Plot or Interactive context: Load settings from a configuration file.
        config_ref may be a file name, or the full path to a file
        '''
        backup_mode = ""
        if self.options.mode == "interactive":
            backup_mode = "interactive"
        config_dict = axicli_utils.load_config(config_ref)
        combined_config = axicli_utils.FakeConfigModule(config_dict)
        self.params = combined_config
        axicli_utils.assign_option_values(self.options, None, [config_dict],\
            axicli_utils.OPTION_NAMES)
        if backup_mode == "interactive":
            self.options.mode = "interactive"

    def interactive(self):
        '''Python module: Begin interactive context and Initialize options'''
        inkex.localize()
        self.getoptions([])
        self.options.units = 0 # inches, by default
        self.options.preview = False
        self.options.mode = "interactive"
        self.plot_status.secondary = False

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
        self.pen.servo_init(self)
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
            x_value = self.pen.turtle.xpos + x_value
            y_value = self.pen.turtle.ypos + y_value

        # Snap interactive movement to travel bounds, with modest tolerance:
        if math.isclose(x_value, self.bounds[0][0], abs_tol=2e-9):
            x_value = self.bounds[0][0] # x_bounds_min
        if math.isclose(x_value,  self.bounds[1][0], abs_tol=2e-9):
            x_value = self.bounds[1][0] # x_bounds_max
        if math.isclose(y_value, self.bounds[0][1], abs_tol=2e-9):
            y_value = self.bounds[0][1] # y_bounds_min
        if math.isclose(y_value, self.bounds[1][1], abs_tol=2e-9):
            y_value = self.bounds[1][1] # y_bounds_max

        turtle = [self.pen.turtle.xpos, self.pen.turtle.ypos]
        target = [x_value, y_value]
        segment = [turtle, target]
        accept, seg = plot_utils.clip_segment(segment, self.bounds)

        if accept and self.plot_status.port: # Segment is at least partially within bounds
            if not plot_utils.points_near(seg[0], turtle, 1e-9): # if initial point clipped
                if self.params.auto_clip_lift and not self.pen.turtle.z_up:
                    self.pen.pen_raise(self)
                    # Pen-up move to initial position
                    self.pen.turtle.z_up = False # Keep track of intended state
                self.go_to_position(seg[0][0], seg[0][1])
            if not self.pen.turtle.z_up:
                self.pen.pen_lower(self)
            self.go_to_position(seg[1][0], seg[1][1]) # Draw clipped segment
            if not plot_utils.points_near(seg[1], target, 1e-9) and\
                    self.params.auto_clip_lift and not self.pen.turtle.z_up:
                self.pen.pen_raise(self)
                # Segment end was clipped; this end is out of bounds.
                self.pen.turtle.z_up = False # Keep track of intended state
        self.pen.turtle.xpos = x_value
        self.pen.turtle.ypos = y_value

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

        # Final turtle position, if allowed to finish:
        self.pen.turtle.xpos, self.pen.turtle.ypos = new_path.last_point()
        self.pen.turtle.z_up = True

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
            self.pen.turtle = copy.copy(self.pen.phys)
            self.pen.turtle.z_up = True

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
        self._xy_plot_segment(False, x_target, y_target)

    def moveto(self,x_target,y_target):
        '''Interactive context: absolute position move, pen-up'''
        if not self._verify_interactive(True):
            return
        self.pen.pen_raise(self)
        self.pen.turtle.z_up = True
        self._xy_plot_segment(False, x_target, y_target)

    def lineto(self,x_target,y_target):
        '''Interactive context: absolute position move, pen-down'''
        self.pen.turtle.z_up = False
        self._xy_plot_segment(False, x_target, y_target)

    def go(self,x_delta,y_delta):
        '''Interactive context: relative position move'''
        self._xy_plot_segment(True, x_delta, y_delta)

    def move(self,x_delta,y_delta):
        '''Interactive context: relative position move, pen-up'''
        if not self._verify_interactive(True):
            return
        self.pen.pen_raise(self)
        self.pen.turtle.z_up = True
        self._xy_plot_segment(True, x_delta, y_delta)

    def line(self,x_delta,y_delta):
        '''Interactive context: relative position move, pen-down'''
        self.pen.turtle.z_up = False
        self._xy_plot_segment(True, x_delta, y_delta)

    def penup(self):
        '''Interactive context: raise pen'''
        if not self._verify_interactive(True):
            return
        self.pen.pen_raise(self)
        self.pen.turtle.z_up = True

    def pendown(self):
        '''Interactive context: lower pen'''
        if not self._verify_interactive(True):
            return
        self.pen.turtle.z_up = False
        if self.params.auto_clip_lift and not\
                plot_utils.point_in_bounds([self.pen.turtle.xpos, \
                    self.pen.turtle.ypos], self.bounds):
            return # Skip out-of-bounds pen lowering
        self.pen.pen_lower(self)

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

    def block(self):
        '''Interactive context: Wait until all current motion commands have completed '''
        if not self._verify_interactive(True):
            return
        serial_utils.exhaust_queue(self)

    def turtle_pos(self):
        '''Interactive context: Report last known "turtle" position'''
        return plot_utils.position_scale(self.pen.turtle.xpos, self.pen.turtle.ypos,\
            self.options.units)

    def turtle_pen(self):
        '''Interactive context: Report last known "turtle" pen state'''
        return self.pen.turtle.z_up

    def current_pos(self):
        '''Interactive context: Report last known physical position '''
        self._verify_interactive(True)
        return plot_utils.position_scale(self.pen.phys.xpos, self.pen.phys.ypos,\
            self.options.units)

    def current_pen(self):
        '''Interactive context: Report last known physical pen state '''
        return self.pen.phys.z_up
