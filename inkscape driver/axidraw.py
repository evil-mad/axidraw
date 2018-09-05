# coding=utf-8
# axidraw.py
# Part of the AxiDraw driver for Inkscape
# https://github.com/evil-mad/AxiDraw
#
# See version_string below for current version and date.
#
# Copyright 2018 Windell H. Oskay, Evil Mad Scientist Laboratories
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
#
# Requires Pyserial 2.7.0 or newer. Pyserial 3.0 recommended.

import copy
import gettext
import math
import os
import sys
import time
from array import array

# Handle a few potential locations of this and its required files
libpath = os.path.join('pyaxidraw', 'lib')
sys.path.append('pyaxidraw')
sys.path.append(libpath)
# sys.path.append('lib')

import ebb_serial  # Requires v 0.13 in plotink
import ebb_motion  # Requires v 0.16 in plotink     https://github.com/evil-mad/plotink
    
import plot_utils  # Requires v 0.10 in plotink
import axidraw_conf  # Some settings can be changed here.

import inkex       # Forked from Inkscape's extension framework
import simplepath
import simplestyle
import cubicsuperpath
from simpletransform import applyTransformToPath, composeTransform, parseTransform

from lxml import etree

try:
    xrange = xrange  # We have Python 2
except NameError:
    xrange = range  # We have Python 3
try:
    # noinspection PyCompatibility
    basestring
except NameError:
    basestring = str

