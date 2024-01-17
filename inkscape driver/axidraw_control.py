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
axidraw_control.py

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

Requires Python 3.7 or newer
"""

from importlib import import_module
import logging
# import threading
import time
import signal
from threading import Event

from axidrawinternal import axidraw   # https://github.com/evil-mad/axidraw
from axidrawinternal.axidraw_options import common_options

from axidrawinternal.plot_utils_import import from_dependency_import # plotink
inkex = from_dependency_import('ink_extensions.inkex')
exit_status = from_dependency_import('ink_extensions_utils.exit_status')
message = from_dependency_import('ink_extensions_utils.message')
ebb_serial = from_dependency_import('plotink.ebb_serial') # https://github.com/evil-mad/plotink

USE_MULTIPROCESSING = False

if USE_MULTIPROCESSING:
    import multiprocessing
    multiprocessing.freeze_support()
else:
    # Multiprocessing does not work on Windows; use multiple threads.
    import threading

logger = logging.getLogger(__name__)

class AxiDrawWrapperClass( inkex.Effect ):
    """ Main wrapper class for operating multiple AxiDraw units """

    default_handler = message.UserMessageHandler()

    def __init__( self, default_logging = True, params = None ):
        if params is None:
            # use default configuration file
            params = import_module("axidrawinternal.axidraw_conf") # Configuration file
        self.params = params
        self.status_code = 0

        # certain options are common to many extensions in this library
        core_axidraw_options = common_options.core_axidraw_options(params.__dict__)
        inkex.Effect.__init__(self, common_options = [core_axidraw_options])

        self.default_logging = default_logging
        if default_logging:
            logger.addHandler(self.default_handler)

        self.set_up_pause_transmitter()

    def set_up_pause_transmitter(self):
        """ intercept ctrl-C (keyboard interrupt) and redefine as "pause" command """
        signal.signal(signal.SIGINT, self.transmit_pause_request)
        # one pause event for all axidraws
        self.software_initiated_pause_event = Event()

    def transmit_pause_request(self, *args):
        """ Transmit a software-requested pause event """
        self.software_initiated_pause_event.set()

    def effect( self ):
        '''
        Main entry point
        '''
        self.start_time = time.time()
        self.options.mode = self.options.mode.strip("\"")
        self.verbose = False

        if self.verbose:
            logger.setLevel(logging.INFO) # default is generally logging.WARNING

        if self.options.mode == "options" and self.options.submode=="sysinfo":
            self.options.mode = "sysinfo"

        if self.options.mode == "options":
            if self.params.options_message:
                logger.error("Use the Plot or Layers tab to start a new "+
                            "plot or plot preview.\n\n" +
                            "  Configuration changes are applied automatically;\n" +
                            '  Pressing "Apply" on this tab has no effect other\n' +
                            "  than displaying this message.")
            return
        '''
        USB port use option (self.options.port_config)

            Allowed values:

            0: Default behavior:
                * Use only the specified port ( self.options.port ) if given
                * If no port is specified, use the first available AxiDraw

            1: Use first AxiDraw located via USB, even if a port is given.
    
            2: Use only specified port, given by self.options.port

            3: Plot to all attached AxiDraw units
        '''

        if self.options.preview or self.options.digest > 1:
            self.options.port_config = 1 # Offline modes; Ignore port & multi-machine options

        if self.options.mode in ( "resume", "res_plot", "res_home"):
            if self.options.port_config == 3: # If requested to use all machines,
                self.options.port_config = 1  # Instead, only resume for first machine.

        if self.options.port_config == 3: # Use all available AxiDraw units.
            process_list = []
            ebb_list = []
            ebb_list = ebb_serial.listEBBports()

            if ebb_list:
                primary_port = None
                if self.options.port is not None:
                    primary_port = ebb_serial.find_named_ebb(self.options.port)

                for found_port in ebb_list:
                    logger.info("Found an EBB:")
                    logger.info(" Port name:   " + found_port[0])	# Port name
                    logger.info(" Description: " + found_port[1])	# Description
                    logger.info(" Hardware ID: " + found_port[2])	# Hardware ID
                if len(ebb_list) == 1:
                    logger.info("Found a single AxiDraw via USB.")
                    self.plot_to_axidraw(None, True)
                else:
                    if primary_port is None:
                        primary_port = ebb_list[0][0]
                    for index, found_port in enumerate(ebb_list):
                        if found_port[0] == primary_port:
                            logger.info("found_port is primary: " + primary_port)
                            continue # We will launch primary after spawning other processes.

                        # Launch subprocess(es) here:
                        logger.info("Launching subprocess to port: " + found_port[0])

                        if USE_MULTIPROCESSING:
                            process = multiprocessing.Process(target=self.plot_to_axidraw,
                                args=(found_port[0],False))
                        else: # Use multithreading:
                            tname = "thread-" + str(index)
                            process = threading.Thread(group=None, target=self.plot_to_axidraw,
                                name=tname, args=(found_port[0],False))
                        process_list.append(process)
                        process.start()

                    logger.info("Plotting to primary: " + primary_port)

                    self.plot_to_axidraw(primary_port, True) # Plot to "primary" AxiDraw
                    for process in process_list:
                        logger.info("Joining a process. ")
                        process.join()
            else: # i.e., if not ebb_list
                logger.error("No available axidraw units found on USB.")
                logger.error("Please check your connection(s) and try again.")
                return
        else:   # All cases except plotting to all available AxiDraw units:
                # This includes: Preview mode and all cases of plotting to a single AxiDraw.

            # If we are to use first available unit, blank the "port" variable.
            if self.options.port_config == 1: # Use first available AxiDraw
                self.options.port = None
            self.plot_to_axidraw(self.options.port, True)

    def plot_to_axidraw( self, port, primary):
        """ Delegate the plot to a particular AxiDraw """
#         if primary:
#             pass
#         else:
#             inkex.errormsg('Skipping secondary. ' )
#             return # Skip secondary units, without opening class or serial connection

        ad = axidraw.AxiDraw(params=self.params, default_logging=self.default_logging)
        ad.set_up_pause_receiver(self.software_initiated_pause_event)

        prim = "primary" if primary else "secondary"
        logger.info("plot_to_axidraw started, at port %s (%s)", port, prim)

        if not hasattr(self.options, 'progress'): # CLI only option; not part of regular options.
            self.options.progress = False

        # Many plotting parameters to pass through:

        selected_options = {item: self.options.__dict__[item] for item in ['mode',
            'speed_pendown', 'speed_penup',  'accel', 'pen_pos_up', 'pen_pos_down',
            'pen_rate_raise', 'pen_rate_lower', 'pen_delay_up', 'pen_delay_down',
            'no_rotate', 'const_speed', 'report_time', 'manual_cmd', 'dist',
            'layer', 'copies', 'page_delay', 'preview', 'rendering', 'model', 'penlift',
            'setup_type', 'resume_type', 'auto_rotate', 'resolution', 'hiding', 'reordering',
            'random_start', 'webhook', 'webhook_url', 'digest', 'progress',]}
        ad.options.__dict__.update(selected_options)

        ad.options.port = port

        # Special case for this wrapper function:
        # If the port is None, change the port config option
        # to be "use first available AxiDraw":
        if port is None:
            ad.options.port_config = 1 # Use first available AxiDraw
        else:
            ad.options.port_config = 2 # Use AxiDraw specified by port

        ad.document = self.document
        ad.original_document = self.document

        if hasattr(self, 'cli_api'):
            ad.plot_status.cli_api = True # Set flag that software called by API

        if not primary:
            ad.set_secondary() # Suppress general message reporting; suppress time reporting

        ad.effect() # Plot the document using axidraw.py

        if primary:
            self.document = ad.document
            self.outdoc =  ad.get_output() # Collect output from axidraw.py
            self.status_code = ad.plot_status.stopped
        else:
            if ad.error_out:
                if port is not None:
                    logger.error('Error on AxiDraw at port "' + port + '":' + ad.error_out)
                else:
                    logger.error('Error on secondary AxiDraw: ' + ad.error_out)

    def parseFile(self, input_file):
        self.parse(input_file)

if __name__ == '__main__':
    e = AxiDrawWrapperClass()
    exit_status.run(e.affect)
