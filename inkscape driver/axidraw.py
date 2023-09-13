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
axidraw.py

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

See version_string below for current version and date.

Requires Python 3.7 or newer and Pyserial 3.5 or newer.
"""
# pylint: disable=pointless-string-statement

__version__ = '3.9.4'  # Dated 2023-09-09

import copy
import gettext
from importlib import import_module
import logging
import math
import time
import socket  # for exception handling only

from lxml import etree

from axidrawinternal.axidraw_options import common_options, versions

from axidrawinternal import path_objects
from axidrawinternal import digest_svg
from axidrawinternal import boundsclip
from axidrawinternal import plot_optimizations
from axidrawinternal import plot_status
from axidrawinternal import pen_handling
from axidrawinternal import plot_warnings
from axidrawinternal import serial_utils
from axidrawinternal import motion
from axidrawinternal import dripfeed
from axidrawinternal import preview

from axidrawinternal.plot_utils_import import from_dependency_import # plotink
simplepath = from_dependency_import('ink_extensions.simplepath')
simplestyle = from_dependency_import('ink_extensions.simplestyle')
cubicsuperpath = from_dependency_import('ink_extensions.cubicsuperpath')
simpletransform = from_dependency_import('ink_extensions.simpletransform')
inkex = from_dependency_import('ink_extensions.inkex')
exit_status = from_dependency_import('ink_extensions_utils.exit_status')
message = from_dependency_import('ink_extensions_utils.message')
ebb_serial = from_dependency_import('plotink.ebb_serial')  # https://github.com/evil-mad/plotink
ebb_motion = from_dependency_import('plotink.ebb_motion')
plot_utils = from_dependency_import('plotink.plot_utils')
text_utils = from_dependency_import('plotink.text_utils')
requests = from_dependency_import('requests')
urllib3 = from_dependency_import('urllib3') # for exception handling only

logger = logging.getLogger(__name__)

class AxiDraw(inkex.Effect):
    """ Main class for AxiDraw """

    logging_attrs = {"default_handler": message.UserMessageHandler()}

    def __init__(self, default_logging=True, user_message_fun=message.emit, params=None):
        if params is None:
            params = import_module("axidrawinternal.axidraw_conf") # Default configuration file
        self.params = params

        inkex.Effect.__init__(self)
        self.version_string = __version__

        self.OptionParser.add_option_group(
            common_options.core_options(self.OptionParser, params.__dict__))
        self.OptionParser.add_option_group(
            common_options.core_mode_options(self.OptionParser, params.__dict__))

        self.plot_status = plot_status.PlotStatus()
        self.pen = pen_handling.PenHandler()
        self.warnings = plot_warnings.PlotWarnings()
        self.preview = preview.Preview()

        self.spew_debugdata = False # Possibly add this as a PlotStatus variable
        self.set_defaults()
        self.digest = None
        self.vb_stash = [1, 1, 0, 0] # Viewbox storage
        self.bounds = [[0, 0], [0, 0]]
        self.connected = False # Python API variable.

        self.plot_status.secondary = False
        self.user_message_fun = user_message_fun

        if default_logging: # logging setup
            logger.setLevel(logging.INFO)
            logger.addHandler(self.logging_attrs["default_handler"])

        if self.spew_debugdata:
            logger.setLevel(logging.DEBUG) # by default level is INFO

    def set_up_pause_receiver(self, software_pause_event):
        """ use a multiprocessing.Event/threading.Event to communicate a
        keyboard interrupt (ctrl-C) to pause the AxiDraw """
        self._software_pause_event = software_pause_event

    def receive_pause_request(self):
        """pause receiver"""
        return hasattr(self, "_software_pause_event") and self._software_pause_event.is_set()

    def set_secondary(self, suppress_standard_out=True):
        """ If a "secondary" AxiDraw called by axidraw_control """
        self.plot_status.secondary = True
        self.called_externally = True
        if suppress_standard_out:
            self.suppress_standard_output_stream()

    def suppress_standard_output_stream(self):
        """ Save values we will need later in unsuppress_standard_output_stream """
        self.logging_attrs["additional_handlers"] = [SecondaryErrorHandler(self),\
            SecondaryNonErrorHandler(self)]
        self.logging_attrs["emit_fun"] = self.user_message_fun
        logger.removeHandler(self.logging_attrs["default_handler"])
        for handler in self.logging_attrs["additional_handlers"]:
            logger.addHandler(handler)

    def unsuppress_standard_output_stream(self):
        """ Release logging stream """
        logger.addHandler(self.logging_attrs["default_handler"])
        if self.logging_attrs["additional_handlers"]:
            for handler in self.logging_attrs["additional_handlers"]:
                logger.removeHandler(handler)

        self.user_message_fun = self.logging_attrs["emit_fun"]

    def set_defaults(self):
        """ Set default values of certain parameters
            These are set when the class is initialized.
            Also called in plot_run() in the Python API, to ensure that
            these defaults are set before plotting additional pages."""

        self.use_layer_speed = False
        self.plot_status.reset() # Clear serial port and pause status flags
        self.pen.reset() # Clear pen state, lift count, layer pen height flag
        self.warnings.reset() # Clear any warning messages
        self.time_elapsed = 0 # Available for use by python API

        self.svg_transform = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        self.digest = None

    def update_options(self):
        """ Parse and update certain options; called in effect and in interactive modes
            whenever the options are updated """

        x_bounds_min = 0.0
        y_bounds_min = 0.0

        # Physical travel bounds, based on AxiDraw model:
        if self.options.model == 2:
            x_bounds_max = self.params.x_travel_V3A3
            y_bounds_max = self.params.y_travel_V3A3
        elif self.options.model == 3:
            x_bounds_max = self.params.x_travel_V3XLX
            y_bounds_max = self.params.y_travel_V3XLX
        elif self.options.model == 4:
            x_bounds_max = self.params.x_travel_MiniKit
            y_bounds_max = self.params.y_travel_MiniKit
        elif self.options.model == 5:
            x_bounds_max = self.params.x_travel_SEA1
            y_bounds_max = self.params.y_travel_SEA1
        elif self.options.model == 6:
            x_bounds_max = self.params.x_travel_SEA2
            y_bounds_max = self.params.y_travel_SEA2
        elif self.options.model == 7:
            x_bounds_max = self.params.x_travel_V3B6
            y_bounds_max = self.params.y_travel_V3B6
        else:
            x_bounds_max = self.params.x_travel_default
            y_bounds_max = self.params.y_travel_default

        self.bounds = [[x_bounds_min - 1e-9, y_bounds_min - 1e-9],
                       [x_bounds_max + 1e-9, y_bounds_max + 1e-9]]

        # Speeds in inches/second:
        self.speed_pendown = self.params.speed_pendown * self.params.speed_lim_xy_hr / 110.0
        self.speed_penup = self.params.speed_penup * self.params.speed_lim_xy_hr / 110.0

        # Input limit checking; constrain input values and prevent zero speeds:
        self.options.pen_pos_up = plot_utils.constrainLimits(self.options.pen_pos_up, 0, 100)
        self.options.pen_pos_down = plot_utils.constrainLimits(self.options.pen_pos_down, 0, 100)
        self.options.pen_rate_raise = \
            plot_utils.constrainLimits(self.options.pen_rate_raise, 1, 200)
        self.options.pen_rate_lower = \
            plot_utils.constrainLimits(self.options.pen_rate_lower, 1, 200)
        self.options.speed_pendown = plot_utils.constrainLimits(self.options.speed_pendown, 1, 110)
        self.options.speed_penup = plot_utils.constrainLimits(self.options.speed_penup, 1, 200)
        self.options.accel = plot_utils.constrainLimits(self.options.accel, 1, 110)


    def effect(self):
        """Main entry point: check to see which mode/tab is selected, and act accordingly."""
        self.start_time = time.time()

        try:
            self.plot_status.secondary
        except AttributeError:
            self.plot_status.secondary = False

        self.text_out = '' # Text log for basic communication messages
        self.error_out = '' # Text log for significant errors

        self.plot_status.stats.reset() # Reset plot duration and distance statistics

        self.doc_units = "in"

        self.pen.phys.xpos = self.params.start_pos_x
        self.pen.phys.ypos = self.params.start_pos_y

        self.layer_speed_pendown = -1
        self.plot_status.copies_to_plot = 1

        self.plot_status.resume.reset() # New values to write to file:

        self.svg_width = 0
        self.svg_height = 0
        self.rotate_page = False

        self.update_options()

        self.options.mode = self.options.mode.strip("\"") # Input sanitization
        self.options.setup_type = self.options.setup_type.strip("\"")
        self.options.manual_cmd = self.options.manual_cmd.strip("\"")
        self.options.resume_type = self.options.resume_type.strip("\"")
        self.options.page_delay = max(self.options.page_delay, 0)

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
            self.user_message_fun(self.version_string)
            return
        if self.options.mode == "manual":
            if self.options.manual_cmd == "none":
                return  # No option selected. Do nothing and return no error.
            if self.options.manual_cmd == "strip_data":
                self.svg = self.document.getroot()
                for slug in ['WCB', 'MergeData', 'plotdata', 'eggbot']:
                    for node in self.svg.xpath('//svg:' + slug, namespaces=inkex.NSS):
                        self.svg.remove(node)
                self.user_message_fun(gettext.gettext(\
                    "All AxiDraw data has been removed from this SVG file."))
                return
            if self.options.manual_cmd in ("res_read", "res_adj_in", "res_adj_mm"):
                self.svg = self.document.getroot()
                self.user_message_fun(self.plot_status.resume.manage_offset(self))
                self.res_dist = max(self.plot_status.resume.new.pause_dist*25.4, 0) # Python API
                return
            if self.options.manual_cmd == "list_names": # Run before regular serial connection!
                self.name_list = ebb_serial.list_named_ebbs() # Variable available for python API
                if not self.name_list:
                    self.user_message_fun(gettext.gettext("No named AxiDraw units located.\n"))
                else:
                    self.user_message_fun(gettext.gettext("List of attached AxiDraw units:"))
                    for detected_ebb in self.name_list:
                        self.user_message_fun(detected_ebb)
                return

        if self.options.mode == "resume":
            if self.options.resume_type == "home":
                self.options.mode = "res_home"
            else:
                self.options.mode = "res_plot"
                self.options.copies = 1

        if self.options.mode == "setup":
            # setup mode -> either align, toggle, or cycle modes.
            self.options.mode = self.options.setup_type

        if self.options.digest > 1: # Generate digest only; do not run plot or preview
            self.options.preview = True # Disable serial communication; restrict certain functions

        if not self.options.preview:
            self.serial_connect()
            self.plot_status.resume.clear_button(self) # Query button to clear its state

        if self.options.mode == "sysinfo":
            versions.log_version_info(self.plot_status, self.params.check_updates,
                                      self.version_string, self.options.preview,
                                      self.user_message_fun, logger)

        if self.plot_status.port is None and not self.options.preview:
            return # unable to connect to axidraw

        if self.options.mode in ('align', 'toggle', 'cycle'):
            self.setup_command()
            self.warnings.report(self.called_externally, self.user_message_fun) # print warnings
            return

        if self.options.mode == "manual":
            self.manual_command() # Handle manual commands that use both power and usb.
            self.warnings.report(self.called_externally, self.user_message_fun) # print warnings
            return

        self.svg = self.document.getroot()
        self.plot_status.resume.update_needed = False
        self.plot_status.resume.new.model = self.options.model # Save model in file

        if self.options.mode in ("plot", "layers", "res_plot", "res_home"):
            # Read saved data from SVG file, including plob version information
            self.plot_status.resume.read_from_svg(self.svg)

        if self.options.mode == "res_plot":  # Initialization for resuming plots
            if self.plot_status.resume.old.pause_dist >= 0:
                self.pen.phys.xpos = self.plot_status.resume.old.last_x
                self.pen.phys.ypos = self.plot_status.resume.old.last_y
                self.plot_status.resume.new.rand_seed = self.plot_status.resume.old.rand_seed
                self.plot_status.resume.new.layer = self.plot_status.resume.old.layer
            else:
                logger.error(gettext.gettext(\
                    "No in-progress plot data found in file; unable to resume."))
                return

        if self.options.mode in ("plot", "layers", "res_plot"):
            self.plot_status.copies_to_plot = self.options.copies
            if self.plot_status.copies_to_plot == 0: # Special case: Continuous copies selected
                self.plot_status.copies_to_plot = -1 # Flag for continuous copies

            if self.options.preview and not self.options.random_start:
                # Special preview case: Without randomizing, pages have identical print time:
                self.plot_status.copies_to_plot = 1

            if self.options.mode == "plot":
                self.plot_status.resume.new.layer = -1  # Plot all layers
            if self.options.mode == "layers":
                self.plot_status.resume.new.layer = self.options.layer

            # Parse & digest SVG document, perform initial optimizations, prepare to resume:
            if not self.prepare_document():
                return

            if self.options.digest > 1: # Generate digest only; do not run plot or preview
                self.plot_cleanup()     # Revert document to save plob & print time elapsed
                self.plot_status.resume.new.plob_version = str(path_objects.PLOB_VERSION)
                self.plot_status.resume.write_to_svg(self.svg)
                self.warnings.report(False, self.user_message_fun) # print warnings
                return

            if self.options.mode == "res_plot": # Crop digest up to when the plot resumes:
                self.digest.crop(self.plot_status.resume.old.pause_dist)

            # CLI PROGRESS BAR: SET UP DRY RUN TO ESTIMATE PLOT LENGTH & TIME
            if self.plot_status.progress.review(self.plot_status, self.options):
                self.plot_document() # "Dry run": Estimate plot length & time

                self.user_message_fun(self.plot_status.progress.restore(self))
                self.plot_status.stats.reset() # Reset plot duration and distance statistics

            if self.options.mode == "res_plot":
                self.pen.phys.xpos = self.plot_status.resume.old.last_x
                self.pen.phys.ypos = self.plot_status.resume.old.last_y

                # Update so that if the plot is paused, we can resume again
                self.plot_status.stats.down_travel_inch = self.plot_status.resume.old.pause_dist

            first_copy = True
            while self.plot_status.copies_to_plot != 0:

                self.preview.reset() # Clear preview data before starting each plot
                self.plot_status.resume.update_needed = True
                self.plot_status.copies_to_plot -= 1

                if first_copy:
                    first_copy = False
                else:
                    self.plot_status.stats.next_page() # Update distance stats for next page
                    if self.options.random_start:
                        self.randomize_optimize() # Only need to re-optimize if randomizing
                self.plot_document()
                dripfeed.page_layer_delay(self, between_pages=True) # Delay between pages

            self.plot_cleanup() # Revert document, print time reports, send webhooks

        elif self.options.mode  == "res_home":
            self.plot_status.resume.copy_old()
            self.pen.phys.xpos = self.plot_status.resume.old.last_x
            self.pen.phys.ypos = self.plot_status.resume.old.last_y
            self.plot_status.resume.update_needed = True

            if not self.plot_status.resume.read:
                logger.error(gettext.gettext("No resume data found; unable to return Home."))
                return
            if (math.fabs(self.pen.phys.xpos < 0.001) and
                    math.fabs(self.pen.phys.ypos < 0.001)):
                logger.error(gettext.gettext(\
                    "Unable to move to Home. (Is the AxiDraw already at Home?)"))
                return

            self.query_ebb_voltage()
            self.pen.servo_init(self)
            self.pen.pen_raise(self)
            self.enable_motors()
            self.go_to_position(self.params.start_pos_x, self.params.start_pos_y)

        if self.plot_status.resume.update_needed:
            self.plot_status.resume.new.last_x = self.pen.phys.xpos
            self.plot_status.resume.new.last_y = self.pen.phys.ypos
            if self.options.digest: # i.e., if self.options.digest > 0
                self.plot_status.resume.new.plob_version = str(path_objects.PLOB_VERSION)
            self.plot_status.resume.write_to_svg(self.svg)
        if self.plot_status.port is not None:
            ebb_motion.doTimedPause(self.plot_status.port, 10, False) # Final timed motion command
            if self.options.port is None:  # Do not close serial port if it was opened externally.
                self.disconnect()
        self.warnings.report(self.called_externally, self.user_message_fun) # print warnings


    def setup_command(self):
        """ Commands from the setup modes. Need power and USB, but not SVG file. """

        if self.options.preview:
            self.user_message_fun('Command unavailable while in preview mode.')
            return

        if self.plot_status.port is None:
            return

        self.query_ebb_voltage()
        self.pen.servo_init(self)

        if self.options.mode == "align":
            self.pen.pen_raise(self)
            ebb_motion.sendDisableMotors(self.plot_status.port, False)
        elif self.options.mode == "cycle":
            self.pen.cycle(self)
        # Note that "toggle" mode is handled within self.pen.servo_init(self)

    def manual_command(self):
        """ Manual mode commands that need USB connectivity and don't need SVG file """

        if self.options.preview: # First: Commands that require serial but not power
            self.user_message_fun('Command unavailable while in preview mode.')
            return
        if self.plot_status.port is None:
            return

        if self.options.manual_cmd == "fw_version":
            self.user_message_fun(self.plot_status.fw_version)
            return

        if self.options.manual_cmd == "bootload":
            success = ebb_serial.bootload(self.plot_status.port)
            if success:
                self.user_message_fun(
                    gettext.gettext("Entering bootloader mode for firmware programming.\n" +
                                    "To resume normal operation, you will need to first\n" +
                                    "disconnect the AxiDraw from both USB and power."))
                self.disconnect() # Disconnect from AxiDraw; end serial session
            else:
                logger.error('Failed while trying to enter bootloader.')
            return

        if self.options.manual_cmd == "read_name":
            name_string = ebb_serial.query_nickname(self.plot_status.port)
            if name_string is None:
                logger.error(gettext.gettext("Error; unable to read nickname.\n"))
            else:
                self.user_message_fun(name_string)
            return

        if (self.options.manual_cmd).startswith("write_name"):
            temp_string = self.options.manual_cmd
            temp_string = temp_string.split("write_name", 1)[1] # Get part after "write_name"
            temp_string = temp_string[:16] # Only use first 16 characters in name
            if not temp_string:
                temp_string = "" # Use empty string to clear nickname.

            if versions.min_fw_version(self.plot_status, "2.5.5"):
                renamed = ebb_serial.write_nickname(self.plot_status.port, temp_string)
                if renamed is True:
                    if temp_string == "":
                        self.user_message_fun('Writing "blank" Nickname; setting to default.')
                    else:
                        self.user_message_fun(f'Nickname "{temp_string}" written.')
                    self.user_message_fun('Rebooting EBB.')
                else:
                    logger.error('Error encountered while writing nickname.')
                ebb_serial.reboot(self.plot_status.port)    # Reboot required after writing nickname
                self.disconnect() # Disconnect from AxiDraw; end serial session
            else:
                logger.error("This function requires a newer firmware version. See: axidraw.com/fw")
            return

        self.query_ebb_voltage() # Next: Commands that also require both power to move motors:
        if self.options.manual_cmd == "raise_pen":
            self.pen.servo_init(self) # Initializes to pen-up position
        elif self.options.manual_cmd == "lower_pen":
            self.pen.servo_init(self) # Initializes to pen-down position
        elif self.options.manual_cmd == "enable_xy":
            self.enable_motors()
        elif self.options.manual_cmd == "disable_xy":
            ebb_motion.sendDisableMotors(self.plot_status.port, False)
        else:  # walk motors or move home cases:
            self.pen.servo_init(self)
            self.enable_motors()  # Set plotting resolution
            if self.options.manual_cmd == "walk_home":
                if versions.min_fw_version(self.plot_status, "2.6.2"):
                    serial_utils.exhaust_queue(self) # Wait until all motion stops
                    a_pos, b_pos = ebb_motion.query_steps(self.plot_status.port, False)
                    n_delta_x = -(a_pos + b_pos) / (4 * self.params.native_res_factor)
                    n_delta_y = -(a_pos - b_pos) / (4 * self.params.native_res_factor)
                    if self.options.resolution == 2:  # Low-resolution mode
                        n_delta_x *= 2
                        n_delta_y *= 2
                else:
                    logger.error("This function requires newer firmware. Update at: axidraw.com/fw")
                    return
            elif self.options.manual_cmd == "walk_y":
                n_delta_x = 0
                n_delta_y = self.options.dist
            elif self.options.manual_cmd == "walk_x":
                n_delta_y = 0
                n_delta_x = self.options.dist
            elif self.options.manual_cmd == "walk_mmy":
                n_delta_x = 0
                n_delta_y = self.options.dist / 25.4
            elif self.options.manual_cmd == "walk_mmx":
                n_delta_y = 0
                n_delta_x = self.options.dist / 25.4
            else:
                return
            f_x = self.pen.phys.xpos + n_delta_x # Note: Walks are relative, not absolute!
            f_y = self.pen.phys.ypos + n_delta_y # New position is not saved; use with care.
            self.go_to_position(f_x, f_y, ignore_limits=True)


    def prepare_document(self):
        """
        Prepare the SVG document for plotting: Create the plot digest, join nearby ends,
        and perform supersampling. If not using randomization, then optimize the digest as well.
        """
        if not self.get_doc_props():
            logger.error(gettext.gettext('This document does not have valid dimensions.'))
            logger.error(gettext.gettext(
                'The page size should be in either millimeters (mm) or inches (in).\r\r'))
            logger.error(gettext.gettext(
                'Consider starting with the Letter landscape or '))
            logger.error(gettext.gettext('the A4 landscape template.\r\r'))
            logger.error(gettext.gettext('The page size may also be set in Inkscape,\r'))
            logger.error(gettext.gettext('using File > Document Properties.'))
            return False

        if not hasattr(self, 'backup_original'):
            self.backup_original = copy.deepcopy(self.document)

        # Modifications to SVG -- including re-ordering and text substitution
        #   may be made at this point, and will not be preserved.

        v_b = self.svg.get('viewBox')
        if v_b:
            p_a_r = self.svg.get('preserveAspectRatio')
            s_x, s_y, o_x, o_y = plot_utils.vb_scale(v_b, p_a_r, self.svg_width, self.svg_height)
        else:
            s_x = 1.0 / float(plot_utils.PX_PER_INCH) # Handle case of no viewbox
            s_y = s_x
            o_x = 0.0
            o_y = 0.0
        self.vb_stash = s_x, s_y, o_x, o_y

        # Initial transform of document is based on viewbox, if present:
        self.svg_transform = simpletransform.parseTransform(\
                f'scale({s_x:.6E},{s_y:.6E}) translate({o_x:.6E},{o_y:.6E})')

        valid_plob = False
        if self.plot_status.resume.old.plob_version:
            logger.debug('Checking Plob')
            valid_plob = digest_svg.verify_plob(self.svg, self.options.model)
        if valid_plob:
            logger.debug('Valid plob found; skipping standard pre-processing.')
            self.digest = path_objects.DocDigest()
            self.digest.from_plob(self.svg)
            self.plot_status.resume.new.plob_version = str(path_objects.PLOB_VERSION)
        else: # Process the input SVG into a simplified, restricted-format DocDigest object:
            digester = digest_svg.DigestSVG() # Initialize class
            if self.options.hiding: # Process all visible layers
                digest_params = [self.svg_width, self.svg_height, s_x, s_y,\
                    -2, self.params.curve_tolerance]
            else: # Process only selected layer, if in layers mode
                digest_params = [self.svg_width, self.svg_height, s_x, s_y,\
                    self.plot_status.resume.new.layer, self.params.curve_tolerance]
            self.digest = digester.process_svg(self.svg, self.warnings,
                digest_params, self.svg_transform,)

            if self.rotate_page: # Rotate digest
                self.digest.rotate(self.params.auto_rotate_ccw)

            if self.options.hiding:
                """
                Perform hidden-line clipping at this point, based on object
                    fills, clipping masks, and document and plotting bounds, via self.bounds
                """
                # clipping involves a non-pure Python dependency (pyclipper), so only import
                # when necessary
                from axidrawinternal.clipping import ClipPathsProcess
                bounds = ClipPathsProcess.calculate_bounds(self.bounds, self.svg_height,\
                    self.svg_width, self.params.clip_to_page, self.rotate_page)
                # flattening removes essential information for the clipping process
                assert not self.digest.flat
                self.digest.layers = ClipPathsProcess().run(self.digest.layers,\
                    bounds, clip_on=True)
                self.digest.layer_filter(self.plot_status.resume.new.layer) # For Layers mode
                self.digest.remove_unstroked() # Only stroked objects can plot
                self.digest.flatten() # Flatten digest before optimizations and plotting
            else:
                """
                Clip digest at plot bounds
                """
                if self.rotate_page:
                    doc_bounds = [self.svg_height + 1e-9, self.svg_width + 1e-9]
                else:
                    doc_bounds = [self.svg_width + 1e-9, self.svg_height + 1e-9]
                out_of_bounds_flag = boundsclip.clip_at_bounds(self.digest, self.bounds,\
                    doc_bounds, self.params.bounds_tolerance, self.params.clip_to_page)
                if out_of_bounds_flag:
                    self.warnings.add_new('bounds')

            """
            Possible future work: Perform automatic hatch filling at this point, based on object
                fill colors and possibly other factors.
            """

            """
            Optimize digest
            """

            allow_reverse = self.options.reordering in [2, 3]

            if self.options.reordering < 3: # Set reordering to 4 to disable path joining
                plot_optimizations.connect_nearby_ends(self.digest, allow_reverse,\
                    self.params.min_gap)

            plot_optimizations.supersample(self.digest,\
                self.params.segment_supersample_tolerance)

            self.randomize_optimize(True) # Do plot randomization & optimizations

        # If it is necessary to save as a Plob, that conversion can be made like so:
        # plob = self.digest.to_plob() # Unnecessary re-conversion for testing only
        # self.digest.from_plob(plob)  # Unnecessary re-conversion for testing only
        return True


    def randomize_optimize(self, first_copy=False):
        """ Randomize start points & perform reordering """

        if self.plot_status.resume.new.plob_version != "n/a":
            return # Working from valid plob; do not perform any optimizations.
        if self.options.random_start:
            if self.options.mode != "res_plot": # Use old rand seed when resuming a plot.
                self.plot_status.resume.new.rand_seed = int(time.time()*100)
            plot_optimizations.randomize_start(self.digest, self.plot_status.resume.new.rand_seed)

        allow_reverse = self.options.reordering in [2, 3]

        if self.options.reordering in [1, 2, 3]:
            plot_optimizations.reorder(self.digest, allow_reverse)

        if first_copy and self.options.digest: # Will return Plob, not full SVG; back it up here.
            self.backup_original = copy.deepcopy(self.digest.to_plob())


    def plot_document(self):
        """ Plot the prepared SVG document, if so selected in the interface """

        if not self.options.preview:
            self.plot_status.resume.clear_button(self) # Query button to clear its state
            self.options.rendering = 0 # Only render previews if we are in preview mode.
            self.preview.v_chart.enable = False
            if self.plot_status.port is None:
                return
            self.query_ebb_voltage()

        self.plot_status.progress.launch(self)

        try:  # wrap everything in a try so we can be sure to close the serial port
            self.pen.servo_init(self)
            self.pen.pen_raise(self)
            self.enable_motors()  # Set plotting resolution

            self.plot_doc_digest(self.digest) # Step through and plot contents of document digest
            self.pen.pen_raise(self)

            if self.plot_status.stopped == 0: # Return Home after normal plot
                self.plot_status.resume.new.clean() # Clear flags indicating resume status
                self.go_to_position(self.params.start_pos_x, self.params.start_pos_y)

        finally: # In case of an exception and loss of the serial port...
            pass

        self.plot_status.progress.close()

    def plot_cleanup(self):
        """
        Perform standard actions after a plot or the last copy from a set of plots:
        Revert file, render previews, print time reports, run webhook.

        Reverting is back to original SVG document, prior to adding preview layers.
            and prior to saving updated "plotdata" progress data in the file.
            No changes to the SVG document prior to this point will be saved.

        Doing so allows us to use routines that alter the SVG prior to this point,
            e.g., plot re-ordering for speed or font substitutions.
        """
        self.document = copy.deepcopy(self.backup_original)

        try: # Handle cases: backup_original May be etree Element or ElementTree
            self.svg = self.document.getroot() # For ElementTree, get the root
        except AttributeError:
            self.svg = self.document # For Element; no need to get the root

        if self.options.digest:
            self.options.rendering = 0 # Turn off rendering

        if self.options.digest > 1: # Save Plob file only and exit.
            elapsed_time = time.time() - self.start_time
            self.time_elapsed = elapsed_time # Available for use by python API
            if self.options.report_time and not self.called_externally: # Print time only
                self.user_message_fun("Elapsed time: " + text_utils.format_hms(elapsed_time))
            return

        self.preview.render(self) # Render preview on the page, if enabled and in preview mode

        if self.plot_status.progress.enable and self.plot_status.stopped == 0:
            self.user_message_fun("\nAxiCLI plot complete.\n") # If sequence ended normally.
        elapsed_time = time.time() - self.start_time
        self.time_elapsed = elapsed_time # Available for use by python API

        if not self.called_externally: # Compile time estimates & print time reports
            self.plot_status.stats.report(self.options, self.user_message_fun, elapsed_time)
            self.pen.status.report(self, self.user_message_fun)
            if self.options.report_time and self.plot_status.resume.new.plob_version != "n/a":
                self.user_message_fun("Document printed from valid Plob digest.")

        if self.options.webhook and not self.options.preview:
            if self.options.webhook_url is not None:
                payload = {'value1': str(self.digest.name),
                    'value2': str(text_utils.format_hms(elapsed_time)),
                    'value3': str(self.options.port),
                    }
                try:
                    requests.post(self.options.webhook_url, data=payload, timeout=7)
                except (TimeoutError, urllib3.exceptions.ConnectTimeoutError,\
                    urllib3.exceptions.MaxRetryError, requests.exceptions.ConnectTimeout):
                    self.user_message_fun("Webhook notification failed (Timed out).\n")
                except (urllib3.exceptions.NewConnectionError,\
                    socket.gaierror, requests.exceptions.ConnectionError):
                    self.user_message_fun("An error occurred while posting webhook. " +
                        "Check your internet connection and webhook URL.\n")

    def plot_doc_digest(self, digest):
        """
        Step through the document digest and plot each of the vertex lists.

        Takes a flattened path_objects.DocDigest object as input. All
        selection of elements to plot and their rendering, including
        transforms, needs to be handled before this routine.
        """

        if not digest:
            return

        for layer in digest.layers:

            self.pen.end_temp_height(self)
            old_use_layer_speed = self.use_layer_speed  # A Boolean
            old_layer_speed_pendown = self.layer_speed_pendown  # Numeric value
            self.pen.pen_raise(self) # Raise pen prior to computing layer properties

            if self.options.mode == "layers": # Special case: The plob contains all layers
                if layer.props.number != self.options.layer: # and is plotted in layers mode.
                    continue # Here, ensure that only certain layers should be printed.

            self.eval_layer_props(layer.props)

            for path_item in layer.paths:
                if self.plot_status.stopped:
                    return
                self.plot_polyline(path_item.subpaths[0])
            self.use_layer_speed = old_use_layer_speed # Restore old layer status variables

            if self.layer_speed_pendown != old_layer_speed_pendown:
                self.layer_speed_pendown = old_layer_speed_pendown
                self.enable_motors() # Set speed value variables for this layer.
            self.pen.end_temp_height(self)

    def eval_layer_props(self, layer_props):
        """
        Check for encoded pause, delay, speed, or height in the layer name, and act upon them.
        Syntax described at: https://wiki.evilmadscientist.com/AxiDraw_Layer_Control
        """

        if layer_props.pause: # Insert programmatic pause
            if not self.plot_status.progress.dry_run: # Skip during dry run only
                if self.plot_status.stopped == 0: # If not already stopped
                    self.plot_status.stopped = -1 # Set flag for programmatic pause
                self.pause_check()  # Carry out the pause, or resume if required.

        old_speed = self.layer_speed_pendown

        self.use_layer_speed = False
        self.layer_speed_pendown = -1

        if layer_props.delay:
            dripfeed.page_layer_delay(self, between_pages=False, delay_ms=layer_props.delay)
        if layer_props.height is not None: # New height will be used when we next lower the pen.
            self.pen.set_temp_height(self, layer_props.height)
        if layer_props.speed:
            self.use_layer_speed = True
            self.layer_speed_pendown = layer_props.speed

        if self.layer_speed_pendown != old_speed:
            self.enable_motors()  # Set speed value variables for this layer.

    def plot_polyline(self, vertex_list):
        """
        Plot a polyline object; a single pen-down XY movement.
        - No transformations, no curves, no neat clipping at document bounds;
            those are all performed _before_ we get to this point.
        - Truncate motion, brute-force, at travel bounds, without mercy or printed warnings.
        """

        if self.plot_status.stopped:
            logger.debug('Polyline: self.plot_status.stopped.')
            return
        if not vertex_list:
            logger.debug('No vertex list to plot. Returning.')
            return
        if len(vertex_list) < 2:
            logger.debug('No full segments in vertex list. Returning.')
            return

        self.pen.pen_raise(self) # Raise, if necessary, prior to pen-up travel to first vertex

        for vertex in vertex_list:
            vertex[0], _t_x = plot_utils.checkLimitsTol(vertex[0], 0, self.bounds[1][0], 2e-9)
            vertex[1], _t_y = plot_utils.checkLimitsTol(vertex[1], 0, self.bounds[1][1], 2e-9)
            # if _t_x or _t_y:
            #     logger.debug('Travel truncated to bounds at plot_polyline.')

        # Pen up straight move, zero velocity at endpoints, to first vertex location
        self.go_to_position(vertex_list[0][0], vertex_list[0][1])

        # Plan and feed trajectory, including lowering and raising pen before and after:
        the_trajectory = motion.trajectory(self, vertex_list)
        dripfeed.feed(self, the_trajectory[0])

    def go_to_position(self, x_dest, y_dest, ignore_limits=False, xyz_pos=None):
        '''
        Immediate XY move to destination, using normal motion planning. Replaces legacy
        function "plot_seg_with_v", assuming zero initial and final velocities.
        '''
        target_data = (x_dest, y_dest, 0, 0, ignore_limits)
        the_trajectory = motion.compute_segment(self, target_data, xyz_pos)
        dripfeed.feed(self, the_trajectory[0])

    def pause_check(self):
        """ Manage Pause functionality and stop plot if requested or at certain errors """
        if self.plot_status.stopped > 0:
            return  # Plot is already stopped. No need to proceed.

        pause_button_pressed = self.plot_status.resume.check_button(self)

        if self.receive_pause_request(): # Keyboard interrupt detected!
            self.plot_status.stopped = -103 # Code 104: "Keyboard interrupt"
            if self.plot_status.delay_between_copies: # However... it could have been...
                self.plot_status.stopped = -2 # Paused between copies (OK).

        if self.plot_status.stopped == -1:
            self.user_message_fun('Plot paused programmatically.\n')
        if self.plot_status.stopped == -103:
            self.user_message_fun('\nPlot paused by keyboard interrupt.\n')

        if pause_button_pressed == -1:
            self.user_message_fun('\nError: USB connection to AxiDraw lost. ' +\
                f'[Position: {25.4 * self.plot_status.stats.down_travel_inch:.3f} mm]\n')


            self.connected = False # Python interactive API variable
            self.plot_status.stopped = -104 # Code 104: "Lost connectivity"

        if pause_button_pressed == 1:
            if self.plot_status.delay_between_copies:
                self.plot_status.stopped = -2 # Paused between copies.
            elif self.options.mode == "interactive":
                logger.warning('Plot halted by button press during interactive session.')
                logger.warning('Manually home this AxiDraw before plotting next item.\n')
                self.plot_status.stopped = -102 # Code 102: "Paused by button press"
            else:
                self.user_message_fun('Plot paused by button press.\n')
                self.plot_status.stopped = -102 # Code 102: "Paused by button press"

        if self.plot_status.stopped == -2:
            self.user_message_fun('Plot sequence ended between copies.\n')

        if self.plot_status.stopped in (-1, -102, -103):
            self.user_message_fun('(Paused after: ' +\
                f'{25.4 * self.plot_status.stats.down_travel_inch:.3f} mm of pen-down travel.)')

        if self.plot_status.stopped < 0: # Stop plot
            self.pen.pen_raise(self)
            if not self.plot_status.delay_between_copies and \
                not self.plot_status.secondary  and self.options.mode != "interactive":
                # Only print if we're not in the delay between copies, nor a "second" unit.
                if self.plot_status.stopped != -104: # Do not display after loss of USB.
                    self.user_message_fun('Use the resume feature to continue.\n')
            self.plot_status.stopped = - self.plot_status.stopped
            self.plot_status.copies_to_plot = 0

            if self.options.mode not in ("plot", "layers", "res_plot"):
                return # Don't update pause_dist in res_home or repositioning modes

            self.plot_status.resume.new.pause_dist = self.plot_status.stats.down_travel_inch
            self.plot_status.resume.new.pause_ref = self.plot_status.stats.down_travel_inch

    def serial_connect(self):
        """ Connect to AxiDraw over USB """
        if serial_utils.connect(self.options, self.plot_status, self.user_message_fun, logger):
            self.connected = True  # Variable available in the Python interactive API.
        else:
            self.plot_status.stopped = 101 # Will become exit code 101; failed to connect

    def enable_motors(self):
        """
        Enable motors, set native motor resolution, and set speed scales.
        The "pen down" speed scale is adjusted by reducing speed when using 8X microstepping or
        disabling aceleration. These factors prevent unexpected dramatic changes in speed when
        turning those two options on and off.
        """
        if self.use_layer_speed:
            local_speed_pendown = self.layer_speed_pendown
        else:
            local_speed_pendown = self.options.speed_pendown

        if self.options.resolution == 1:  # High-resolution ("Super") mode
            if not self.options.preview:
                res_1, res_2 = ebb_motion.query_enable_motors(self.plot_status.port, False)
                if not (res_1 == 1 and res_2 == 1): # Do not re-enable if already enabled
                    ebb_motion.sendEnableMotors(self.plot_status.port, 1)  # 16X microstepping
            self.step_scale = 2.0 * self.params.native_res_factor
            self.speed_pendown = local_speed_pendown * self.params.speed_lim_xy_hr / 110.0
            self.speed_penup = self.options.speed_penup * self.params.speed_lim_xy_hr / 110.0
            if self.options.const_speed:
                self.speed_pendown = self.speed_pendown * self.params.const_speed_factor_hr
        else:  # i.e., self.options.resolution == 2; Low-resolution ("Normal") mode
            if not self.options.preview:
                res_1, res_2 = ebb_motion.query_enable_motors(self.plot_status.port, False)
                if not (res_1 == 2 and res_2 == 2): # Do not re-enable if already enabled
                    ebb_motion.sendEnableMotors(self.plot_status.port, 2)  # 8X microstepping
            self.step_scale = self.params.native_res_factor
            # Low-res mode: Allow faster pen-up moves. Keep maximum pen-down speed the same.
            self.speed_penup = self.options.speed_penup * self.params.speed_lim_xy_lr / 110.0
            self.speed_pendown = local_speed_pendown * self.params.speed_lim_xy_lr / 110.0
            if self.options.const_speed:
                self.speed_pendown = self.speed_pendown * self.params.const_speed_factor_lr
        # ebb_serial.command(self.plot_status.port, "CU,3,1\r") # EBB 2.8.1+: Enable data-low LED

    def query_ebb_voltage(self):
        """ Check that power supply is detected. """
        serial_utils.query_voltage(self.options, self.params, self.plot_status, self.warnings)

    def get_doc_props(self):
        """
        Get the document's height and width attributes from the <svg> tag. Use a default value in
        case the property is not present or is expressed in units of percentages.
        """

        self.svg_height = plot_utils.getLengthInches(self, 'height')
        self.svg_width = plot_utils.getLengthInches(self, 'width')

        width_string = self.svg.get('width')
        if width_string:
            _value, units = plot_utils.parseLengthWithUnits(width_string)
            self.doc_units = units
        if self.svg_height is None or self.svg_width is None:
            return False
        if self.options.no_rotate: # Override regular auto_rotate option
            self.options.auto_rotate = False
        if self.options.auto_rotate and (self.svg_height > self.svg_width):
            self.rotate_page = True
        return True

    def get_output(self):
        """Return serialized copy of svg document output"""
        result = etree.tostring(self.document)
        return result.decode("utf-8")

    def disconnect(self):
        '''End serial session; disconnect from AxiDraw '''
        if self.plot_status.port:
            ebb_serial.closePort(self.plot_status.port)
        self.plot_status.port = None
        self.connected = False  # Python interactive API variable