class AxiDraw(inkex.Effect):

    def __init__(self):
        inkex.Effect.__init__(self)

        self.OptionParser.add_option("--mode",\
            action="store", type="string", dest="mode",\
            default="plot", \
            help="Mode or GUI tab. One of: [plot, layers, align, toggle, manual"\
            + ", sysinfo, version,  res_plot, res_home]. Default: plot.")
            
        self.OptionParser.add_option("--speed_pendown",\
            type="int", action="store", dest="speed_pendown", \
            default=axidraw_conf.speed_pendown, \
            help="Maximum plotting speed, when pen is down (1-100)")
            
        self.OptionParser.add_option("--speed_penup",\
            type="int", action="store", dest="speed_penup", \
            default=axidraw_conf.speed_penup, \
            help="Maximum transit speed, when pen is up (1-100)")

        self.OptionParser.add_option("--accel",\
            type="int", action="store", dest="accel", \
            default=axidraw_conf.accel, \
            help="Acceleration rate factor (1-100)")

        self.OptionParser.add_option("--pen_pos_down",\
            type="int", action="store", dest="pen_pos_down",\
            default=axidraw_conf.pen_pos_down,\
            help="Height of pen when lowered (0-100)")

        self.OptionParser.add_option("--pen_pos_up",\
            type="int", action="store", dest="pen_pos_up", \
            default=axidraw_conf.pen_pos_up, \
            help="Height of pen when raised (0-100)")

        self.OptionParser.add_option("--pen_rate_lower",\
            type="int", action="store", dest="pen_rate_lower",\
            default=axidraw_conf.pen_rate_lower, \
            help="Rate of lowering pen (1-100)")

        self.OptionParser.add_option("--pen_rate_raise",\
            type="int", action="store", dest="pen_rate_raise",\
            default=axidraw_conf.pen_rate_raise,\
            help="Rate of raising pen (1-100)")
    
        self.OptionParser.add_option("--pen_delay_down",\
            type="int", action="store", dest="pen_delay_down",\
            default=axidraw_conf.pen_delay_down,\
            help="Optional delay after pen is lowered (ms)")
                     
        self.OptionParser.add_option("--pen_delay_up",\
            type="int", action="store", dest="pen_delay_up", \
            default=axidraw_conf.pen_delay_up,\
            help="Optional delay after pen is raised (ms)")
          
        self.OptionParser.add_option("--no_rotate",\
            type="inkbool", action="store", dest="no_rotate",\
           default=False,\
           help="Disable auto-rotate; preserve plot orientation")
           
        self.OptionParser.add_option("--const_speed",\
            type="inkbool", action="store", dest="const_speed",\
            default=axidraw_conf.const_speed,\
            help="Use constant velocity when pen is down")
         
        self.OptionParser.add_option("--report_time",\
            type="inkbool", action="store", dest="report_time",\
            default=axidraw_conf.report_time,\
            help="Report time elapsed")
        
        self.OptionParser.add_option("--manual_cmd",\
            type="string", action="store", dest="manual_cmd",\
            default="ebb_version",\
            help="Manual command. One of: [ebb_version, raise_pen, lower_pen, " \
            + "walk_x, walk_y, enable_xy, disable_xy, bootload, strip_data, " \
            + "read_name, list_names,  write_name]. Default: ebb_version")
        
        self.OptionParser.add_option("--walk_dist",\
            type="float", action="store", dest="walk_dist",\
            default=1,\
            help="Distance for manual walk (inches)")

        self.OptionParser.add_option("--layer",\
            type="int", action="store", dest="layer",\
            default=axidraw_conf.default_Layer,\
            help="Layer(s) selected for layers mode (1-1000). Default: 1")

        self.OptionParser.add_option("--copies",\
            type="int", action="store", dest="copies",\
            default=axidraw_conf.copies,\
            help="Copies to plot, or 0 for continuous plotting. Default: 1")
            
        self.OptionParser.add_option("--page_delay",\
            type="int", action="store", dest="page_delay",\
            default=axidraw_conf.page_delay,\
            help="Optional delay between copies (s).")

        self.OptionParser.add_option("--preview",\
            type="inkbool", action="store", dest="preview",\
            default=axidraw_conf.preview,\
            help="Preview mode; simulate plotting only.")
            
        self.OptionParser.add_option("--rendering",\
            type="int", action="store", dest="rendering",\
            default=axidraw_conf.rendering,\
            help="Preview mode rendering option (0-3). 0: None. " \
            + "1: Pen-down movement. 2: Pen-up movement. 3: All movement.")

        self.OptionParser.add_option("--model",\
            type="int", action="store", dest="model",\
            default=axidraw_conf.model,\
            help="AxiDraw Model (1-3). 1: AxiDraw V2 or V3. " \
            + "2:AxiDraw V3/A3. 3: AxiDraw V3 XLX.")
            
        self.OptionParser.add_option("--port",\
            type="string", action="store", dest="port",\
            default=axidraw_conf.port,\
            help="Serial port or named AxiDraw to use")

        self.OptionParser.add_option("--port_config",\
            type="int", action="store", dest="port_config",\
            default=axidraw_conf.port_config,\
            help="Port use code (0-2)."\
            +" 0: Plot to first unit found, unless port is specified"\
            + "1: Plot to first AxiDraw Found. "\
            + "2: Plot to specified AxiDraw. ")
            
        self.OptionParser.add_option("--setup_type",\
            type="string", action="store", dest="setup_type",\
            default="align",\
            help="Setup option selected (GUI Only)")
            
        self.OptionParser.add_option("--resume_type",\
            type="string", action="store", dest="resume_type",\
            default="plot",
            help="The resume option selected (GUI Only)")

        self.OptionParser.add_option("--auto_rotate",\
            type="inkbool", action="store", dest="auto_rotate",\
            default=axidraw_conf.auto_rotate,\
            help="Boolean: Auto select portrait vs landscape (GUI Only)")       

        self.OptionParser.add_option("--resolution",\
            type="int", action="store", dest="resolution",\
            default=axidraw_conf.resolution,\
            help="Resolution option selected (GUI Only)")

        self.version_string = "AxiDraw Control - Version 2.1.3, 2018-09-04."
        self.spew_debugdata = False

        self.delay_between_copies = False  # Not currently delaying between copies
        self.ignore_limits = False
        self.set_defaults()
        self.pen_up = None  # Initial state of pen is neither up nor down, but _unknown_.
        self.virtual_pen_up = False  # Keeps track of pen postion when stepping through plot before resuming
        self.Secondary = False

    def set_defaults(self):
        # Set default values of certain parameters
        # These are set when the class is initialized.
        # Also called in plot_run(), to ensure that
        # these defaults are set before plotting additional pages.
        
        self.svg_layer_old = int(0)
        self.svg_node_count_old = int(0)
        self.svg_last_path_old = int(0)
        self.svg_last_path_nc_old = int(0)
        self.svg_last_known_pos_x_old = float(0.0)
        self.svg_last_known_pos_y_old = float(0.0)
        self.svg_paused_pos_x_old = float(0.0)
        self.svg_paused_pos_y_old = float(0.0)
        self.svg_rand_seed_old = float(1.0)
        self.svg_row_old = int(0)
        self.svg_application_old = ""
        self.use_custom_layer_speed = False
        self.use_custom_layer_pen_height = False
        self.resume_mode = False
        self.b_stopped = False
        self.serial_port = None
        self.force_pause = False  # Flag to initiate forced pause
        self.node_count = int(0)  # NOTE: python uses 32-bit ints.
        self.x_bounds_min = axidraw_conf.StartPosX
        self.y_bounds_min = axidraw_conf.StartPosY
        self.svg_transform = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        
        
    def update_options(self):
        # Parse and update certain options; called in effect and in interactive modes
        # whenever the options are updated 
        
        # Plot area bounds, based on AxiDraw model:
        # These bounds may be restricted further by (e.g.,) document size.
        if self.options.model == 2:
            self.x_bounds_max = axidraw_conf.XTravel_V3A3
            self.y_bounds_max = axidraw_conf.YTravel_V3A3
        elif self.options.model == 3:
            self.x_bounds_max = axidraw_conf.XTravel_V3XLX
            self.y_bounds_max = axidraw_conf.YTravel_V3XLX
        else:
            self.x_bounds_max = axidraw_conf.XTravel_Default
            self.y_bounds_max = axidraw_conf.YTravel_Default

        self.bounds = [[self.x_bounds_min,self.y_bounds_min],
                       [self.x_bounds_max,self.y_bounds_max]]

        self.x_max_phy = self.x_bounds_max  # Copy for physical limit reference
        self.y_max_phy = self.y_bounds_max

        self.speed_pendown = axidraw_conf.speed_pendown * axidraw_conf.SpeedLimXY_HR / 110.0  # Speed given as maximum inches/second in XY plane
        self.speed_penup = axidraw_conf.speed_penup * axidraw_conf.SpeedLimXY_HR / 110.0  # Speed given as maximum inches/second in XY plane

        # Input limit checking::
        self.options.pen_pos_up = plot_utils.constrainLimits(self.options.pen_pos_up, 0, 100)  # Constrain input values
        self.options.pen_pos_down = plot_utils.constrainLimits(self.options.pen_pos_down, 0, 100)  # Constrain input values
        self.options.pen_rate_raise = plot_utils.constrainLimits(self.options.pen_rate_raise, 1, 200)  # Prevent zero speed
        self.options.pen_rate_lower = plot_utils.constrainLimits(self.options.pen_rate_lower, 1, 200)  # Prevent zero speed
        self.options.speed_pendown = plot_utils.constrainLimits(self.options.speed_pendown, 1, 110)  # Prevent zero speed
        self.options.speed_penup =   plot_utils.constrainLimits(self.options.speed_penup, 1, 200)    # Prevent zero speed
        self.options.accel =   plot_utils.constrainLimits(self.options.accel, 1, 110)    # Prevent zero speed
        

    def effect(self):
        """Main entry point: check to see which mode/tab is selected, and act accordingly."""

        self.start_time = time.time()

        try:
            self.Secondary
        except AttributeError:
            self.Secondary = False

        self.text_out = '' # Text log for basic communication messages
        self.error_out = '' # Text log for significant errors
        
        self.pt_estimate = 0.0  # plot time estimate, milliseconds

        self.doc_units = "in"
        self.doc_unit_scale_factor = 1

        f_x = None
        f_y = None
        self.f_curr_x = axidraw_conf.StartPosX
        self.f_curr_y = axidraw_conf.StartPosY
        self.pt_first = (axidraw_conf.StartPosX, axidraw_conf.StartPosY)
        self.f_speed = 1
        self.node_target = int(0)
        self.pathcount = int(0)
        self.layers_found_to_plot = False
        self.layer_pen_pos_down = -1
        self.layer_speed_pendown = -1
        self.s_current_layer_name = ''
        self.copies_to_plot = 1

        # New values to write to file:
        self.svg_layer = int(0)
        self.svg_node_count = int(0)
        self.svg_data_read = False
        self.svg_data_written = False
        self.svg_last_path = int(0)
        self.svg_last_path_nc = int(0)
        self.svg_last_known_pos_x = float(0.0)
        self.svg_last_known_pos_y = float(0.0)
        self.svg_paused_pos_x = float(0.0)
        self.svg_paused_pos_y = float(0.0)
        self.svg_rand_seed = float(1.0)
        self.svg_width = 0
        self.svg_height = 0
        self.rotate_page = False
        
        self.print_in_layers_mode = False
        self.use_tag_nest_level = 0

        self.speed_pendown = axidraw_conf.speed_pendown * axidraw_conf.SpeedLimXY_HR / 110.0  # Speed given as maximum inches/second in XY plane
        self.speed_penup = axidraw_conf.speed_penup * axidraw_conf.SpeedLimXY_HR / 110.0  # Speed given as maximum inches/second in XY plane

        self.update_options()

        # So that we only generate a warning once for each
        # unsupported SVG element, we use a dictionary to track
        # which elements have received a warning
        self.warnings = {}
        self.warn_out_of_bounds = False

        self.pen_up_travel_inches = 0.0
        self.pen_down_travel_inches = 0.0
        self.path_data_pu = []  # pen-up path data for preview layers
        self.path_data_pd = []  # pen-down path data for preview layers
        self.path_data_pen_up = -1  # A value of -1 indicates an indeterminate state- requiring new "M" in path.
        # self.PreviewScaleFactor = 1.0 # Allow scaling in case of non-viewbox rendering

        self.vel_data_plot = False
        self.vel_data_time = 0
        self.vel_data_chart1 = []  # Velocity visualization, for preview of velocity vs time Motor 1
        self.vel_data_chart2 = []  # Velocity visualization, for preview of velocity vs time Motor 2
        self.vel_data_chart_t = []  # Velocity visualization, for preview of velocity vs time Total V

        skip_serial = False
        if self.options.preview:
            skip_serial = True

        # Input sanitization:
        self.options.mode = self.options.mode.strip("\"")
        self.options.setup_type = self.options.setup_type.strip("\"")
        self.options.manual_cmd = self.options.manual_cmd.strip("\"")
        self.options.resume_type = self.options.resume_type.strip("\"")

        try:
            self.called_externally
        except AttributeError:
            self.called_externally = False
    
        if self.options.mode == "options":
            return
        if self.options.mode == "timing":
            return
        if self.options.mode == "version":
            # Return the version of _this python script_.
            self.text_log(self.version_string)
            return
        if self.options.mode == "manual":
            if self.options.manual_cmd == "none":
                return  # No option selected. Do nothing and return no error.
            elif self.options.manual_cmd == "strip_data":
                self.svg = self.document.getroot()
                for node in self.svg.xpath('//svg:WCB', namespaces=inkex.NSS):
                    self.svg.remove(node)
                for node in self.svg.xpath('//svg:eggbot', namespaces=inkex.NSS):
                    self.svg.remove(node)
                self.text_log(gettext.gettext("All AxiDraw data has been removed from this SVG file."))
                return
            elif self.options.manual_cmd == "list_names":
                name_list = ebb_serial.list_named_ebbs() # does not require connection to AxiDraw
                if not name_list:
                    self.text_log(gettext.gettext("No named AxiDraw units located.\n"))
                else:
                    self.text_log(gettext.gettext("List of attached AxiDraw units:"))
                    for EBB in name_list:
                        self.text_log(EBB)
                return    
                
        if self.options.mode == "sysinfo":
            self.options.mode = "manual"  # Use "manual" command mechanism to handle sysinfo request.
            self.options.manual_cmd = "sysinfo"

        if self.options.mode == "resume":
            # resume mode + resume_type -> either  res_plot or res_home modes.
            if self.options.resume_type == "home":
                self.options.mode = "res_home"
            else:
                self.options.mode = " res_plot"

        if self.options.mode == "setup":
            # setup mode + setup_type -> either align or toggle modes.
            if self.options.setup_type == "align":
                self.options.mode = "align"
            else:
                self.options.mode = "toggle"

        if not skip_serial:
            self.serial_connect()
            if self.serial_port is None:
                return

        self.svg = self.document.getroot()
        self.ReadWCBdata(self.svg)

        resume_data_needs_updating = False

        if self.options.page_delay < 0:
            self.options.page_delay = 0

        if self.options.mode == "plot":
            self.copies_to_plot = self.options.copies
            if self.copies_to_plot == 0:
                self.copies_to_plot = -1
                if self.options.preview:  
                    # Special case: 0 (continuous copies), but in preview mode.
                    self.copies_to_plot = 1  
                    # In this case, revert back to single copy, since there is
                    # no way to terminate. Canceling is initiated by 
                    # USB/button press!
            while self.copies_to_plot != 0:
                self.layers_found_to_plot = False
                resume_data_needs_updating = True
                self.svg_rand_seed = round(time.time() * 100) / 100  # New random seed for new plot

                self.print_in_layers_mode = False
                self.plot_current_layer = True
                self.svg_node_count = 0
                self.svg_last_path = 0
                self.svg_layer = 12345  # indicate (to resume routine) that we are plotting all layers.

                self.delay_between_copies = False  # Indicate that we are not currently delaying between copies
                self.copies_to_plot -= 1
                self.plot_document()
                self.delay_between_copies = True  # Indicate that we are currently delaying between copies

                time_counter = 10 * self.options.page_delay
                while time_counter > 0:
                    time_counter -= 1
                    if self.copies_to_plot != 0 and not self.b_stopped:  # Delay if we're between copies, not after the last or paused.
                        if self.options.preview:
                            self.pt_estimate += 100
                        else:
                            time.sleep(0.100)  # Use short intervals to improve responsiveness
                            self.PauseResumeCheck()  # Detect button press while paused between plots
                            if self.b_stopped:
                                self.copies_to_plot = 0

        elif self.options.mode == "res_home" or self.options.mode == " res_plot":
            resume_data_needs_updating = True
            self.resumePlotSetup()
            if self.resume_mode:
                self.plot_document()
            elif self.options.mode == "res_home":
                if not self.svg_data_read or (self.svg_last_known_pos_x_old == 0 and self.svg_last_known_pos_y_old == 0):
                    self.text_log(gettext.gettext("No resume data found; unable to return to home position."))
                else:
                    self.plot_document()
                    self.svg_node_count = self.svg_node_count_old  # Write old values back to file, to resume later.
                    self.svg_last_path = self.svg_last_path_old
                    self.svg_last_path_nc = self.svg_last_path_nc_old
                    self.svg_paused_pos_x = self.svg_paused_pos_x_old
                    self.svg_paused_pos_y = self.svg_paused_pos_y_old
                    self.svg_layer = self.svg_layer_old
                    self.svg_rand_seed = self.svg_rand_seed_old
            else:
                self.text_log(gettext.gettext("No in-progress plot data found in file."))

        elif self.options.mode == "layers":
            self.copies_to_plot = self.options.copies
            if self.copies_to_plot == 0:
                self.copies_to_plot = -1
                if self.options.preview:  # Special case: 0 (continuous copies) selected, but running in preview mode.
                    self.copies_to_plot = 1  # In this case, revert back to single copy, since there's no way to terminate.
            while self.copies_to_plot != 0:
                resume_data_needs_updating = True
                self.svg_rand_seed = time.time()  # New random seed for new plot
                self.print_in_layers_mode = True
                self.plot_current_layer = False
                self.layers_found_to_plot = False
                self.svg_last_path = 0
                self.svg_node_count = 0
                self.svg_layer = self.options.layer
                self.delay_between_copies = False
                self.copies_to_plot -= 1
                self.plot_document()
                self.delay_between_copies = True  # Indicate that we are currently delaying between copies
                time_counter = 10 * self.options.page_delay
                while time_counter > 0:
                    time_counter -= 1
                    if self.copies_to_plot != 0 and not self.b_stopped:
                        if self.options.preview:
                            self.pt_estimate += 100
                        else:
                            time.sleep(0.100)  # Use short intervals to improve responsiveness
                            self.PauseResumeCheck()  # Detect button press while paused between plots

        elif self.options.mode == "align" or self.options.mode == "toggle":
            self.setup_command()

        elif self.options.mode == "manual":
            self.manual_command()  # Handle manual commands that use both power and usb.

        if resume_data_needs_updating:
            self.UpdateSVGWCBData(self.svg)
        if self.serial_port is not None:
            ebb_motion.doTimedPause(self.serial_port, 10)  # Pause a moment for underway commands to finish.
            if self.options.port is None:  # Do not close serial port if it was opened externally.
                ebb_serial.closePort(self.serial_port)

    def resumePlotSetup(self):
        self.layer_found = False
        if 0 <= self.svg_layer_old < 101:
            self.options.layer = self.svg_layer_old
            self.print_in_layers_mode = True
            self.plot_current_layer = False
            self.layer_found = True
        elif self.svg_layer_old == 12345:  # Plot all layers
            self.print_in_layers_mode = False
            self.plot_current_layer = True
            self.layer_found = True
        if self.layer_found:
            if self.svg_node_count_old > 0:
                self.node_target = self.svg_node_count_old
                self.svg_layer = self.svg_layer_old
                self.ServoSetupWrapper()
                self.pen_raise()
                self.EnableMotors()  # Set plotting resolution
                if self.options.mode == " res_plot":
                    self.resume_mode = True
                self.f_speed = self.speed_pendown
                self.f_curr_x = self.svg_last_known_pos_x_old + axidraw_conf.StartPosX
                self.f_curr_y = self.svg_last_known_pos_y_old + axidraw_conf.StartPosY
                self.svg_rand_seed = self.svg_rand_seed_old  # Use old random seed value
                if self.spew_debugdata:
                    self.text_log('Entering resume mode at layer:  ' + str(self.svg_layer))

    def ReadWCBdata(self, svg_to_check):
        # Read plot progress data, stored in a custom "WCB" XML element
        self.svg_data_read = False
        wcb_node = None
        for node in svg_to_check:
            if node.tag == 'svg':
                for subNode in svg_to_check:
                    if subNode.tag == inkex.addNS('WCB', 'svg') or subNode.tag == 'WCB':
                        wcb_node = subNode
            elif node.tag == inkex.addNS('WCB', 'svg') or node.tag == 'WCB':
                wcb_node = node
        if wcb_node is not None:
            try:
                self.svg_layer_old = int(wcb_node.get('layer'))
                self.svg_node_count_old = int(wcb_node.get('node'))
                self.svg_last_path_old = int(wcb_node.get('lastpath'))
                self.svg_last_path_nc_old = int(wcb_node.get('lastpathnc'))
                self.svg_last_known_pos_x_old = float(wcb_node.get('lastknownposx'))
                self.svg_last_known_pos_y_old = float(wcb_node.get('lastknownposy'))
                self.svg_paused_pos_x_old = float(wcb_node.get('pausedposx'))
                self.svg_paused_pos_y_old = float(wcb_node.get('pausedposy'))
                self.svg_application_old = str(wcb_node.get('application'))
                self.svg_data_read = True
            except TypeError:
                self.svg.remove(wcb_node)  # An error before this point leaves svg_data_read as False.
                # Also remove the node, to prevent adding a duplicate WCB node later.
            try:
                # Check for additonal, optional attributes:
                self.svg_rand_seed_old = float(wcb_node.get('randseed'))
                self.svg_row_old = float(wcb_node.get('row'))
            except TypeError:
                pass  # Leave as default if not found

    def UpdateSVGWCBData(self, a_node_list):
        if not self.svg_data_read:
            wcb_data = etree.SubElement(self.svg, 'WCB')
            self.svg_data_read = True  # Ensure that we don't keep adding WCB elements
        if not self.svg_data_written:
            for node in a_node_list:
                if node.tag == 'svg':
                    self.UpdateSVGWCBData(node)
                elif node.tag == inkex.addNS('WCB', 'svg') or node.tag == 'WCB':
                    node.set('layer', str(self.svg_layer))
                    node.set('node', str(self.svg_node_count))
                    node.set('lastpath', str(self.svg_last_path))
                    node.set('lastpathnc', str(self.svg_last_path_nc))
                    node.set('lastknownposx', str(self.svg_last_known_pos_x))
                    node.set('lastknownposy', str(self.svg_last_known_pos_y))
                    node.set('pausedposx', str(self.svg_paused_pos_x))
                    node.set('pausedposy', str(self.svg_paused_pos_y))
                    node.set('randseed', str(self.svg_rand_seed))
                    node.set('application', "Axidraw")  # Name of this program
                    self.svg_data_written = True

    def setup_command(self):
        """
        Execute commands from the setup modes
        """

        if self.options.preview:
            self.text_log('Command unavailable while in preview mode.')
            return

        if self.serial_port is None:
            return

        self.queryEBBVoltage()

        self.ServoSetupWrapper()

        if self.options.mode == "align":
            self.pen_raise()
            ebb_motion.sendDisableMotors(self.serial_port)
        elif self.options.mode == "toggle":
            ebb_motion.TogglePen(self.serial_port)

    def manual_command(self):
        """
        Execute commands in the "manual" mode/tab
        """

        # First: Commands that require serial but not power:
        if self.options.preview:
            self.text_log('Command unavailable while in preview mode.')
            return

        if self.serial_port is None:
            return

        if self.options.manual_cmd == "sysinfo":
            ebb_version_string = ebb_serial.queryVersion(self.serial_port)  # Full string, human readable
            self.text_log('EBB version information:\n ' + ebb_version_string)
            self.text_log('Additional system information:')
            self.text_log(gettext.gettext(self.version_string))
            self.text_log(sys.version)
            return

        if self.options.manual_cmd == "ebb_version":
            ebb_version_string = ebb_serial.queryVersion(self.serial_port)  # Full string, human readable
            self.text_log(ebb_version_string)
            return

        if self.options.manual_cmd == "bootload":
            success = ebb_serial.bootload(self.serial_port)
            if success == True:
                self.text_log(gettext.gettext("Entering bootloader mode for firmware programming.\n" +
                                           "To resume normal operation, you will need to first\n" +
                                           "disconnect the AxiDraw from both USB and power."))
                ebb_serial.closePort(self.serial_port) # Manually close port
                self.serial_port = None                # Indicate that serial port is closed.
            else:
                self.text_log('Failed while trying to enter bootloader.')
            return

        if self.options.manual_cmd == "read_name":
            name_string = ebb_serial.query_nickname(self.serial_port)
            if name_string is None:
                self.error_log(gettext.gettext("Error; unable to read nickname.\n"))
            else:
                self.text_log(name_string)
            return

        if (self.options.manual_cmd).startswith("write_name"):
            temp_string = self.options.manual_cmd
            temp_string = temp_string.split("write_name",1)[1] # Get part after "write_name"
            temp_string = temp_string[:16] # Only use first 16 characters in name
            if not temp_string:
                temp_string = "" # Use empty string to clear nickname.
            version_status = ebb_serial.min_version(self.serial_port, "2.5.5")
            if version_status:
                renamed = ebb_serial.write_nickname(self.serial_port, temp_string)
                if renamed is True:
                    self.text_log('Nickname written. Rebooting EBB.')
                else:
                    self.error_log('Error encountered while writing nickname.')
                ebb_serial.reboot(self.serial_port)    # Reboot required after writing nickname
                ebb_serial.closePort(self.serial_port) # Manually close port
                self.serial_port = None                # Indicate that serial port is closed.
            else:
                self.error_log("AxiDraw naming requires firmware version 2.5.5 or higher.")
            return
            
        # Next: Commands that require both power and serial connectivity:
        self.queryEBBVoltage()
        # Query if button pressed, to clear the result:
        ebb_motion.QueryPRGButton(self.serial_port)  
        if self.options.manual_cmd == "raise_pen":
            self.ServoSetupWrapper()
            self.pen_raise()
        elif self.options.manual_cmd == "lower_pen":
            self.ServoSetupWrapper()
            self.pen_lower()
        elif self.options.manual_cmd == "enable_xy":
            self.EnableMotors()
        elif self.options.manual_cmd == "disable_xy":
            ebb_motion.sendDisableMotors(self.serial_port)
        else:  # self.options.manual_cmd is walk motor:
            if self.options.manual_cmd == "walk_y":
                n_delta_x = 0
                n_delta_y = self.options.walk_dist
            elif self.options.manual_cmd == "walk_x":
                n_delta_y = 0
                n_delta_x = self.options.walk_dist
            else:
                return

            self.f_speed = self.speed_pendown

            self.EnableMotors()  # Set plotting resolution
            self.f_curr_x = self.svg_last_known_pos_x_old + axidraw_conf.StartPosX
            self.f_curr_y = self.svg_last_known_pos_y_old + axidraw_conf.StartPosY
            self.ignore_limits = True
            f_x = self.f_curr_x + n_delta_x  # Note: Walking motors is strictly relative to initial position.
            f_y = self.f_curr_y + n_delta_y  # New position is not saved, this may interfere with resuming plots.
            self.plotSegmentWithVelocity(f_x, f_y, 0, 0)

    def updateVCharts(self, v1, v2, v_total):
        # Update velocity charts, using some appropriate scaling for X and Y display.
        temp_time = self.doc_unit_scale_factor * self.vel_data_time / 1000.0
        scale_factor = 10.0 / self.options.resolution
        self.vel_data_chart1.append(" {0:0.3f} {1:0.3f}".format(temp_time, 8.5 - self.doc_unit_scale_factor * v1 / scale_factor))
        self.vel_data_chart2.append(" {0:0.3f} {1:0.3f}".format(temp_time, 8.5 - self.doc_unit_scale_factor * v2 / scale_factor))
        self.vel_data_chart_t.append(" {0:0.3f} {1:0.3f}".format(temp_time, 8.5 - self.doc_unit_scale_factor * v_total / scale_factor))

    def plot_document(self):
        # Plot the actual SVG document, if so selected in the interface
        # parse the svg data as a series of line segments and send each segment to be plotted

        if not self.getDocProps():
            # Error: This document appears to have inappropriate (or missing) dimensions.
            self.text_log(gettext.gettext('This document does not have valid dimensions.\r'))
            self.text_log(gettext.gettext('The page size must be in either millimeters (mm) or inches (in).\r\r'))
            self.text_log(gettext.gettext('Consider starting with the Letter landscape or '))
            self.text_log(gettext.gettext('the A4 landscape template.\r\r'))
            self.text_log(gettext.gettext('The page size may also be set in Inkscape,\r'))
            self.text_log(gettext.gettext('using File > Document Properties.'))
            return

        user_units_width = plot_utils.unitsToUserUnits("1in")
        self.doc_unit_scale_factor = plot_utils.userUnitToUnits(user_units_width, self.doc_units)

        if not self.options.preview:
            self.options.rendering = 0  # Only render previews if we are in preview mode.
            vel_data_plot = False
            if self.serial_port is None:
                return
            self.queryEBBVoltage()
            unused = ebb_motion.QueryPRGButton(self.serial_port)  # Initialize button-press detection

        # Modifications to SVG -- including re-ordering and text substitution may be made at this point, and will not be preserved.

        # Viewbox handling
        # Ignores translations and the preserveAspectRatio attribute

        viewbox = self.svg.get('viewBox')
        if viewbox:
            vinfo = viewbox.strip().replace(',', ' ').split(' ')
            offset0 = -float(vinfo[0])
            offset1 = -float(vinfo[1])
            if vinfo[2] != 0:
                # TODO: Handle a wider yet range of viewBox formats and values
                sx = self.svg_width / float(vinfo[2])
                if vinfo[3] != 0:
                    sy = self.svg_height / float(vinfo[3])
                else:
                    sy = sx
                self.doc_unit_scale_factor = 1.0 / sx  # Scale preview to viewbox
        else:
            # Handle case of no viewbox provided.
            sx = 1.0 / float(plot_utils.PX_PER_INCH)
            sy = sx
            offset0 = 0.0
            offset1 = 0.0

        self.svg_transform = parseTransform('scale({0:f},{1:f}) translate({2:f},{3:f})'.format(sx, sy, offset0, offset1))

        if axidraw_conf.clip_to_page: # Clip at edges of page size (default)
            if self.rotate_page:
                if self.y_bounds_max > self.svg_width:
                    self.y_bounds_max = self.svg_width
                if self.x_bounds_max > self.svg_height:
                    self.x_bounds_max = self.svg_height
            else:
                if self.x_bounds_max > self.svg_width:
                    self.x_bounds_max = self.svg_width
                if self.y_bounds_max > self.svg_height:
                    self.y_bounds_max = self.svg_height
            self.bounds = [[self.x_bounds_min,self.y_bounds_min],
                           [self.x_bounds_max,self.y_bounds_max]]

        try:  # wrap everything in a try so we can be sure to close the serial port
            self.ServoSetupWrapper()
            self.pen_raise()
            self.EnableMotors()  # Set plotting resolution

            if self.options.mode == "res_home" or self.options.mode == " res_plot":
                if self.resume_mode:
                    f_x = self.svg_paused_pos_x_old + axidraw_conf.StartPosX
                    f_y = self.svg_paused_pos_y_old + axidraw_conf.StartPosY
                    self.resume_mode = False
                    self.plotSegmentWithVelocity(f_x, f_y, 0, 0)  # pen-up move to starting point
                    self.resume_mode = True
                    self.node_count = 0
                else:  # i.e., ( self.options.mode == "res_home" ):
                    f_x = axidraw_conf.StartPosX
                    f_y = axidraw_conf.StartPosY
                    self.plotSegmentWithVelocity(f_x, f_y, 0, 0)
                    return

            # Call the recursive routine to plot the document:
            self.traverse_svg(self.svg, self.svg_transform)
            self.pen_raise()  # Always end with pen-up

            # Return to home after end of normal plot:
            if not self.b_stopped and self.pt_first:
                self.x_bounds_min = axidraw_conf.StartPosX
                self.y_bounds_min = axidraw_conf.StartPosY
                f_x = self.pt_first[0]
                f_y = self.pt_first[1]
                self.node_count = self.node_target
                self.plotSegmentWithVelocity(f_x, f_y, 0, 0)

            """
            Revert back to original SVG document, prior to adding preview layers.
             and prior to saving updated "WCB" progress data in the file.
             No changes to the SVG document prior to this point will be saved.
            
             Doing so allows us to use routines that alter the SVG
             prior to this point -- e.g., plot re-ordering for speed 
             or font substitutions.
            """

            try:
                # If called from an external script that specifies a "backup_original",
                # revert to _that_, rather than the true original
                self.document = copy.deepcopy(self.backup_original)
                self.svg = self.document.getroot()
            except AttributeError:
                self.document = copy.deepcopy(self.original_document)
                self.svg = self.document.getroot()

            if not self.b_stopped:
                if self.options.mode in ["plot", "layers", "res_home", " res_plot"]:
                    # Clear saved plot data from the SVG file,
                    # IF we have _successfully completed_ a normal plot from the plot, layer, or resume mode.
                    self.svg_layer = 0
                    self.svg_node_count = 0
                    self.svg_last_path = 0
                    self.svg_last_path_nc = 0
                    self.svg_last_known_pos_x = 0
                    self.svg_last_known_pos_y = 0
                    self.svg_paused_pos_x = 0
                    self.svg_paused_pos_y = 0
                    self.svg_rand_seed = 0

            if self.warn_out_of_bounds:
                warning_text = "Warning: AxiDraw movement was limited by its "
                warning_text += "physical range of motion. If everything looks "
                warning_text += "right, your document may have an error with "
                warning_text += "its units or scaling. Contact technical "
                warning_text += "support for help."
                self.text_log(gettext.gettext(warning_text))

            if self.options.preview:
                # Remove old preview layers, whenever preview mode is enabled
                for node in self.svg:
                    if node.tag == inkex.addNS('g', 'svg') or node.tag == 'g':
                        if node.get(inkex.addNS('groupmode', 'inkscape')) == 'layer':
                            layer_name = node.get(inkex.addNS('label', 'inkscape'))
                            if layer_name == '% Preview':
                                self.svg.remove(node)

            if self.options.rendering > 0:  # Render preview. Only possible when in preview mode.
                self.previewLayer = etree.Element(inkex.addNS('g', 'svg'))
                self.previewSLU = etree.SubElement(self.previewLayer, inkex.addNS('g', 'svg'))
                self.previewSLD = etree.SubElement(self.previewLayer, inkex.addNS('g', 'svg'))

                self.previewLayer.set(inkex.addNS('groupmode', 'inkscape'), 'layer')
                self.previewLayer.set(inkex.addNS('label', 'inkscape'), '% Preview')
                self.previewSLD.set(inkex.addNS('groupmode', 'inkscape'), 'layer')
                self.previewSLD.set(inkex.addNS('label', 'inkscape'), '% Pen-down drawing')
                self.previewSLU.set(inkex.addNS('groupmode', 'inkscape'), 'layer')
                self.previewSLU.set(inkex.addNS('label', 'inkscape'), '% Pen-up transit')
                self.svg.append(self.previewLayer)

                stroke_width = "0.2mm"  # Adjust this here, in your preferred units.

                width_uu = plot_utils.unitsToUserUnits(stroke_width)  # Convert stroke width to user units (typ. px)
                width_du = plot_utils.userUnitToUnits(width_uu, self.doc_units)  # Convert to document units (typ. mm)

                line_width_scale_factor = self.doc_unit_scale_factor / plot_utils.PX_PER_INCH

                width_du = width_du * line_width_scale_factor  # Apply scaling

                """
                Important note: stroke-width is a css style element, and cannot accept scientific notation.
                
                In cases with large scaling, i.e., high values of self.doc_unit_scale_factor
                resulting from the viewbox attribute of the SVG document, it may be necessary to use 
                a _very small_ stroke width, so that the stroke width displayed on the screen
                has a reasonable width after being displayed greatly magnified thanks to the viewbox.
                
                Use log10(the number) to determine the scale, and thus the precision needed.
                """

                log_ten = math.log10(width_du)
                if log_ten > 0:  # For width_du > 1
                    width_string = "{0:.3f}".format(width_du) + str(self.doc_units)
                else:
                    prec = int(math.ceil(-log_ten) + 3)
                    width_string = "{0:.{1}f}".format(width_du, prec) + str(self.doc_units)

                p_style = {'stroke-width': width_string, 'fill': 'none', 'stroke-linejoin': 'round', 'stroke-linecap': 'round'}

                ns_prefix = "plot"
                if self.options.rendering > 1:
                    p_style.update({'stroke': 'rgb(255, 159, 159)'})
                    path_attrs = {
                        'style': simplestyle.formatStyle(p_style),
                        'd': " ".join(self.path_data_pu),
                        inkex.addNS('desc', ns_prefix): "pen-up transit"}
                    etree.SubElement(self.previewSLU,
                                     inkex.addNS('path', 'svg '), path_attrs, nsmap=inkex.NSS)

                if self.options.rendering == 1 or self.options.rendering == 3:
                    p_style.update({'stroke': 'blue'})
                    path_attrs = {
                        'style': simplestyle.formatStyle(p_style),
                        'd': " ".join(self.path_data_pd),
                        inkex.addNS('desc', ns_prefix): "pen-down drawing"}
                    etree.SubElement(self.previewSLD,
                                     inkex.addNS('path', 'svg '), path_attrs, nsmap=inkex.NSS)

                if self.options.rendering > 0 and self.vel_data_plot:  # Preview enabled & do velocity Plot
                    self.vel_data_chart1.insert(0, "M")
                    self.vel_data_chart2.insert(0, "M")
                    self.vel_data_chart_t.insert(0, "M")

                    p_style.update({'stroke': 'black'})
                    path_attrs = {
                        'style': simplestyle.formatStyle(p_style),
                        'd': " ".join(self.vel_data_chart_t),
                        inkex.addNS('desc', ns_prefix): "Total V"}
                    etree.SubElement(self.previewLayer,
                                     inkex.addNS('path', 'svg '), path_attrs, nsmap=inkex.NSS)

                    p_style.update({'stroke': 'red'})
                    path_attrs = {
                        'style': simplestyle.formatStyle(p_style),
                        'd': " ".join(self.vel_data_chart1),
                        inkex.addNS('desc', ns_prefix): "Motor 1 V"}
                    etree.SubElement(self.previewLayer,
                                     inkex.addNS('path', 'svg '), path_attrs, nsmap=inkex.NSS)

                    p_style.update({'stroke': 'green'})
                    path_attrs = {
                        'style': simplestyle.formatStyle(p_style),
                        'd': " ".join(self.vel_data_chart2),
                        inkex.addNS('desc', ns_prefix): "Motor 2 V"}
                    etree.SubElement(self.previewLayer,
                                     inkex.addNS('path', 'svg '), path_attrs, nsmap=inkex.NSS)

            if self.options.report_time and (not self.called_externally):
                if self.copies_to_plot == 0: # No copies remaining to plot
                    if self.options.preview:
                        m, s = divmod(self.pt_estimate / 1000.0, 60)
                        h, m = divmod(m, 60)
                        h = int(h)
                        m = int(m)
                        s = int(s)
                        if h > 0:
                            self.text_log("Estimated print time: {0:d}:{1:02d}:{2:02d} (Hours, minutes, seconds)".format(h, m, s))
                        else:
                            self.text_log("Estimated print time: {0:02d}:{1:02d} (minutes, seconds)".format(m, s))

                    elapsed_time = time.time() - self.start_time
                    m, s = divmod(elapsed_time, 60)
                    h, m = divmod(m, 60)
                    h = int(h)
                    m = int(m)
                    s = int(s)
                    down_dist = 0.0254 * self.pen_down_travel_inches
                    tot_dist = down_dist + (0.0254 * self.pen_up_travel_inches)
                    if self.options.preview:
                        self.text_log("Length of path to draw: {0:1.2f} m.".format(down_dist))
                        self.text_log("Total movement distance: {0:1.2f} m.".format(tot_dist))
                        if self.options.rendering > 0:
                            self.text_log("This estimate took: {0:d}:{1:02d}:{2:02d} (Hours, minutes, seconds)".format(h, m, s))
                    else:
                        if h > 0:
                            self.text_log("Elapsed time: {0:d}:{1:02d}:{2:02d} (Hours, minutes, seconds)".format(h, m, s))
                        else:
                            self.text_log("Elapsed time: {0:02d}:{1:02d} (minutes, seconds)".format(m, s))
                        self.text_log("Length of path drawn: {0:1.2f} m.".format(down_dist))
                        self.text_log("Total distance moved: {0:1.2f} m.".format(tot_dist))

        finally:
            # We may have had an exception and lost the serial port...
            pass

    def traverse_svg(self, a_node_list,
                            mat_current=None,
                            parent_visibility='visible'):
        """
        Recursively traverse the SVG file to plot out all of the
        paths.  The function keeps track of the composite transformation
        that should be applied to each path.

        This function handles path, group, line, rect, polyline, polygon,
        circle, ellipse and use (clone) elements.  Notable elements not
        handled include text.  Unhandled elements should be converted to
        paths in Inkscape.
        """

        if mat_current is None:
            mat_current = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

        for node in a_node_list:
            if self.b_stopped:
                return

            style = simplestyle.parseStyle(node.get('style'))

            # Check for "display:none" in the node's style attribute:
            if 'display' in style.keys() and style['display'] == 'none':
                continue  # Do not plot this object or its children

            # The node may have a display="none" attribute as well:
            if node.get('display') == 'none':
                continue  # Do not plot this object or its children

            # Visibility attributes control whether a given object will plot.
            # Children of hidden (not visible) parents may be plotted if
            # they assert visibility.
            visibility = node.get('visibility', parent_visibility)
            if visibility == 'inherit':
                visibility = parent_visibility

            if 'visibility' in style.keys():
                visibility = style['visibility']  # Style may override the attribute.

            # first apply the current matrix transform to this node's transform
            mat_new = composeTransform(mat_current, parseTransform(node.get("transform")))

            if node.tag == inkex.addNS('g', 'svg') or node.tag == 'g':

                # Store old layer status variables before recursively traversing the layer that we just found.
                old_use_custom_layer_pen_height = self.use_custom_layer_pen_height  # A Boolean
                old_use_custom_layer_speed = self.use_custom_layer_speed  # A Boolean
                old_layer_pen_pos_down = self.layer_pen_pos_down  # Numeric value
                old_layer_speed_pendown = self.layer_speed_pendown  # Numeric value

                oldplot_current_layer = self.plot_current_layer
                old_layer_name = self.s_current_layer_name

                if node.get(inkex.addNS('groupmode', 'inkscape')) == 'layer':
                    self.s_current_layer_name = node.get(inkex.addNS('label', 'inkscape'))
                    self.DoWePlotLayer(self.s_current_layer_name)
                    self.pen_raise()
                self.traverse_svg(node, mat_new, parent_visibility=visibility)

                # Restore old layer status variables
                self.use_custom_layer_pen_height = old_use_custom_layer_pen_height
                self.use_custom_layer_speed = old_use_custom_layer_speed

                if self.layer_speed_pendown != old_layer_speed_pendown:
                    self.layer_speed_pendown = old_layer_speed_pendown
                    self.EnableMotors()  # Set speed value variables for this layer.

                if self.layer_pen_pos_down != old_layer_pen_pos_down:
                    self.layer_pen_pos_down = old_layer_pen_pos_down
                    self.ServoSetup()  # Set pen height value variables for this layer.

                self.plot_current_layer = oldplot_current_layer
                self.s_current_layer_name = old_layer_name  # Recall saved layer name after plotting deeper layer

            elif node.tag == inkex.addNS('symbol', 'svg') or node.tag == 'symbol':
                # A symbol is much like a group, except that it should only be rendered when called within a "use" tag.
                if self.use_tag_nest_level > 0:
                    self.traverse_svg(node, mat_new, parent_visibility=visibility)

            elif node.tag == inkex.addNS('a', 'svg') or node.tag == 'a':
                # An 'a' is much like a group, in that it is a generic container element.
                self.traverse_svg(node, mat_new, parent_visibility=visibility)

            elif node.tag == inkex.addNS('use', 'svg') or node.tag == 'use':

                """
                A <use> element refers to another SVG element via an xlink:href="#blah"
                attribute.  We will handle the element by doing an XPath search through
                the document, looking for the element with the matching id="blah"
                attribute.  We then recursively process that element after applying
                any necessary (x,y) translation.
                
                Notes:
                 1. We ignore the height and g attributes as they do not apply to
                    path-like elements, and
                 2. Even if the use element has visibility="hidden", SVG still calls
                    for processing the referenced element.  The referenced element is
                    hidden only if its visibility is "inherit" or "hidden".
                 3. We may be able to unlink clones using the code in pathmodifier.py
                """

                refid = node.get(inkex.addNS('href', 'xlink'))
                if refid is not None:
                    # [1:] to ignore leading '#' in reference
                    path = '//*[@id="{0}"]'.format(refid[1:])
                    refnode = node.xpath(path)
                    if refnode is not None:
                        x = float(node.get('x', '0'))
                        y = float(node.get('y', '0'))
                        # Note: the transform has already been applied
                        if x != 0 or y != 0:
                            mat_new2 = composeTransform(mat_new, parseTransform('translate({0:f},{1:f})'.format(x, y)))
                        else:
                            mat_new2 = mat_new
                        visibility = node.get('visibility', visibility)
                        self.use_tag_nest_level += 1  # Use a number, not a boolean, to keep track of nested "use" elements.
                        self.traverse_svg(refnode, mat_new2, parent_visibility=visibility)
                        self.use_tag_nest_level -= 1
                    else:
                        continue
                else:
                    continue
            elif self.plot_current_layer:  # Skip subsequent tag checks unless we are plotting this layer.
                if visibility == 'hidden' or visibility == 'collapse':
                    continue  # Do not plot this node if it is not visible.
                if node.tag == inkex.addNS('path', 'svg'):

                    """
                    If in resume mode AND self.pathcount < self.svg_last_path, then skip this path.
                    If in resume mode and self.pathcount = self.svg_last_path, then start here, and set
                    self.node_count equal to self.svg_last_path_nc
                    """

                    do_we_plot_this_path = False
                    if self.resume_mode:
                        if self.pathcount < self.svg_last_path_old:  # Fully plotted; skip.
                            self.pathcount += 1
                        elif self.pathcount == self.svg_last_path_old:  # First partially-plotted path
                            self.node_count = self.svg_last_path_nc_old  # node_count after last completed path
                            do_we_plot_this_path = True
                    else:
                        do_we_plot_this_path = True
                    if do_we_plot_this_path:
                        self.pathcount += 1
                        self.plot_path(node, mat_new)

                elif node.tag == inkex.addNS('rect', 'svg') or node.tag == 'rect':

                    """
                    Manually transform 
                       <rect x="X" y="Y" width="W" height="H"/> 
                    into 
                       <path d="MX,Y lW,0 l0,H l-W,0 z"/> 
                    I.e., explicitly draw three sides of the rectangle and the
                    fourth side implicitly
                    
                    If in resume mode AND self.pathcount < self.svg_last_path, then skip this path.
                    If in resume mode and self.pathcount = self.svg_last_path, then start here, and set
                    self.node_count equal to self.svg_last_path_nc
                    """

                    do_we_plot_this_path = False
                    if self.resume_mode:
                        if self.pathcount < self.svg_last_path_old:  # Fully plotted; skip.
                            self.pathcount += 1
                        elif self.pathcount == self.svg_last_path_old:  # First partially-plotted path
                            self.node_count = self.svg_last_path_nc_old  # node_count after last completed path
                            do_we_plot_this_path = True
                    else:
                        do_we_plot_this_path = True
                    if do_we_plot_this_path:
                        self.pathcount += 1
                        # Create (but do not add to SVG) a path with the outline of the rectangle
                        newpath = etree.Element(inkex.addNS('path', 'svg'))

                        x = float(node.get('x'))
                        y = float(node.get('y'))
                        w = float(node.get('width'))
                        h = float(node.get('height'))
                        s = node.get('style')
                        if s:
                            newpath.set('style', s)
                        t = node.get('transform')
                        if t:
                            newpath.set('transform', t)
                        a = []
                        a.append(['M ', [x, y]])
                        a.append([' l ', [w, 0]])
                        a.append([' l ', [0, h]])
                        a.append([' l ', [-w, 0]])
                        a.append([' Z', []])
                        newpath.set('d', simplepath.formatPath(a))
                        self.plot_path(newpath, mat_new)

                elif node.tag == inkex.addNS('line', 'svg') or node.tag == 'line':

                    """
                    Convert
                      <line x1="X1" y1="Y1" x2="X2" y2="Y2/>
                    to
                      <path d="MX1,Y1 LX2,Y2"/>    
                    If in resume mode AND self.pathcount < self.svg_last_path, then skip this path.
                    If in resume mode and self.pathcount = self.svg_last_path, then start here, and set
                    self.node_count equal to self.svg_last_path_nc
                    """

                    do_we_plot_this_path = False
                    if self.resume_mode:
                        if self.pathcount < self.svg_last_path_old:  # Fully plotted; skip.
                            self.pathcount += 1
                        elif self.pathcount == self.svg_last_path_old:  # First partially-plotted path
                            self.node_count = self.svg_last_path_nc_old  # node_count after last completed path
                            do_we_plot_this_path = True
                    else:
                        do_we_plot_this_path = True
                    if do_we_plot_this_path:
                        self.pathcount += 1
                        # Create (but do not add to SVG) a path to contain the line
                        newpath = etree.Element(inkex.addNS('path', 'svg'))
                        x1 = float(node.get('x1'))
                        y1 = float(node.get('y1'))
                        x2 = float(node.get('x2'))
                        y2 = float(node.get('y2'))
                        s = node.get('style')
                        if s:
                            newpath.set('style', s)
                        t = node.get('transform')
                        if t:
                            newpath.set('transform', t)
                        a = []
                        a.append(['M ', [x1, y1]])
                        a.append([' L ', [x2, y2]])
                        newpath.set('d', simplepath.formatPath(a))
                        self.plot_path(newpath, mat_new)

                elif node.tag == inkex.addNS('polyline', 'svg') or node.tag == 'polyline':

                    """
                    Convert
                     <polyline points="x1,y1 x2,y2 x3,y3 [...]"/> 
                    OR  
                     <polyline points="x1 y1 x2 y2 x3 y3 [...]"/> 
                    to 
                      <path d="Mx1,y1 Lx2,y2 Lx3,y3 [...]"/> 
                    Note: we ignore polylines with no points, or polylines with only a single point.
                    """

                    pl = node.get('points', '').strip()
                    if pl == '':
                        continue

                    # if we're in resume mode AND self.pathcount < self.svg_last_path, then skip over this path.
                    # if we're in resume mode and self.pathcount = self.svg_last_path, then start here, and set
                    # self.node_count equal to self.svg_last_path_nc

                    do_we_plot_this_path = False
                    if self.resume_mode:
                        if self.pathcount < self.svg_last_path_old:  # Fully plotted; skip.
                            self.pathcount += 1
                        elif self.pathcount == self.svg_last_path_old:  # First partially-plotted path
                            self.node_count = self.svg_last_path_nc_old  # node_count after last completed path
                            do_we_plot_this_path = True
                    else:
                        do_we_plot_this_path = True
                    if do_we_plot_this_path:
                        self.pathcount += 1
                        pa = pl.replace(',', ' ').split()  # replace comma with space before splitting
                        if not pa:
                            continue
                        path_length = len(pa)
                        if path_length < 4:  # Minimum of x1,y1 x2,y2 required.
                            continue
                        d = "M " + pa[0] + " " + pa[1]
                        i = 2
                        while i < (path_length - 1):
                            d += " L " + pa[i] + " " + pa[i + 1]
                            i += 2

                        # Create (but do not add to SVG) a path to represent the polyline
                        newpath = etree.Element(inkex.addNS('path', 'svg'))
                        newpath.set('d', d)
                        s = node.get('style')
                        if s:
                            newpath.set('style', s)
                        t = node.get('transform')
                        if t:
                            newpath.set('transform', t)
                        self.plot_path(newpath, mat_new)

                elif node.tag == inkex.addNS('polygon', 'svg') or node.tag == 'polygon':

                    """
                    Convert 
                     <polygon points="x1,y1 x2,y2 x3,y3 [...]"/> 
                    to 
                      <path d="Mx1,y1 Lx2,y2 Lx3,y3 [...] Z"/> 
                    Note: we ignore polygons with no points
                    """

                    pl = node.get('points', '').strip()
                    if pl == '':
                        continue

                    # if we're in resume mode AND self.pathcount < self.svg_last_path, then skip over this path.
                    # if we're in resume mode and self.pathcount = self.svg_last_path, then start here, and set
                    #    self.node_count equal to self.svg_last_path_nc

                    do_we_plot_this_path = False
                    if self.resume_mode:
                        if self.pathcount < self.svg_last_path_old:  # Fully plotted; skip.
                            self.pathcount += 1
                        elif self.pathcount == self.svg_last_path_old:  # First partially-plotted path
                            self.node_count = self.svg_last_path_nc_old  # node_count after last completed path
                            do_we_plot_this_path = True
                    else:
                        do_we_plot_this_path = True
                    if do_we_plot_this_path:
                        self.pathcount += 1
                        pa = pl.split()
                        if not len(pa):
                            continue  # skip the following statements
                        d = "M " + pa[0]
                        for i in xrange(1, len(pa)):
                            d += " L " + pa[i]
                        d += " Z"
                        # Create (but do not add to SVG) a path to represent the polygon
                        newpath = etree.Element(inkex.addNS('path', 'svg'))
                        newpath.set('d', d)
                        s = node.get('style')
                        if s:
                            newpath.set('style', s)
                        t = node.get('transform')
                        if t:
                            newpath.set('transform', t)
                        self.plot_path(newpath, mat_new)

                elif node.tag in [inkex.addNS('ellipse', 'svg'), 'ellipse',
                                  inkex.addNS('circle', 'svg'), 'circle']:

                    # Convert circles and ellipses to a path with two 180 degree arcs.
                    # In general (an ellipse), we convert
                    #   <ellipse rx="RX" ry="RY" cx="X" cy="Y"/>
                    # to
                    #   <path d="MX1,CY A RX,RY 0 1 0 X2,CY A RX,RY 0 1 0 X1,CY"/>
                    # where
                    #   X1 = CX - RX
                    #   X2 = CX + RX
                    # Note: ellipses or circles with a radius attribute of value 0 are ignored

                    if node.tag == inkex.addNS('ellipse', 'svg') or node.tag == 'ellipse':
                        rx = float(node.get('rx', '0'))
                        ry = float(node.get('ry', '0'))
                    else:
                        rx = float(node.get('r', '0'))
                        ry = rx
                    if rx == 0 or ry == 0:
                        continue

                    # if we're in resume mode AND self.pathcount < self.svg_last_path, then skip over this path.
                    # if we're in resume mode and self.pathcount = self.svg_last_path, then start here, and set
                    #    self.node_count equal to self.svg_last_path_nc

                    do_we_plot_this_path = False
                    if self.resume_mode:
                        if self.pathcount < self.svg_last_path_old:
                            # This path was *completely plotted* already; skip.
                            self.pathcount += 1
                        elif self.pathcount == self.svg_last_path_old:
                            # this path is the first *not completely* plotted path:
                            self.node_count = self.svg_last_path_nc_old  # node_count after last completed path
                            do_we_plot_this_path = True
                    else:
                        do_we_plot_this_path = True
                    if do_we_plot_this_path:
                        self.pathcount += 1

                        cx = float(node.get('cx', '0'))
                        cy = float(node.get('cy', '0'))
                        x1 = cx - rx
                        x2 = cx + rx
                        d = 'M {0:f},{1:f} '.format(x1, cy) + \
                            'A {0:f},{1:f} '.format(rx, ry) + \
                            '0 1 0 {0:f},{1:f} '.format(x2, cy) + \
                            'A {0:f},{1:f} '.format(rx, ry) + \
                            '0 1 0 {0:f},{1:f}'.format(x1, cy)
                        # Create (but do not add to SVG) a path to represent the circle or ellipse
                        newpath = etree.Element(inkex.addNS('path', 'svg'))
                        newpath.set('d', d)
                        s = node.get('style')
                        if s:
                            newpath.set('style', s)
                        t = node.get('transform')
                        if t:
                            newpath.set('transform', t)
                        self.plot_path(newpath, mat_new)
                elif node.tag == inkex.addNS('metadata', 'svg') or node.tag == 'metadata':
                    continue
                elif node.tag == inkex.addNS('defs', 'svg') or node.tag == 'defs':
                    continue
                elif node.tag == inkex.addNS('namedview', 'sodipodi') or node.tag == 'namedview':
                    continue
                elif node.tag == inkex.addNS('WCB', 'svg') or node.tag == 'WCB':
                    continue
                elif node.tag == inkex.addNS('MergeData', 'svg') or node.tag == 'MergeData':
                    continue
                elif node.tag == inkex.addNS('eggbot', 'svg') or node.tag == 'eggbot':
                    continue
                elif node.tag == inkex.addNS('title', 'svg') or node.tag == 'title':
                    continue
                elif node.tag == inkex.addNS('desc', 'svg') or node.tag == 'desc':
                    continue

                elif node.tag in [inkex.addNS('text', 'svg'), 'text',
                                  inkex.addNS('flowRoot', 'svg'), 'flowRoot']:
                    if 'text' not in self.warnings and self.plot_current_layer:
                        if self.s_current_layer_name == '':
                            temp_text = '.'
                        else:
                            temp_text = ', found in a \nlayer named: "' + self.s_current_layer_name + '" .'
                        self.text_log(gettext.gettext('Note: This file contains some plain text' + temp_text))
                        self.text_log(gettext.gettext('Please convert your text into paths before drawing,'))
                        self.text_log(gettext.gettext('using Path > Object to Path. '))
                        self.text_log(gettext.gettext('You can also create new text by using Hershey Text,'))
                        self.text_log(gettext.gettext('located in the menu at Extensions > Render.'))
                        self.warnings['text'] = 1
                    continue
                elif node.tag == inkex.addNS('image', 'svg') or node.tag == 'image':
                    if 'image' not in self.warnings and self.plot_current_layer:
                        if self.s_current_layer_name == '':
                            temp_text = ''
                        else:
                            temp_text = ' in layer "' + self.s_current_layer_name + '"'
                        self.text_log(gettext.gettext('Warning:' + temp_text))
                        self.text_log(gettext.gettext('unable to draw bitmap images; '))
                        self.text_log(gettext.gettext('Please convert images to line art before drawing. '))
                        self.text_log(gettext.gettext('Consider using the Path > Trace bitmap tool. '))
                        self.warnings['image'] = 1
                    continue
                elif node.tag == inkex.addNS('pattern', 'svg') or node.tag == 'pattern':
                    continue
                elif node.tag == inkex.addNS('radialGradient', 'svg') or node.tag == 'radialGradient':
                    continue  # Similar to pattern
                elif node.tag == inkex.addNS('linearGradient', 'svg') or node.tag == 'linearGradient':
                    continue  # Similar in pattern
                elif node.tag == inkex.addNS('style', 'svg') or node.tag == 'style':
                    # This is a reference to an external style sheet and not the value
                    # of a style attribute to be inherited by child elements
                    continue
                elif node.tag == inkex.addNS('cursor', 'svg') or node.tag == 'cursor':
                    continue
                elif node.tag == inkex.addNS('font', 'svg') or node.tag == 'font':
                    continue
                elif node.tag == inkex.addNS('color-profile', 'svg') or node.tag == 'color-profile':
                    # Gamma curves, color temp, etc. are not relevant to single color output
                    continue
                elif not isinstance(node.tag, basestring):
                    # This is likely an XML processing instruction such as an XML
                    # comment.  lxml uses a function reference for such node tags
                    # and as such the node tag is likely not a printable string.
                    # Further, converting it to a printable string likely won't
                    # be very useful.
                    continue
                else:
                    if str(node.tag) not in self.warnings and self.plot_current_layer:
                        t = str(node.tag).split('}')
                        if self.s_current_layer_name == "":
                            layer_description = "found in file. "
                        else:
                            layer_description = 'in layer "' + self.s_current_layer_name + '".'

                        self.text_log('Warning: unable to plot <' + str(t[-1]) + '> object')
                        self.text_log(layer_description + 'Please convert it to a path first.')
                        self.warnings[str(node.tag)] = 1
                    continue

    def DoWePlotLayer(self, str_layer_name):
        """
        Parse layer name for layer number and other properties.

        First: scan layer name for first non-numeric character,
        and scan the part before that (if any) into a number
        Then, (if not printing in all-layers mode)
        see if the number matches the layer number that we are printing.

        Secondary function: Parse characters following the layer number (if any) to see if
        there is a "+H" or "+S" escape code, that indicates that overrides the pen-down
        height or speed for the given layer. A "+D" indicates a given time delay.

        Two additional single-character escape codes are:
        "%" (leading character only)-- sets a non-printing "documentation" layer.
        "!" (leading character only)-- force a pause, as though the button were pressed.

        The escape sequences are described at: https://wiki.evilmadscientist.com/AxiDraw_Layer_Control
        """

        # Look at layer name.  Sample first character, then first two, and
        # so on, until the string ends or the string no longer consists of digit characters only.
        temp_num_string = 'x'
        string_pos = 1
        layer_name_int = -1
        layer_match = False
        if sys.version_info < (3,):  # Yes this is ugly. More elegant suggestions welcome. :)
            current_layer_name = str_layer_name.encode('ascii', 'ignore')  # Drop non-ascii characters
        else:
            current_layer_name = str(str_layer_name)
        current_layer_name.lstrip()  # Remove leading whitespace
        self.plot_current_layer = True  # Temporarily assume that we are plotting the layer

        max_length = len(current_layer_name)
        if max_length > 0:
            if current_layer_name[0] == '%':
                self.plot_current_layer = False  # First character is "%" -- skip this layer
            if current_layer_name[0] == '!':
                # First character is "!" -- force a pause

                # if we're in resume mode AND self.pathcount < self.svg_last_path, then skip over this path.
                # if two or more forced pauses occur without any plotting between them, they
                # may be treated as a _single_ pause when resuming.

                do_we_pause_now = False
                if self.resume_mode:
                    if self.pathcount < self.svg_last_path_old:  # Fully plotted; skip.
                        # This pause was *already executed*, and we are resuming past it. Skip.
                        self.pathcount += 1
                else:
                    do_we_pause_now = True
                if do_we_pause_now:
                    self.pathcount += 1  # This action counts as a "path" from the standpoint of pause/resume

                    # Record this as though it were a completed path:
                    self.svg_last_path = self.pathcount  # The number of the last path completed
                    self.svg_last_path_nc = self.node_count  # the node count after the last path was completed.

                    self.force_pause = True
                    self.PauseResumeCheck()  # Carry out the pause, or resume if required.

            while string_pos <= max_length:
                layer_name_fragment = current_layer_name[:string_pos]
                if layer_name_fragment.isdigit():
                    temp_num_string = current_layer_name[:string_pos]  # Store longest numeric string so far
                    string_pos += 1
                else:
                    break

        if self.print_in_layers_mode:  # Also true if resuming a print that was of a single layer.
            if str.isdigit(temp_num_string):
                layer_name_int = int(float(temp_num_string))
                if self.svg_layer == layer_name_int:
                    layer_match = True  # Match! The current layer IS named.

            if not layer_match:
                self.plot_current_layer = False

        if self.plot_current_layer:
            self.layers_found_to_plot = True

            # End of part 1, current layer to see if we print it.
            # Now, check to see if there is additional information coded here.

            old_pen_down = self.layer_pen_pos_down
            old_speed = self.layer_speed_pendown

            # set default values before checking for any overrides:
            self.use_custom_layer_pen_height = False
            self.use_custom_layer_speed = False
            self.layer_pen_pos_down = -1
            self.layer_speed_pendown = -1

            if string_pos > 0:
                string_pos -= 1

            if max_length > string_pos + 2:
                while string_pos <= max_length:
                    key = current_layer_name[string_pos:string_pos + 2].lower()
                    if key == "+h" or key == "+s" or key == "+d":
                        param_start = string_pos + 2
                        string_pos += 3
                        temp_num_string = 'x'
                        if max_length > 0:
                            while string_pos <= max_length:
                                if str.isdigit(current_layer_name[param_start:string_pos]):
                                    temp_num_string = current_layer_name[param_start:string_pos]  # Longest numeric string so far
                                    string_pos += 1
                                else:
                                    break
                        if str.isdigit(temp_num_string):
                            parameter_int = int(float(temp_num_string))

                            if key == "+d":
                                if parameter_int > 0:
                                    # Delay requested before plotting this layer. Delay times are in milliseconds.
                                    time_remaining = float(parameter_int) / 1000.0  # Convert to seconds

                                    while time_remaining > 0:
                                        if time_remaining < 0.15:
                                            time.sleep(time_remaining)  # Less than 150 ms remaining to be paused. Do it all at once.
                                            time_remaining = 0
                                            self.PauseResumeCheck()  # Check if pause button was pressed while we were sleeping
                                        else:
                                            time.sleep(0.1)  # Use short 100 ms intervals to improve pausing responsiveness
                                            time_remaining -= 0.1
                                            self.PauseResumeCheck()  # Check if pause button was pressed while we were sleeping

                            if key == "+h":
                                if 0 <= parameter_int <= 100:
                                    self.use_custom_layer_pen_height = True
                                    self.layer_pen_pos_down = parameter_int

                            if key == "+s":
                                if 0 < parameter_int <= 110:
                                    self.use_custom_layer_speed = True
                                    self.layer_speed_pendown = parameter_int

                        string_pos = param_start + len(temp_num_string)
                    else:
                        break  # exit loop.

            if self.layer_speed_pendown != old_speed:
                self.EnableMotors()  # Set speed value variables for this layer.
            if self.layer_pen_pos_down != old_pen_down:
                self.ServoSetup()  # Set pen down height for this layer.
                # This new value will be used when we next lower the pen. (It's up between layers.)

    def plot_path(self, path, mat_transform):
        """
        Plot the path while applying the transformation defined by the matrix [mat_transform].
        - Turn this path into a cubicsuperpath (list of beziers).
        - Further subdivide the cubic path into a list of straight segments within tolerance
        - Identify "even and odd" parts of the path, to decide when the pen is up and down.
        """

        d = path.get('d')

        if self.spew_debugdata:
            self.text_log('plot_path()\n')
            self.text_log('path d: ' + d)
            if len(simplepath.parsePath(d)) == 0:
                self.text_log('path length is zero, will not be plotting this path.')

        if len(d) > 3000:  # Raise pen when computing extremely long paths.
            if not self.pen_up:  # skip if pen is already up
                self.pen_raise()

        if len(simplepath.parsePath(d)) == 0:
            return

        if self.plot_current_layer:
            tolerance = axidraw_conf.BoundsTolerance  
            # Allow negligible violation of boundaries without throwing an error.

            x_max = self.x_bounds_max + tolerance
            x_min = self.x_bounds_min - tolerance
            y_max = self.y_bounds_max + tolerance
            y_min = self.y_bounds_min - tolerance

            # Page clip warnings: Need to warn if physical X_max is less than
            # page-clip X_Max AND a path is clipped on X.

            x_pmax = 3.0E8
            y_pmax = 3.0E8
            if self.rotate_page:
                if self.x_max_phy < self.svg_height:
                    x_pmax = self.y_max_phy + tolerance
                if self.y_max_phy < self.svg_width:
                    y_pmax = self.x_max_phy + tolerance
            else:
                if self.x_max_phy < self.svg_width:
                    x_pmax = self.x_max_phy + tolerance
                if self.y_max_phy < self.svg_height:
                    y_pmax = self.y_max_phy + tolerance

            p = cubicsuperpath.parsePath(d)

            # Apply the transformation to each point
            applyTransformToPath(mat_transform, p)

            # p is now a list of lists of cubic beziers [control pt1, control pt2, endpoint]
            # where the start-point is the last point in the previous segment.
            for sp in p: # for subpaths in the path:

                # Divide each path into a set of straight segments:
                plot_utils.subdivideCubicPath(sp, 0.02 / axidraw_conf.smoothness)

                """
                Pre-parse the subdivided paths:
                    - Clip path segments to the bounds; split into additional subpaths if necessary.
                    - Apply auto-rotation
                    - Pick out vertex location information (only) from the cubic bezier curve data
                """
                
                subpath_list = []
                a_path = []
                prev_in_bounds = False # Don't assume that prior point was in bounds
                first_point = True
                prev_vertex = []
                
                for vertex in sp: # For each vertex in our subdivided path
                    if self.rotate_page:
                        t_x = float(vertex[1][1])  # Flipped X/Y
                        t_y = self.svg_width - float(vertex[1][0])
                    else:
                        t_x = float(vertex[1][0])  
                        t_y = float(vertex[1][1])
                    this_vertex = [t_x,t_y]

                    in_bounds = True

                    if not self.ignore_limits:
                        if t_x > x_max or t_x < x_min or t_y > y_max or t_y < y_min:
                            in_bounds = False
                            if axidraw_conf.clip_to_page:
                                if t_x > x_pmax or t_y > y_pmax:
                                    self.warn_out_of_bounds = True
                            else:
                                self.warn_out_of_bounds = True

                    """
                    Possible cases, for first vertex:
                    (1) In bounds: Add the vertex to the path.
                    (2) Not in bounds: Do not add the vertex. 
                    
                    Possible cases, for subsequent vertices:
                    (1) In bounds, as was previous: Add the vertex.
                      -> No segment between two in-bound points is clipped.
                    (2) In bounds, prev was not: Clip & start new path.
                    (3) OOB, prev was in bounds: Clip & end the path.
                    (4) OOB, as was previous: Segment _may_ clip corner.
                      -> Either add no points or start & end new path
                    """

                    if first_point:
                        if in_bounds:
                            a_path.append([t_x, t_y])
                    else:
                        if in_bounds and prev_in_bounds:
                            a_path.append([t_x, t_y])
                        else:
                            segment =  [prev_vertex,this_vertex] 
                            accept, seg = plot_utils.clip_segment(segment, self.bounds)
                            if in_bounds and not prev_in_bounds:
                                if len(a_path) > 0:
                                    subpath_list.append(a_path)
                                    a_path = [] # start new subpath
                                a_path.append([seg[0][0], seg[0][1]])
                                t_x = seg[1][0]
                                t_y = seg[1][1]
                                a_path.append([t_x, t_y])
                            if prev_in_bounds and not in_bounds:
                                t_x = seg[1][0]
                                t_y = seg[1][1]
                                a_path.append([t_x, t_y])
                                subpath_list.append(a_path) # Save subpath
                                a_path = [] # Start new subpath
                            if (not prev_in_bounds) and not in_bounds:
                                if accept:
                                    if len(a_path) > 0:
                                        subpath_list.append(a_path)
                                        a_path = [] # start new subpath
                                    a_path.append([seg[0][0], seg[0][1]])
                                    t_x = seg[1][0]
                                    t_y = seg[1][1]
                                    a_path.append([t_x, t_y])
                                    subpath_list.append(a_path) # Save subpath
                                    a_path = [] # Start new subpath
                    first_point = False
                    prev_vertex = this_vertex
                    prev_in_bounds = in_bounds
                    
                if len(a_path) > 0:
                    subpath_list.append(a_path)

                if not subpath_list: # Do not attempt to plot empty segments
                    continue

                for subpath in subpath_list:
                    n_index = 0
                    single_path = []
                    for vertex in subpath:
                        if self.b_stopped:
                            return
                        f_x = vertex[0]
                        f_y = vertex[1]
                        
                        if n_index == 0:
                            # "Pen-up" move to new path start location. Skip pen-lift if the path is shorter than MinGap.
                            if plot_utils.distance(f_x - self.f_curr_x, f_y - self.f_curr_y) > axidraw_conf.MinGap:
                                self.pen_raise()
                                self.plotSegmentWithVelocity(f_x, f_y, 0, 0) # Pen up straight move, zero velocity at endpoints
                            else:
                                self.plotSegmentWithVelocity(f_x, f_y, 0, 0) # Short pen down move, in place of pen-up move.
                            # self.node_count += 1    # Alternative: Increment node counter, at a slight accuracy cost.
                        elif n_index == 1:
                            self.pen_lower()
                        n_index += 1
                        single_path.append([f_x, f_y])    
                    self.plan_trajectory(single_path)

            if not self.b_stopped:  # an "index" for resuming plots quickly-- record last complete path
                self.svg_last_path = self.pathcount  # The number of the last path completed
                self.svg_last_path_nc = self.node_count  # the node count after the last path was completed.

    def plan_trajectory(self, input_path):
        """
        Plan the trajectory for a full path, accounting for linear acceleration.
        Inputs: Ordered (x,y) pairs to cover.
        Output: A list of segments to plot, of the form (Xfinal, Yfinal, v_initial, v_final)
        [Aside: We may eventually migrate to the form (Xfinal, Yfinal, Vix, Viy, Vfx,Vfy)]

        Important note: This routine uses *inch* units (inches of distance, velocities of inches/second, etc.),
        and works in the basis of the XY axes, not the native axes of the motors.
        """

        spew_trajectory_debug_data = self.spew_debugdata  # Suggested values: False or self.spew_debugdata

        if spew_trajectory_debug_data:
            self.text_log('\nplan_trajectory()\n')

        if self.b_stopped:
            return
        if self.f_curr_x is None:
            return

        # Handle simple segments (lines) that do not require any complex planning:
        if len(input_path) < 3:
            if spew_trajectory_debug_data:
                self.text_log('Drawing straight line, not a curve.')  # "SHORTPATH ESCAPE"
                self.text_log('plotSegmentWithVelocity({}, {}, {}, {})'.format(
                    input_path[1][0], input_path[1][1], 0, 0))
            # Get X & Y Destination coordinates from last element, input_path[1]:
            self.plotSegmentWithVelocity(input_path[1][0], input_path[1][1], 0, 0)
            return

        # For other trajectories, we need to go deeper.
        traj_length = len(input_path)

        if spew_trajectory_debug_data:
            self.text_log('Input path to plan_trajectory: ')
            for xy in input_path:
                self.text_log('x: {0:1.3f},  y: {1:1.3f}'.format(xy[0], xy[1]))
            self.text_log('\ntraj_length: ' + str(traj_length))

        speed_limit = self.speed_pendown  # speed_limit is maximum travel rate (in/s), in XY plane.
        if self.pen_up:
            speed_limit = self.speed_penup  # Unlikely case, but handle it anyway...

        if spew_trajectory_debug_data:
            self.text_log('\nspeed_limit (plan_trajectory) ' + str(speed_limit) + ' inches per second')

        traj_dists = array('f')  # float, Segment length (distance) when arriving at the junction
        traj_vels = array('f')  # float, Velocity (_speed_, really) when arriving at the junction

        traj_vectors = []  # Array that will hold normalized unit vectors along each segment
        trimmed_path = []  # Array that will hold usable segments of input_path

        traj_dists.append(0.0)  # First value, at time t = 0
        traj_vels.append(0.0)  # First value, at time t = 0

        if self.options.resolution == 1:  # High-resolution mode
            min_dist = axidraw_conf.MaxStepDist_HR  # Skip segments likely to be shorter than one step
        else:
            min_dist = axidraw_conf.MaxStepDist_LR  # Skip segments likely to be shorter than one step

        last_index = 0
        for i in xrange(1, traj_length):
            # Construct basic arrays of position and distances, skipping zero length (and nearly zero length) segments.

            # Distance per segment:
            tmp_dist_x = input_path[i][0] - input_path[last_index][0]
            tmp_dist_y = input_path[i][1] - input_path[last_index][1]

            tmp_dist = plot_utils.distance(tmp_dist_x, tmp_dist_y)

            if tmp_dist >= min_dist:
                traj_dists.append(tmp_dist)

                traj_vectors.append([tmp_dist_x / tmp_dist, tmp_dist_y / tmp_dist])  # Normalized unit vectors for computing cosine factor

                tmp_x = input_path[i][0]
                tmp_y = input_path[i][1]
                trimmed_path.append([tmp_x, tmp_y])  # Selected, usable portions of input_path.

                if spew_trajectory_debug_data:
                    self.text_log('\nSegment: input_path[{0:1.0f}] -> input_path[{1:1.0f}]'.format(last_index, i))
                    self.text_log('Destination: x: {0:1.3f},  y: {1:1.3f}. Move distance: {2:1.3f}'.format(tmp_x, tmp_y, tmp_dist))

                last_index = i
            elif spew_trajectory_debug_data:
                self.text_log('\nSegment: input_path[{0:1.0f}] -> input_path[{1:1.0f}] is zero (or near zero); skipping!'.format(last_index, i))
                self.text_log('  x: {0:1.3f},  y: {1:1.3f}, distance: {2:1.3f}'.format(input_path[i][0], input_path[i][1], tmp_dist))

        traj_length = len(traj_dists)

        # Handle zero-segment plot:
        if traj_length < 2:
            if spew_trajectory_debug_data:
                self.text_log('\nSkipped a path element that did not have any well-defined segments.')
            return

        # Handle simple segments (lines) that do not require any complex planning (after removing zero-length elements):
        if traj_length < 3:
            if spew_trajectory_debug_data:
                self.text_log('\nDrawing straight line, not a curve.')
            self.plotSegmentWithVelocity(trimmed_path[0][0], trimmed_path[0][1], 0, 0)
            return

        if spew_trajectory_debug_data:
            self.text_log('\nAfter removing any zero-length segments, we are left with: ')
            self.text_log('traj_dists[0]: {0:1.3f}'.format(traj_dists[0]))
            for i in xrange(0, len(trimmed_path)):
                self.text_log('i: {0:1.0f}, x: {1:1.3f}, y: {2:1.3f}, distance: {3:1.3f}'.format(i,
                    trimmed_path[i][0], trimmed_path[i][1], traj_dists[i + 1]))
                self.text_log('  And... traj_dists[i+1]: {0:1.3f}'.format(traj_dists[i + 1]))

        # Acceleration/deceleration rates:
        if self.pen_up:
            accel_rate = axidraw_conf.AccelRatePU * self.options.accel / 100.0
        else:
            accel_rate = axidraw_conf.AccelRate * self.options.accel / 100.0

        # Maximum acceleration time: Time needed to accelerate from full stop to maximum speed:
        # v = a * t, so t_max = vMax / a
        t_max = speed_limit / accel_rate

        # Distance that is required to reach full speed, from zero speed:  x = 1/2 a t^2
        accel_dist = 0.5 * accel_rate * t_max * t_max

        if spew_trajectory_debug_data:
            self.text_log('\nspeed_limit: {0:1.3f}'.format(speed_limit))
            self.text_log('t_max: {0:1.3f}'.format(t_max))
            self.text_log('accel_rate: {0:1.3f}'.format(accel_rate))
            self.text_log('accel_dist: {0:1.3f}'.format(accel_dist))
            cosine_print_array = array('f')

        """
        Now, step through every vertex in the trajectory, and calculate what the speed
        should be when arriving at that vertex.
        
        In order to do so, we need to understand how the trajectory will evolve in terms 
        of position and velocity for a certain amount of time in the future, past that vertex. 
        The most extreme cases of this is when we are traveling at 
        full speed initially, and must come to a complete stop.
            (This is actually more sudden than if we must reverse course-- that must also
            go through zero velocity at the same rate of deceleration, and a full reversal
            that does not occur at the path end might be able to have a 
            nonzero velocity at the endpoint.)
            
        Thus, we look ahead from each vertex until one of the following occurs:
            (1) We have looked ahead by at least t_max, or
            (2) We reach the end of the path.

        The data that we have to start out with is this:
            - The position and velocity at the previous vertex
            - The position at the current vertex
            - The position at subsequent vertices
            - The velocity at the final vertex (zero)

        To determine the correct velocity at each vertex, we will apply the following rules:
        
        (A) For the first point, V(i = 0) = 0.

        (B) For the last point point, V = 0 as well.
        
        (C) If the length of the segment is greater than the distance 
        required to reach full speed, then the vertex velocity may be as 
        high as the maximum speed.
        
        Note that we must actually check not the total *speed* but the acceleration
        along the two native motor axes.
        
        (D) If not; if the length of the segment is less than the total distance
        required to get to full speed, then the velocity at that vertex
        is limited by to the value that can be reached from the initial
        starting velocity, in the distance given.
                
        (E) The maximum velocity through the junction is also limited by the
        turn itself-- if continuing straight, then we do not need to slow down
        as much as if we were fully reversing course. 
        We will model each corner as a short curve that we can accelerate around.
        
        (F) To calculate the velocity through each turn, we must _look ahead_ to
        the subsequent (i+1) vertex, and determine what velocity 
        is appropriate when we arrive at the next point. 
        
        Because future points may be close together-- the subsequent vertex could
        occur just before the path end -- we actually must look ahead past the 
        subsequent (i + 1) vertex, all the way up to the limits that we have described 
        (e.g., t_max) to understand the subsequent behavior. Once we have that effective
        endpoint, we can work backwards, ensuring that we will be able to get to the
        final speed/position that we require. 
        
        A less complete (but far simpler) procedure is to first complete the trajectory
        description, and then -- only once the trajectory is complete -- go back through,
        but backwards, and ensure that we can actually decelerate to each velocity.

        (G) The minimum velocity through a junction may be set to a constant.
        There is often some (very slow) speed -- perhaps a few percent of the maximum speed
        at which there are little or no resonances. Even when the path must directly reverse
        itself, we can usually travel at a non-zero speed. This, of course, presumes that we 
        still have a solution for getting to the endpoint at zero speed.
        """

        delta = axidraw_conf.cornering / 5000  # Corner rounding/tolerance factor-- not sure how high this should be set.

        for i in xrange(1, traj_length - 1):
            dcurrent = traj_dists[i]  # Length of the segment leading up to this vertex

            v_prev_exit = traj_vels[i - 1]  # Velocity when leaving previous vertex

            """
            Velocity at vertex: Part I
            
            Check to see what our plausible maximum speeds are, from 
            acceleration only, without concern about cornering, nor deceleration.
            """

            if dcurrent > accel_dist:
                # There _is_ enough distance in the segment for us to either
                # accelerate to maximum speed or come to a full stop before this vertex.
                vcurrent_max = speed_limit
                if spew_trajectory_debug_data:
                    self.text_log('Speed Limit on vel : ' + str(i))
            else:
                # There is _not necessarily_ enough distance in the segment for us to either
                # accelerate to maximum speed or come to a full stop before this vertex.
                # Calculate how much we *can* swing the velocity by:

                vcurrent_max = plot_utils.vFinal_Vi_A_Dx(v_prev_exit, accel_rate, dcurrent)
                if vcurrent_max > speed_limit:
                    vcurrent_max = speed_limit

                if spew_trajectory_debug_data:
                    self.text_log('traj_vels I: {0:1.3f}'.format(vcurrent_max))

            """
            Velocity at vertex: Part II 
            
            Assuming that we have the same velocity when we enter and
            leave a corner, our acceleration limit provides a velocity
            that depends upon the angle between input and output directions.
            
            The cornering algorithm models the corner as a slightly smoothed corner,
            to estimate the angular acceleration that we encounter:
            https://onehossshay.wordpress.com/2011/09/24/improving_grbl_cornering_algorithm/
            
            The dot product of the unit vectors is equal to the cosine of the angle between the
            two unit vectors, giving the deflection between the incoming and outgoing angles. 
            Note that this angle is (pi - theta), in the convention of that article, giving us
            a sign inversion. [cos(pi - theta) = - cos(theta)]
            """
            cosine_factor = - plot_utils.dotProductXY(traj_vectors[i - 1], traj_vectors[i])

            root_factor = math.sqrt((1 - cosine_factor) / 2)
            denominator = 1 - root_factor
            if denominator > 0.0001:
                rfactor = (delta * root_factor) / denominator
            else:
                rfactor = 100000
            vjunction_max = math.sqrt(accel_rate * rfactor)

            if vcurrent_max > vjunction_max:
                vcurrent_max = vjunction_max

            traj_vels.append(vcurrent_max)  # "Forward-going" speed limit for velocity at this particular vertex.
        traj_vels.append(0.0)  # Add zero velocity, for final vertex.

        if spew_trajectory_debug_data:
            self.text_log(' ')
            for dist in cosine_print_array:
                self.text_log('Cosine Factor: {0:1.3f}'.format(dist))
            self.text_log(' ')

            for dist in traj_vels:
                self.text_log('traj_vels II: {0:1.3f}'.format(dist))
            self.text_log(' ')

        """            
        Velocity at vertex: Part III

        We have, thus far, ensured that we could reach the desired velocities, going forward, but
        have also assumed an effectively infinite deceleration rate.        

        We now go through the completed array in reverse, limiting velocities to ensure that we 
        can properly decelerate in the given distances.        
        """

        for j in xrange(1, traj_length):
            i = traj_length - j  # Range: From (traj_length - 1) down to 1.

            v_final = traj_vels[i]
            v_initial = traj_vels[i - 1]
            seg_length = traj_dists[i]

            if v_initial > v_final and seg_length > 0:
                v_init_max = plot_utils.vInitial_VF_A_Dx(v_final, -accel_rate, seg_length)

                if spew_trajectory_debug_data:
                    self.text_log('VInit Calc: (v_final = {0:1.3f}, accel_rate = {1:1.3f}, seg_length = {2:1.3f}) '
                                   .format(v_final, accel_rate, seg_length))

                if v_init_max < v_initial:
                    v_initial = v_init_max
                traj_vels[i - 1] = v_initial

        if spew_trajectory_debug_data:
            for dist in traj_vels:
                self.text_log('traj_vels III: {0:1.3f}'.format(dist))
            self.text_log(' ')

        #         if spew_trajectory_debug_data:
        #             self.text_log( 'List results for this input path:')
        #             for i in xrange(0, traj_length-1):
        #                 self.text_log( 'i: %1.0f' %(i))
        #                 self.text_log( 'x: %1.3f,  y: %1.3f' %(trimmed_path[i][0],trimmed_path[i][1]))
        #                 self.text_log( 'distance: %1.3f' %(traj_dists[i+1]))
        #                 self.text_log( 'traj_vels[i]: %1.3f' %(traj_vels[i]))
        #                 self.text_log( 'traj_vels[i+1]: %1.3f\n' %(traj_vels[i+1]))

        for i in xrange(0, traj_length - 1):
            self.plotSegmentWithVelocity(trimmed_path[i][0], trimmed_path[i][1], traj_vels[i], traj_vels[i + 1])

    def plotSegmentWithVelocity(self, x_dest, y_dest, v_i, v_f):
        """
        Control the serial port to command the machine to draw
        a straight line segment, with basic acceleration support.

        Inputs:     Destination (x,y)
                    Initial velocity
                    Final velocity

        Method: Divide the segment up into smaller segments, each
        of which has constant velocity.
        Send commands out the com port as a set of short line segments
        (dx, dy) with specified durations (in ms) of how long each segment
        takes to draw.the segments take to draw.
        Uses linear ("trapezoid") acceleration and deceleration strategy.

        Inputs are expected be in units of inches (for distance)
            or inches per second (for velocity).

        Input: A list of segments to plot, of the form (Xfinal, Yfinal, Vinitial, Vfinal)

        Input parameters are in distances of inches and velocities of inches per second.

        Within this routine, we convert from inches into motor steps.

        Note: Native motor axes are Motor 1, Motor 2:
            motor_dist1 = ( xDist + yDist ) # Distance for motor to move, Axis 1
            motor_dist2 = ( xDist - yDist ) # Distance for motor to move, Axis 2

        We will only discuss motor steps, and resolution, within the context of native axes.

        """

        self.PauseResumeCheck()

        spew_segment_debug_data = self.spew_debugdata
        #         spew_segment_debug_data = True

        if spew_segment_debug_data:
            self.text_log('plotSegmentWithVelocity({0}, {1}, {2}, {3})'.format(x_dest, y_dest, v_i, v_f))
            if self.resume_mode or self.b_stopped:
                spew_text = '\nSkipping '
            else:
                spew_text = '\nExecuting '
            spew_text += 'plotSegmentWithVelocity() function\n'
            if self.pen_up:
                spew_text += '  Pen-up transit'
            else:
                spew_text += '  Pen-down move'
            spew_text += ' from (x = {0:1.3f}, y = {1:1.3f})'.format(self.f_curr_x, self.f_curr_y)
            spew_text += ' to (x = {0:1.3f}, y = {1:1.3f})\n'.format(x_dest, y_dest)
            spew_text += '    w/ v_i = {0:1.2f}, v_f = {1:1.2f} '.format(v_i, v_f)
            self.text_log(spew_text)
            if self.resume_mode:
                self.text_log(' -> NOTE: ResumeMode is active')
            if self.b_stopped:
                self.text_log(' -> NOTE: Stopped by button press.')

        constant_vel_mode = False
        if self.options.const_speed and not self.pen_up:
            constant_vel_mode = True

        if self.b_stopped:
            self.copies_to_plot = 0
            return
        if self.f_curr_x is None:
            return

        if not self.ignore_limits:  # check page size limits:
            tolerance = axidraw_conf.BoundsTolerance  # Truncate up to 1 step at boundaries without throwing an error.
            x_dest, x_bounded = plot_utils.checkLimitsTol(x_dest, self.x_bounds_min, self.x_bounds_max, tolerance)
            y_dest, y_bounded = plot_utils.checkLimitsTol(y_dest, self.y_bounds_min, self.y_bounds_max, tolerance)
            if x_bounded or y_bounded:
                self.warn_out_of_bounds = True

        delta_x_inches = x_dest - self.f_curr_x
        delta_y_inches = y_dest - self.f_curr_y

        # Velocity inputs; clarify units.
        vi_inches_per_sec = v_i
        vf_inches_per_sec = v_f

        # Look at distance to move along 45-degree axes, for native motor steps:
        # Recall that StepScaleFactor gives a scaling factor for converting from inches to steps. It is *not* the native resolution
        # self.StepScaleFactor is Either 1016 or 2032, for 8X or 16X microstepping, respectively.

        motor_dist1 = delta_x_inches + delta_y_inches  # Distance in inches that the motor+belt must turn through at Motor 1
        motor_dist2 = delta_x_inches - delta_y_inches  # Distance in inches that the motor+belt must turn through at Motor 2

        motor_steps1 = int(round(self.StepScaleFactor * motor_dist1))  # Round the requested motion to the nearest motor step.
        motor_steps2 = int(round(self.StepScaleFactor * motor_dist2))  # Round the requested motion to the nearest motor step.

        # Since we are rounding, we need to keep track of the actual distance moved,
        # not just the _requested_ distance to move.

        motor_dist1_rounded = float(motor_steps1) / (2.0 * self.StepScaleFactor)
        motor_dist2_rounded = float(motor_steps2) / (2.0 * self.StepScaleFactor)

        # Convert back to find the actual X & Y distances that will be moved:
        delta_x_inches_rounded = (motor_dist1_rounded + motor_dist2_rounded)
        delta_y_inches_rounded = (motor_dist1_rounded - motor_dist2_rounded)

        if abs(motor_steps1) < 1 and abs(motor_steps2) < 1:  # If total movement is less than one step, skip this movement.
            return

        segment_length_inches = plot_utils.distance(delta_x_inches_rounded, delta_y_inches_rounded)

        if spew_segment_debug_data:
            self.text_log('\ndelta_x_inches Requested: ' + str(delta_x_inches))
            self.text_log('delta_y_inches Requested: ' + str(delta_y_inches))
            self.text_log('motor_steps1: ' + str(motor_steps1))
            self.text_log('motor_steps2: ' + str(motor_steps2))
            self.text_log('\ndelta_x_inches to be moved: ' + str(delta_x_inches_rounded))
            self.text_log('delta_y_inches to be moved: ' + str(delta_y_inches_rounded))
            self.text_log('segment_length_inches: ' + str(segment_length_inches))
            if not self.pen_up:
                self.text_log('\nBefore speedlimit check::')
                self.text_log('vi_inches_per_sec: {0}'.format(vi_inches_per_sec))
                self.text_log('vf_inches_per_sec: {0}\n'.format(vf_inches_per_sec))

        if self.options.report_time:  # Also keep track of distance:
            if self.pen_up:
                self.pen_up_travel_inches = self.pen_up_travel_inches + segment_length_inches
            else:
                self.pen_down_travel_inches = self.pen_down_travel_inches + segment_length_inches

        # Maximum travel speeds:
        # & acceleration/deceleration rate: (Maximum speed) / (time to reach that speed)

        if self.pen_up:
            speed_limit = self.speed_penup
        else:
            speed_limit = self.speed_pendown

        # Acceleration/deceleration rates:
        if self.pen_up:
            accel_rate = axidraw_conf.AccelRatePU * self.options.accel / 100.0
        else:
            accel_rate = axidraw_conf.AccelRate * self.options.accel / 100.0

        # Maximum acceleration time: Time needed to accelerate from full stop to maximum speed:  v = a * t, so t_max = vMax / a
        t_max = speed_limit / accel_rate

        # Distance that is required to reach full speed, from zero speed:  x = 1/2 a t^2
        accel_dist = 0.5 * accel_rate * t_max * t_max

        if vi_inches_per_sec > speed_limit:
            vi_inches_per_sec = speed_limit
        if vf_inches_per_sec > speed_limit:
            vf_inches_per_sec = speed_limit

        if spew_segment_debug_data:
            self.text_log('\nspeed_limit (PlotSegment) ' + str(speed_limit))
            self.text_log('After speedlimit check::')
            self.text_log('vi_inches_per_sec: {0}'.format(vi_inches_per_sec))
            self.text_log('vf_inches_per_sec: {0}\n'.format(vf_inches_per_sec))

        # Times to reach maximum speed, from our initial velocity
        # vMax = vi + a*t  =>  t = (vMax - vi)/a
        # vf = vMax - a*t   =>  t = -(vf - vMax)/a = (vMax - vf)/a
        # -- These are _maximum_ values. We often do not have enough time/space to reach full speed.

        t_accel_max = (speed_limit - vi_inches_per_sec) / accel_rate
        t_decel_max = (speed_limit - vf_inches_per_sec) / accel_rate

        if spew_segment_debug_data:
            self.text_log('\naccel_rate: {0:.3}'.format(accel_rate))
            self.text_log('speed_limit: {0:.3}'.format(speed_limit))
            self.text_log('vi_inches_per_sec: {0}'.format(vi_inches_per_sec))
            self.text_log('vf_inches_per_sec: {0}'.format(vf_inches_per_sec))
            self.text_log('t_accel_max: {0:.3}'.format(t_accel_max))
            self.text_log('t_decel_max: {0:.3}'.format(t_decel_max))

        # Distance that is required to reach full speed, from our start at speed vi_inches_per_sec:
        # distance = vi * t + (1/2) a t^2
        accel_dist_max = (vi_inches_per_sec * t_accel_max) + (0.5 * accel_rate * t_accel_max * t_accel_max)
        # Use the same model for deceleration distance; modeling it with backwards motion:
        decel_dist_max = (vf_inches_per_sec * t_decel_max) + (0.5 * accel_rate * t_decel_max * t_decel_max)

        # time slices: Slice travel into intervals that are (say) 30 ms long.
        time_slice = axidraw_conf.TimeSlice  # Default slice intervals

        # Declare arrays:
        # These are _normally_ 4-byte integers, but could (theoretically) be 2-byte integers on some systems.
        #   if so, this could cause errors in rare cases (very large/long moves, etc.).
        # Set up an alert system, just in case!

        duration_array = array('I')  # unsigned integer for duration -- up to 65 seconds for a move if only 2 bytes.
        dist_array = array('f')  # float
        dest_array1 = array('i')  # signed integer
        dest_array2 = array('i')  # signed integer

        time_elapsed = 0.0
        position = 0.0
        velocity = vi_inches_per_sec

        """
        
        Next, we wish to estimate total time duration of this segment. 
        In doing so, we must consider the possible cases:

        Case 1: 'Trapezoid'
            Segment length is long enough to reach full speed.
            Segment length > accel_dist_max + decel_dist_max
            We will get to full speed, with an opportunity to "coast" at full speed
            in the middle.
            
        Case 2: 'Triangle'
            Segment length is not long enough to reach full speed.
            Accelerate from initial velocity to a local maximum speed,
            then decelerate from that point to the final velocity.

        Case 3: 'Linear velocity ramp'
            For small enough moves -- say less than 10 intervals (typ 500 ms),
            we do not have significant time to ramp the speed up and down.
            Instead, perform only a simple speed ramp between initial and final.

        Case 4: 'Constant velocity'
            Use a single, constant velocity for all pen-down movements.
            Also a fallback position, when moves are too short for linear ramps.
            
        In each case, we ultimately construct the trajectory in segments at constant velocity.
        In cases 1-3, that set of segments approximates a linear slope in velocity. 
        
        Because we may end up with slight over/undershoot in position along the paths
        with this approach, we perform a final scaling operation (to the correct distance) at the end.
        
        """

        if not constant_vel_mode or self.pen_up:  # Allow accel when pen is up.
            if segment_length_inches > (accel_dist_max + decel_dist_max + time_slice * speed_limit):
                """ 
                Case 1: 'Trapezoid'
                """

                if spew_segment_debug_data:
                    self.text_log('Type 1: Trapezoid' + '\n')
                speed_max = speed_limit  # We will reach _full cruising speed_!

                intervals = int(math.floor(t_accel_max / time_slice))  # Number of intervals during acceleration

                # If intervals == 0, then we are already at (or nearly at) full speed.
                if intervals > 0:
                    time_per_interval = t_accel_max / intervals

                    velocity_step_size = (speed_max - vi_inches_per_sec) / (intervals + 1.0)
                    # For six time intervals of acceleration, first interval is at velocity (max/7)
                    # 6th (last) time interval is at 6*max/7
                    # after this interval, we are at full speed.

                    for index in xrange(0, intervals):  # Calculate acceleration phase
                        velocity += velocity_step_size
                        time_elapsed += time_per_interval
                        position += velocity * time_per_interval
                        duration_array.append(int(round(time_elapsed * 1000.0)))
                        dist_array.append(position)  # Estimated distance along direction of travel
                    if spew_segment_debug_data:
                        self.text_log('Accel intervals: ' + str(intervals))

                # Add a center "coasting" speed interval IF there is time for it.
                coasting_distance = segment_length_inches - (accel_dist_max + decel_dist_max)

                if coasting_distance > (time_slice * speed_max):
                    # There is enough time for (at least) one interval at full cruising speed.
                    velocity = speed_max
                    cruising_time = coasting_distance / velocity
                    time_elapsed += cruising_time
                    duration_array.append(int(round(time_elapsed * 1000.0)))
                    position += velocity * cruising_time
                    dist_array.append(position)  # Estimated distance along direction of travel
                    if spew_segment_debug_data:
                        self.text_log('Coast Distance: ' + str(coasting_distance))
                        self.text_log('Coast velocity: ' + str(velocity))

                intervals = int(math.floor(t_decel_max / time_slice))  # Number of intervals during deceleration

                if intervals > 0:
                    time_per_interval = t_decel_max / intervals
                    velocity_step_size = (speed_max - vf_inches_per_sec) / (intervals + 1.0)

                    for index in xrange(0, intervals):  # Calculate deceleration phase
                        velocity -= velocity_step_size
                        time_elapsed += time_per_interval
                        position += velocity * time_per_interval
                        duration_array.append(int(round(time_elapsed * 1000.0)))
                        dist_array.append(position)  # Estimated distance along direction of travel
                    if spew_segment_debug_data:
                        self.text_log('Decel intervals: ' + str(intervals))

            else:
                """ 
                Case 2: 'Triangle' 
                
                We will _not_ reach full cruising speed, but let's go as fast as we can!
                
                We begin with given: initial velocity, final velocity,
                    maximum acceleration rate, distance to travel.
                
                The optimal solution is to accelerate at the maximum rate, to some maximum velocity Vmax,
                and then to decelerate at same maximum rate, to the final velocity. 
                This forms a triangle on the plot of V(t). 
                
                The value of Vmax -- and the time at which we reach it -- may be varied in order to
                accommodate our choice of distance-traveled and velocity requirements.
                (This does assume that the segment requested is self consistent, and planned 
                with respect to our acceleration requirements.)
                
                In a more detail, with short notation Vi = vi_inches_per_sec, Vf = vf_inches_per_sec, 
                    Amax = accel_rate_local, Dv = (Vf - Vi)
                
                (i) We accelerate from Vi, at Amax to some maximum velocity Vmax.
                This takes place during an interval of time Ta. 
                
                (ii) We then decelerate from Vmax, to Vf, at the same maximum rate, Amax.
                This takes place during an interval of time Td.
                
                (iii) The total time elapsed is Ta + Td
                
                (iv) v = v0 + a * t
                    =>    Vmax = Vi + Amax * Ta
                    and   Vmax = Vf + Amax * Td  (i.e., Vmax - Amax * Td = Vf)
                
                    Thus Td = Ta - (Vf - Vi) / Amax, or Td = Ta - (Dv / Amax)
                    
                (v) The distance covered during the acceleration interval Ta is given by:
                    Xa = Vi * Ta + (1/2) Amax * Ta^2
                    
                    The distance covered during the deceleration interval Td is given by:
                    Xd = Vf * Td + (1/2) Amax * Td^2
                    
                    Thus, the total distance covered during interval Ta + Td is given by:
                    segment_length_inches = Xa + Xd = Vi * Ta + (1/2) Amax * Ta^2 + Vf * Td + (1/2) Amax * Td^2

                (vi) Now substituting in Td = Ta - (Dv / Amax), we find:
                    Amax * Ta^2 + 2 * Vi * Ta + ( Vi^2 - Vf^2 )/( 2 * Amax ) - segment_length_inches = 0
                    
                    Solving this quadratic equation for Ta, we find:
                    Ta = ( sqrt(2 * Vi^2 + 2 * Vf^2 + 4 * Amax * segment_length_inches) - 2 * Vi ) / ( 2 * Amax )
                    
                    [We pick the positive root in the quadratic formula, since Ta must be positive.]
                
                (vii) From Ta and part (iv) above, we can find Vmax and Td.
                """

                if spew_segment_debug_data:
                    self.text_log('\nType 2: Triangle')

                if segment_length_inches >= 0.9 * (accel_dist_max + decel_dist_max):
                    accel_rate_local = 0.9 * ((accel_dist_max + decel_dist_max) / segment_length_inches) * accel_rate

                    if accel_dist_max + decel_dist_max == 0:
                        accel_rate_local = accel_rate  # prevent possible divide by zero case, if already at full speed

                    if spew_segment_debug_data:
                        self.text_log('accel_rate_local changed')
                else:
                    accel_rate_local = accel_rate

                if accel_rate_local > 0:  # Handle edge cases including when we are already at maximum speed
                    ta = (math.sqrt(2 * vi_inches_per_sec * vi_inches_per_sec + 2 * vf_inches_per_sec * vf_inches_per_sec + 4 * accel_rate_local * segment_length_inches)
                          - 2 * vi_inches_per_sec) / (2 * accel_rate_local)
                else:
                    ta = 0

                vmax = vi_inches_per_sec + accel_rate_local * ta
                if spew_segment_debug_data:
                    self.text_log('vmax: ' + str(vmax))

                intervals = int(math.floor(ta / time_slice))  # Number of intervals during acceleration

                if intervals == 0:
                    ta = 0

                if accel_rate_local > 0:  # Handle edge cases including when we are already at maximum speed
                    td = ta - (vf_inches_per_sec - vi_inches_per_sec) / accel_rate_local
                else:
                    td = 0

                d_intervals = int(math.floor(td / time_slice))  # Number of intervals during acceleration

                if intervals + d_intervals > 4:
                    if intervals > 0:
                        if spew_segment_debug_data:
                            self.text_log('Triangle intervals UP: ' + str(intervals))

                        time_per_interval = ta / intervals
                        velocity_step_size = (vmax - vi_inches_per_sec) / (intervals + 1.0)
                        # For six time intervals of acceleration, first interval is at velocity (max/7)
                        # 6th (last) time interval is at 6*max/7
                        # after this interval, we are at full speed.

                        for index in xrange(0, intervals):  # Calculate acceleration phase
                            velocity += velocity_step_size
                            time_elapsed += time_per_interval
                            position += velocity * time_per_interval
                            duration_array.append(int(round(time_elapsed * 1000.0)))
                            dist_array.append(position)  # Estimated distance along direction of travel
                    else:
                        if spew_segment_debug_data:
                            self.text_log('Note: Skipping accel phase in triangle.')

                    if d_intervals > 0:
                        if spew_segment_debug_data:
                            self.text_log('Triangle intervals Down: ' + str(d_intervals))

                        time_per_interval = td / d_intervals
                        velocity_step_size = (vmax - vf_inches_per_sec) / (d_intervals + 1.0)
                        # For six time intervals of acceleration, first interval is at velocity (max/7)
                        # 6th (last) time interval is at 6*max/7
                        # after this interval, we are at full speed.

                        for index in xrange(0, d_intervals):  # Calculate acceleration phase
                            velocity -= velocity_step_size
                            time_elapsed += time_per_interval
                            position += velocity * time_per_interval
                            duration_array.append(int(round(time_elapsed * 1000.0)))
                            dist_array.append(position)  # Estimated distance along direction of travel
                    else:
                        if spew_segment_debug_data:
                            self.text_log('Note: Skipping decel phase in triangle.')
                else:
                    """ 
                    Case 3: 'Linear or constant velocity changes' 
                    
                    Picked for segments that are shorter than 6 time slices. 
                    Linear velocity interpolation between two endpoints.
                    
                    Because these are typically short segments (not enough time for a good "triangle"--
                    we slightly boost the starting speed, by taking its average with vmax for the segment.
                    
                    For very short segments (less than 2 time slices), use a single 
                        segment with constant velocity.
                    """

                    if spew_segment_debug_data:
                        self.text_log('Type 3: Linear' + '\n')
                    # xFinal = vi * t  + (1/2) a * t^2, and vFinal = vi + a * t
                    # Combining these (with same t) gives: 2 a x = (vf^2 - vi^2)  => a = (vf^2 - vi^2)/2x
                    # So long as this 'a' is less than accel_rate, we can linearly interpolate in velocity.

                    vi_inches_per_sec = (vmax + vi_inches_per_sec) / 2  # Boost initial speed for this segment
                    velocity = vi_inches_per_sec  # Boost initial speed for this segment

                    local_accel = (vf_inches_per_sec * vf_inches_per_sec - vi_inches_per_sec * vi_inches_per_sec) / (2.0 * segment_length_inches)

                    if local_accel > accel_rate:
                        local_accel = accel_rate
                    elif local_accel < -accel_rate:
                        local_accel = -accel_rate
                    if local_accel == 0:
                        # Initial velocity = final velocity -> Skip to constant velocity routine.
                        constant_vel_mode = True
                    else:
                        t_segment = (vf_inches_per_sec - vi_inches_per_sec) / local_accel

                        intervals = int(math.floor(t_segment / time_slice))  # Number of intervals during deceleration
                        if intervals > 1:
                            time_per_interval = t_segment / intervals
                            velocity_step_size = (vf_inches_per_sec - vi_inches_per_sec) / (intervals + 1.0)
                            # For six time intervals of acceleration, first interval is at velocity (max/7)
                            # 6th (last) time interval is at 6*max/7
                            # after this interval, we are at full speed.

                            for index in xrange(0, intervals):  # Calculate acceleration phase
                                velocity += velocity_step_size
                                time_elapsed += time_per_interval
                                position += velocity * time_per_interval
                                duration_array.append(int(round(time_elapsed * 1000.0)))
                                dist_array.append(position)  # Estimated distance along direction of travel
                        else:
                            # Short segment; Not enough time for multiple segments at different velocities.
                            vi_inches_per_sec = vmax  # These are _slow_ segments-- use fastest possible interpretation.
                            constant_vel_mode = True

        if constant_vel_mode:
            """
            Case 4: 'Constant Velocity mode'
            """

            if spew_segment_debug_data:
                self.text_log('-> [Constant Velocity Mode Segment]' + '\n')
            # Single segment with constant velocity.

            if self.options.const_speed and not self.pen_up:
                velocity = self.speed_pendown  # Constant pen-down speed
            elif vf_inches_per_sec > vi_inches_per_sec:
                velocity = vf_inches_per_sec
            elif vi_inches_per_sec > vf_inches_per_sec:
                velocity = vi_inches_per_sec
            elif vi_inches_per_sec > 0:  # Allow case of two are equal, but nonzero
                velocity = vi_inches_per_sec
            else:  # Both endpoints are equal to zero.
                velocity = self.speed_pendown / 10  # TODO: Check this method. May be better to level it out to same value as others.

            if spew_segment_debug_data:
                self.text_log('velocity: ' + str(velocity))

            time_elapsed = segment_length_inches / velocity
            duration_array.append(int(round(time_elapsed * 1000.0)))
            dist_array.append(segment_length_inches)  # Estimated distance along direction of travel
            position += segment_length_inches

        """ 
        The time & distance motion arrays for this path segment are now computed.
        Next: We scale to the correct intended travel distance, 
        round into integer motor steps and manage the process
        of sending the output commands to the motors.
        """

        if spew_segment_debug_data:
            self.text_log('position/segment_length_inches: ' + str(position / segment_length_inches))

        for index in xrange(0, len(dist_array)):
            # Scale our trajectory to the "actual" travel distance that we need:
            fractional_distance = dist_array[index] / position  # Fractional position along the intended path
            dest_array1.append(int(round(fractional_distance * motor_steps1)))
            dest_array2.append(int(round(fractional_distance * motor_steps2)))

            sum(dest_array1)

        if spew_segment_debug_data:
            self.text_log('\nSanity check after computing motion:')
            self.text_log('Final motor_steps1: {0:}'.format(dest_array1[-1]))  # View last element in list
            self.text_log('Final motor_steps2: {0:}'.format(dest_array2[-1]))  # View last element in list

        prev_motor1 = 0
        prev_motor2 = 0
        prev_time = 0

        for index in xrange(0, len(dest_array1)):
            move_steps1 = dest_array1[index] - prev_motor1
            move_steps2 = dest_array2[index] - prev_motor2
            move_time = duration_array[index] - prev_time
            prev_time = duration_array[index]

            if move_time < 1:
                move_time = 1  # don't allow zero-time moves.

            if abs(float(move_steps1) / float(move_time)) < 0.002:
                move_steps1 = 0  # don't allow too-slow movements of this axis
            if abs(float(move_steps2) / float(move_time)) < 0.002:
                move_steps2 = 0  # don't allow too-slow movements of this axis

            # Don't allow too fast movements of either axis: Catch rounding errors that could cause an overspeed event
            while (abs(float(move_steps1) / float(move_time)) >= axidraw_conf.MaxStepRate) or (abs(float(move_steps2) / float(move_time)) >= axidraw_conf.MaxStepRate):
                move_time += 1

            prev_motor1 += move_steps1
            prev_motor2 += move_steps2

            if move_steps1 != 0 or move_steps2 != 0:  # if at least one motor step is required for this move.

                motor_dist1_temp = float(move_steps1) / (self.StepScaleFactor * 2.0)
                motor_dist2_temp = float(move_steps2) / (self.StepScaleFactor * 2.0)

                # Convert back to find the actual X & Y distances that will be moved:
                x_delta = (motor_dist1_temp + motor_dist2_temp)  # X Distance moved in this subsegment, in inches
                y_delta = (motor_dist1_temp - motor_dist2_temp)  # Y Distance moved in this subsegment, in inches

                if not self.resume_mode and not self.b_stopped:

                    f_new_x = self.f_curr_x + x_delta
                    f_new_y = self.f_curr_y + y_delta

                    if self.options.preview:
                        self.pt_estimate += move_time
                        if self.options.rendering > 0:  # Generate preview paths
                            if self.vel_data_plot:
                                velocity_local1 = move_steps1 / float(move_time)
                                velocity_local2 = move_steps2 / float(move_time)
                                velocity_local = plot_utils.distance(move_steps1, move_steps2) / float(move_time)
                                self.updateVCharts(velocity_local1, velocity_local2, velocity_local)
                                self.vel_data_time += move_time
                                self.updateVCharts(velocity_local1, velocity_local2, velocity_local)
                            if self.rotate_page:
                                x_new_t = self.doc_unit_scale_factor * (self.svg_width - f_new_y)
                                y_new_t = self.doc_unit_scale_factor * f_new_x
                                x_old_t = self.doc_unit_scale_factor * (self.svg_width - self.f_curr_y)
                                y_old_t = self.doc_unit_scale_factor * self.f_curr_x
                            else:
                                x_new_t = self.doc_unit_scale_factor * f_new_x
                                y_new_t = self.doc_unit_scale_factor * f_new_y
                                x_old_t = self.doc_unit_scale_factor * self.f_curr_x
                                y_old_t = self.doc_unit_scale_factor * self.f_curr_y
                            if self.pen_up:
                                if self.options.rendering > 1:  # rendering is 2 or 3. Show pen-up movement
                                    if self.path_data_pen_up != 1:
                                        self.path_data_pu.append("M{0:0.3f} {1:0.3f}".format(x_old_t, y_old_t))
                                        self.path_data_pen_up = 1  # Reset pen state indicator
                                    self.path_data_pu.append(" {0:0.3f} {1:0.3f}".format(x_new_t, y_new_t))
                            else:
                                if self.options.rendering == 1 or self.options.rendering == 3:  # If 1 or 3, show pen-down movement
                                    if self.path_data_pen_up != 0:
                                        self.path_data_pd.append("M{0:0.3f} {1:0.3f}".format(x_old_t, y_old_t))
                                        self.path_data_pen_up = 0  # Reset pen state indicator
                                    self.path_data_pd.append(" {0:0.3f} {1:0.3f}".format(x_new_t, y_new_t))
                    else:
                        ebb_motion.doXYMove(self.serial_port, move_steps2, move_steps1, move_time)
                        if move_time > 50:
                            if self.options.mode != "manual":
                                time.sleep(float(move_time - 10) / 1000.0)  # pause before issuing next command

                    if spew_segment_debug_data:
                        self.text_log('XY move:({0}, {1}), in {2} ms'.format(move_steps1, move_steps2, move_time))
                        self.text_log('fNew(X,Y) :({0:.2}, {1:.2})'.format(f_new_x, f_new_y))
                        if (move_steps1 / move_time) >= axidraw_conf.MaxStepRate:
                            self.text_log('Motor 1 overspeed error.')
                        if (move_steps2 / move_time) >= axidraw_conf.MaxStepRate:
                            self.text_log('Motor 2 overspeed error.')

                    self.f_curr_x = f_new_x  # Update current position
                    self.f_curr_y = f_new_y

                    self.svg_last_known_pos_x = self.f_curr_x - axidraw_conf.StartPosX
                    self.svg_last_known_pos_y = self.f_curr_y - axidraw_conf.StartPosY

    def PauseResumeCheck(self):
        # Pause & Resume functionality is managed here, called (for example) while planning
        # a segment to plot. First check to see if the pause button has been pressed.
        # Increment the node counter.
        # Also, resume drawing if we _were_ in resume mode and need to resume at this node.

        pause_state = 0
        
        if self.b_stopped:
            return  # We have _already_ halted the plot due to a button press. No need to proceed.

        if self.options.preview:
            str_button = 0
        else:
            str_button = ebb_motion.QueryPRGButton(self.serial_port)  # Query if button pressed

        #To test corner cases of pause and resume cycles, one may manually force a pause:
        #if (self.options.mode == "plot") and (self.node_count == 24):
        #    self.force_pause = True

        if self.force_pause:
            str_button = 1  # simulate pause button press

        if self.serial_port is not None:
            try:
                pause_state = int(str_button[0])
            except:                    
                self.error_log('\nUSB connection to AxiDraw lost.')
                pause_state = 2  # Pause the plot; we appear to have lost connectivity.
                if self.spew_debugdata:
                    self.error_log('\n (Node # : ' + str(self.node_count) + ')')


        if pause_state == 1 and not self.delay_between_copies:
            if self.force_pause:
                self.error_log('Plot paused by layer name control.')
            else:
                if self.Secondary or self.options.mode == "interactive": 
                    self.error_log('Plot halted by button press.')
                    self.error_log('Important: Manually home this AxiDraw before plotting next item.')
                else:
                    self.error_log('Plot paused by button press.')

            if self.spew_debugdata:
                self.text_log('\n (Paused after node number : ' + str(self.node_count) + ')')

        if pause_state == 1 and self.delay_between_copies:
            self.error_log('Plot sequence ended between copies.')

        if self.force_pause:
            self.force_pause = False  # Clear the flag

        if pause_state == 1 or pause_state == 2:  # Stop plot
            self.svg_node_count = self.node_count
            self.svg_paused_pos_x = self.f_curr_x - axidraw_conf.StartPosX
            self.svg_paused_pos_y = self.f_curr_y - axidraw_conf.StartPosY
            self.pen_raise()
            if not self.delay_between_copies and \
                not self.Secondary and self.options.mode != "interactive":  
                # Only say this if we're not in the delay between copies, nor a "second" unit.
                self.text_log('Use the resume feature to continue.')
            self.b_stopped = True
            return  # Note: This segment is not plotted.

        self.node_count += 1  # This whole segment move counts as ONE pause/resume node in our plot

        if self.resume_mode:
            if self.node_count >= self.node_target:
                self.resume_mode = False
                if self.spew_debugdata:
                    self.text_log('\nRESUMING PLOT at node : ' + str(self.node_count))
                    self.text_log('\nself.virtual_pen_up : ' + str(self.virtual_pen_up))
                    self.text_log('\nself.pen_up : ' + str(self.pen_up))
                if not self.virtual_pen_up:  # This is the point where we switch from virtual to real pen
                    self.pen_lower()

    def serial_connect(self):
        named_port = None
#         if self.options.port is not None:
#             self.text_log('str(type(self.options.port)) : ' + str(type(self.options.port)))
        
        if self.options.port_config == 1: # port_config value "1": Use first available AxiDraw.
            self.options.port = None
        if not self.options.port: # Try to connect to first available AxiDraw.
            self.serial_port = ebb_serial.openPort()
        elif str(type(self.options.port)) in (
            "<type 'str'>", "<type 'unicode'>", "<class 'str'>"):
            # This function may be passed a port name to open (and later close).
            tempstring = str(self.options.port)
            self.options.port = tempstring.strip('\"')
            named_port = self.options.port
            # self.text_log( 'About to test serial port: ' + str(self.options.port) )
            the_port = ebb_serial.find_named_ebb(self.options.port)
            self.serial_port = ebb_serial.testPort(the_port)
            self.options.port = None  # Clear this input, to ensure that we close the port later.
        else:
            # This function may be passed a serial port object reference;
            # an instance of serial.serialposix.Serial.
            # In that case, we should interact with that given
            # port object, and leave it open at the end.

            self.serial_port = self.options.port
        if self.serial_port is None:
            if named_port:
                self.error_log(gettext.gettext('Failed to connect to AxiDraw "' + str(named_port) + '"'))
            else:
                self.error_log(gettext.gettext("Failed to connect to AxiDraw."))
            return
            
        elif self.spew_debugdata: # Successfully connected
            if named_port:
                self.text_log(gettext.gettext('Connected successfully to port:  ' + str(named_port) ))
            else:
              self.text_log (" Connected successfully")