class SecondaryLoggingHandler(logging.Handler):
    '''To be used for logging to AxiDraw.text_out and AxiDraw.error_out.'''
    def __init__(self, axidraw, log_name, level = logging.NOTSET):
        super().__init__(level=level)

        log = getattr(axidraw, log_name) if hasattr(axidraw, log_name) else ""
        setattr(axidraw, log_name, log)

        self.axidraw = axidraw
        self.log_name = log_name

        self.setFormatter(logging.Formatter()) # pass message through unchanged

    def emit(self, record):
        assert(hasattr(self.axidraw, self.log_name))
        new_log = getattr(self.axidraw, self.log_name) + "\n" + self.format(record)
        setattr(self.axidraw, self.log_name, new_log)

class SecondaryErrorHandler(SecondaryLoggingHandler):
    '''Handle logging for "secondary" machines, plotting alongside primary.'''
    def __init__(self, axidraw):
        super().__init__(axidraw, 'error_out', logging.ERROR)

class SecondaryNonErrorHandler(SecondaryLoggingHandler):
    class ExceptErrorsFilter(logging.Filter):
        def filter(self, record):
            return record.levelno < logging.ERROR

    def __init__(self, axidraw):
        super().__init__(axidraw, 'text_out')
        self.addFilter(self.ExceptErrorsFilter())

if __name__ == '__main__':
    logging.basicConfig()
    e = AxiDraw()
    exit_status.run(e.affect)