#             self.text_log ( ebb_serial.query_nickname(self.serial_port, False))


    def EnableMotors(self):
        """
        Enable motors, set native motor resolution, and set speed scales.

        The "pen down" speed scale is adjusted with the following factors
        that make the controls more intuitive:
        * Reduce speed by factor of 2 when using 8X microstepping
        * Reduce speed by factor of 2 when disabling acceleration

        These factors prevent unexpected dramatic changes in speed when turning
        those two options on and off.
        """

        if self.use_custom_layer_speed:
            local_speed_pendown = self.layer_speed_pendown
        else:
            local_speed_pendown = self.options.speed_pendown

        if self.options.resolution == 1:  # High-resolution ("Super") mode
            if not self.options.preview:
                ebb_motion.sendEnableMotors(self.serial_port, 1)  # 16X microstepping
            self.StepScaleFactor = 2.0 * axidraw_conf.NativeResFactor
            self.speed_pendown = local_speed_pendown * axidraw_conf.SpeedLimXY_HR / 110.0  # Speed given as maximum inches/second in XY plane
            self.speed_penup = self.options.speed_penup * axidraw_conf.SpeedLimXY_HR / 110.0  # Speed given as maximum inches/second in XY plane

        else:  # i.e., self.options.resolution == 2; Low-resolution ("Normal") mode
            if not self.options.preview:
                ebb_motion.sendEnableMotors(self.serial_port, 2)  # 8X microstepping
            self.StepScaleFactor = axidraw_conf.NativeResFactor
            # In low-resolution mode, allow faster pen-up moves. Keep maximum pen-down speed the same.
            self.speed_penup = self.options.speed_penup * axidraw_conf.SpeedLimXY_LR / 110.0  # Speed given as maximum inches/second in XY plane
            self.speed_pendown = local_speed_pendown * axidraw_conf.SpeedLimXY_LR / 110.0  # Speed given as maximum inches/second in XY plane

        if self.options.const_speed:
            if self.options.resolution == 1:  # High-resolution ("Super") mode
                self.speed_pendown = self.speed_pendown * axidraw_conf.const_speedFactor_LR
            else:
                self.speed_pendown = self.speed_pendown * axidraw_conf.const_speedFactor_HR

            # TODO: Re-evaluate this approach. It may be better to allow a higher maximum speed, but
            #    get to it via a very short (1-2 segment only) acceleration period, rather than truly constant.
        # ebb_motion.PBOutConfig( self.serial_port, 3, 0 )    # Configure I/O Pin B3 as an output, low

    def pen_raise(self):
        self.virtual_pen_up = True  # Virtual pen keeps track of state for resuming plotting.
        if not self.resume_mode and not self.pen_up:  # skip if pen is already up, or if we're resuming.
            if self.use_custom_layer_pen_height:
                pen_down_pos = self.layer_pen_pos_down
            else:
                pen_down_pos = self.options.pen_pos_down

            v_distance = float(self.options.pen_pos_up - pen_down_pos)
            v_time = int((1000.0 * v_distance) / (3 * self.options.pen_rate_raise))
            if v_time < 0:  # Handle case that pen_pos_down is above pen_pos_up
                v_time = -v_time
            v_time += self.options.pen_delay_up
            if v_time < 0:  # Do not allow negative delay times
                v_time = 0
            if self.options.preview:
                self.updateVCharts(0, 0, 0)
                self.vel_data_time += v_time
                self.updateVCharts(0, 0, 0)
                self.pt_estimate += v_time
            else:
                ebb_motion.sendPenUp(self.serial_port, v_time)
                # ebb_motion.PBOutValue( self.serial_port, 3, 0 )    # I/O Pin B3 output: low
                if v_time > 50:
                    if self.options.mode != "manual":
                        time.sleep(float(v_time - 10) / 1000.0)  # pause before issuing next command
            self.pen_up = True
        self.path_data_pen_up = -1

    def pen_lower(self):
        self.virtual_pen_up = False  # Virtual pen keeps track of state for resuming plotting.
        if self.pen_up or self.pen_up is None:  # skip if pen is already down
            if not self.resume_mode and not self.b_stopped:  # skip if resuming or stopped
                if self.use_custom_layer_pen_height:
                    pen_down_pos = self.layer_pen_pos_down
                else:
                    pen_down_pos = self.options.pen_pos_down
                v_distance = float(self.options.pen_pos_up - pen_down_pos)
                v_time = int((1000.0 * v_distance) / (3 * self.options.pen_rate_lower))
                if v_time < 0:  # Handle case that pen_pos_down is above pen_pos_up
                    v_time = -v_time
                v_time += self.options.pen_delay_down
                if v_time < 0:  # Do not allow negative delay times
                    v_time = 0
                if self.options.preview:
                    self.updateVCharts(0, 0, 0)
                    self.vel_data_time += v_time
                    self.updateVCharts(0, 0, 0)
                    self.pt_estimate += v_time
                else:
                    ebb_motion.sendPenDown(self.serial_port, v_time)
                    # ebb_motion.PBOutValue( self.serial_port, 3, 1 )    # I/O Pin B3 output: high
                    if v_time > 50:
                        if self.options.mode != "manual":
                            # pause before issuing next command
                            time.sleep(float(v_time - 10) / 1000.0)  
                self.pen_up = False
        self.path_data_pen_up = -1

    def ServoSetupWrapper(self):
        # Utility wrapper for self.ServoSetup.
        #
        # 1. Configure servo up & down positions and lifting/lowering speeds.
        # 2. Query EBB to learn if we're in the up or down state.
        #
        # This wrapper is used in the manual, setup, and various plot modes,
        #   for initial pen raising/lowering.

        self.ServoSetup()  # Pre-stage the pen up and pen down positions
        if self.options.preview:
            self.pen_up = True  # A fine assumption when in preview mode
            self.virtual_pen_up = True  #
        else:  # Need to figure out if we're in the pen-up or pen-down state... or neither!
        
            value = ebb_motion.queryEBBLV(self.serial_port)
            if value != self.options.pen_pos_up + 1:
                """
                When the EBB is reset, it goes to its default "pen up" position,
                for which QueryPenUp will tell us that the EBB believes it is
                in the pen-up position. However, its actual position is the
                default, not the pen-up position that we've requested.
                
                To fix this, we can manually command the pen to either the
                pen-up or pen-down position, as requested. HOWEVER, that may
                take as much as five seconds in the very slowest pen-movement
                speeds, and we want to skip that delay if the pen were actually
                already in the right place, for example if we're plotting right
                after raising the pen, or plotting twice in a row
                
                Solution: Use an otherwise unused EBB firmware variable (EBBLV),
                which is set to zero upon reset. If we set that value to be
                nonzero, and later find that it's still nonzero, we know that
                the servo position has been set (at least once) since reset.
                
                Knowing that the pen is up _does not_ confirm that the pen is
                at the *requested* pen-up position. We can store
                (self.options.pen_pos_up + 1), with possible values in the range
                1 - 101 in EBBLV, to verify that the current position is
                correct, and that we can  skip extra pen-up/pen-down movements.
                """

                self.pen_up = None
                self.virtual_pen_up = False
                ebb_motion.setEBBLV(self.serial_port, self.options.pen_pos_up + 1) 

            else:   # It looks like the EEBLV has already been set; we can trust the value from QueryPenUp:
                    # Note, however, that this does not ensure that the current 
                    #    Z position matches that in the settings.
                if ebb_motion.QueryPenUp(self.serial_port):
                    self.pen_up = True
                    self.virtual_pen_up = True
                else:
                    self.pen_up = False
                    self.virtual_pen_up = False

    def ServoSetup(self):
        """
        Pen position units range from 0% to 100%, which correspond to
        a typical timing range of 7500 - 25000 in units of 1/(12 MHz).
        1% corresponds to ~14.6 us, or 175 units of 1/(12 MHz).
        """

        if self.use_custom_layer_pen_height:
            pen_down_pos = self.layer_pen_pos_down
        else:
            pen_down_pos = self.options.pen_pos_down

        if not self.options.preview:
            servo_range = axidraw_conf.ServoMax - axidraw_conf.ServoMin
            servo_slope = float(servo_range) / 100.0

            int_temp = int(round(axidraw_conf.ServoMin + servo_slope * self.options.pen_pos_up))
            ebb_motion.setPenUpPos(self.serial_port, int_temp)

            int_temp = int(round(axidraw_conf.ServoMin + servo_slope * pen_down_pos))
            ebb_motion.setPenDownPos(self.serial_port, int_temp)

            """ 
            Servo speed units (as set with setPenUpRate) are units of %/second,
            referring to the percentages above.  
            The EBB takes speeds in units of 1/(12 MHz) steps
            per 24 ms.  Scaling as above, 1% of range in 1 second 
            with SERVO_MAX = 27831 and SERVO_MIN = 9855
            corresponds to 180 steps change in 1 s
            That gives 0.180 steps/ms, or 4.5 steps / 24 ms.
            
            Our input range (1-100%) corresponds to speeds up to 
            100% range in 0.25 seconds, or 4 * 4.5 = 18 steps/24 ms.
            """

            int_temp = 18 * self.options.pen_rate_raise
            ebb_motion.setPenUpRate(self.serial_port, int_temp)

            int_temp = 18 * self.options.pen_rate_lower
            ebb_motion.setPenDownRate(self.serial_port, int_temp)

    def queryEBBVoltage(self):  # Check that power supply is detected.
        if axidraw_conf.SkipVoltageCheck:
            return
        if self.serial_port is not None and not self.options.preview:
            voltage_o_k = ebb_motion.queryVoltage(self.serial_port)
            if not voltage_o_k:
                if 'voltage' not in self.warnings:
                    self.text_log(gettext.gettext('Warning: Low voltage detected.\nCheck that power supply is plugged in.'))
                    self.warnings['voltage'] = 1

    def getDocProps(self):
        """
        Get the document's height and width attributes from the <svg> tag.
        Use a default value in case the property is not present or is
        expressed in units of percentages.
        """

        self.svg_height = plot_utils.getLengthInches(self, 'height')
        self.svg_width = plot_utils.getLengthInches(self, 'width')

        width_string = self.svg.get('width')
        if width_string:
            value, units = plot_utils.parseLengthWithUnits(width_string)
            self.doc_units = units

        if self.options.no_rotate:
            self.options.auto_rotate = False
        if self.options.auto_rotate and (self.svg_height > self.svg_width):
            self.rotate_page = True
        if self.svg_height is None or self.svg_width is None:
            return False
        else:
            return True

    def text_log(self,text_to_add):
        if not self.Secondary:
            inkex.errormsg(text_to_add)
        else:
            self.text_out = self.text_out + '\n' + text_to_add

    def error_log(self,text_to_add):
        if not self.Secondary:
            inkex.errormsg(text_to_add)
        else:
            self.error_out = self.error_out + '\n' + text_to_add
    
    def get_output(self):
        # Return serialized copy of svg document output
        result = etree.tostring(self.document)
        return result.decode("utf-8")
    
    def plot_setup(self, svg_input):
        # For use as an imported python module
        # Initialize AxiDraw options & parse SVG file
        file_ok = False
        inkex.localize()
        self.getoptions([])
        # Parse input file or SVG string
        if svg_input is not None:
            try:
                stream = open(svg_input, 'r')
                p = etree.XMLParser(huge_tree=True)
                self.document = etree.parse(stream, parser=p)
                self.original_document = copy.deepcopy(self.document)
                stream.close()
                file_ok = True
            except IOError:
                pass # It wasn't a file...
            if not file_ok:
                try:
                    svg_string = svg_input.encode('utf-8') # Need consistent encoding.
                    p = etree.XMLParser(huge_tree=True, encoding='utf-8')
                    self.document = etree.ElementTree(etree.fromstring(svg_string, parser=p))
                    self.original_document = copy.deepcopy(self.document)
                    file_ok = True
                except:
                    self.error_log("Unable to open SVG input file.")
                    quit()
        if file_ok:
            self.getdocids()
        #self.Secondary = True # Option: Suppress standard output stream

    def plot_run(self, output=False):
        # For use as an imported python module
        # Plot the document, optionally return SVG file output
        if self.document is None:
            self.error_log("No SVG input provided.")
            self.error_log("Use plot_setup(svg_input) before plot_run().")
            quit()
        self.set_defaults()
        self.effect()
        if output:
            return self.get_output()

    def interactive(self):
        # Initialize AxiDraw options
        # For interactive-mode use as an imported python module
        inkex.localize()
        self.getoptions([])
        self.options.units = 0 # inches, by default
        self.options.preview = False
        self.options.mode = "interactive"
        self.Secondary = False
        
    def connect(self):
        # Begin session
        # For interactive-mode use as an imported python module
        #
        # Parse settings,
        # Connect to AxiDraw,
        # Raise pen,
        # Set position as (0,0).
        self.serial_connect()                   # Open USB serial session
        if self.serial_port is None:
            return False
        self.update_options()                   # Apply general settings
        self.f_curr_x = axidraw_conf.StartPosX  # Set XY position to (0,0)
        self.f_curr_y = axidraw_conf.StartPosY
        self.turtle_x = self.f_curr_x                # Set turtle position to (0,0)
        self.turtle_y = self.f_curr_y
        # Query if button pressed, to clear the result:
        ebb_motion.QueryPRGButton(self.serial_port)  
        self.ServoSetupWrapper()                # Apply servo settings
        self.pen_raise()                        # Raise pen
        self.EnableMotors()     # Set plot resolution & speed & enable motors
        return True
        
    def update(self):
        # Process optional parameters
        # For interactive-mode use as an imported python module
        self.update_options()
        if self.serial_port:
            self.ServoSetup()
            self.EnableMotors()  # Set plotting resolution & speed

    def _xy_plot_segment(self,relative,x_value,y_value): # Absolute move
        """
        Perform movements for interactive context XY movement commands.
        Internal function; uses inch units.
        Maintains record of "turtle" position, and directs the carriage to
        move from the last turtle position to the new turtle position,
        clipping that movement segment to the allowed bounds of movement.
        Commands directing movement outside of the bounds are clipped
        with pen up.
        """
        
        if self.options.units: # If using centimeter units
            x_value = x_value / 2.54
            y_value = y_value / 2.54
        if relative:
            x_value = self.turtle_x + x_value
            y_value = self.turtle_y + y_value
        segment =  [[self.turtle_x,self.turtle_y],
                    [x_value,y_value]] 
        accept, seg = plot_utils.clip_segment(segment, self.bounds)
        
        if accept: # If some part of the segment is within bounds
            if self.serial_port:
                self.plotSegmentWithVelocity(seg[1][0], seg[1][1], 0, 0)

        self.turtle_x = x_value
        self.turtle_y = y_value

    def goto(self,x_target,y_target): # Absolute move
        # absolute position move
        # For interactive-mode use as an imported python module
        self._xy_plot_segment(False,x_target, y_target)

    def moveto(self,x_target,y_target):
        # pen-up absolute position move
        # For interactive-mode use as an imported python module
        self.pen_raise()
        self._xy_plot_segment(False,x_target, y_target)

    def lineto(self,x_target,y_target):
        # pen-down absolute position move
        # For interactive-mode use as an imported python module
        self.pen_lower()
        self._xy_plot_segment(False,x_target, y_target)

    def go(self,x_delta,y_delta):
        # relative position move
        # For interactive-mode use as an imported python module
        self._xy_plot_segment(True,x_delta, y_delta)

    def move(self,x_delta,y_delta):
        # pen-up relative position move
        # For interactive-mode use as an imported python module
        self.pen_raise()
        self._xy_plot_segment(True,x_delta, y_delta)

    def line(self,x_delta,y_delta):
        # pen-down relative position move
        # For interactive-mode use as an imported python module
        self.pen_lower()
        self._xy_plot_segment(True,x_delta, y_delta)

    def penup(self):
        # For interactive-mode use as an imported python module
        self.pen_raise()

    def pendown(self):
        # For interactive-mode use as an imported python module
        self.pen_lower()

    def disconnect(self):
        # End session; disconnect from AxiDraw
        # For interactive-mode use as an imported python module
        if self.serial_port:
            ebb_serial.closePort(self.serial_port)
        self.serial_port = None


if __name__ == '__main__':
    e = AxiDraw()
    e.affect()