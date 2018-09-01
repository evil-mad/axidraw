# axidraw_control.py
# Part of the AxiDraw driver for Inkscape
# https://github.com/evil-mad/AxiDraw
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

import os
import sys
import time

import threading

# Handle a few potential locations of this and its required files
libpath = os.path.join('pyaxidraw', 'lib')
sys.path.append('pyaxidraw')
sys.path.append(libpath)
sys.path.append('lib')

import gettext

import inkex # Forked from Inkscape's extension framework (GPLv2)

import ebb_serial # Requires v 0.13 in plotink:	 https://github.com/evil-mad/plotink
import axidraw_conf # Some settings can be changed here.

try:
    from . import axidraw
except:
    import axidraw   # https://github.com/evil-mad/axidraw

use_multiprocessing = False

if use_multiprocessing:     
    import multiprocessing
    multiprocessing.freeze_support()
else:
    # Multiprocessing does not work on Windows; use multiple threads.
    import threading
    
class AxiDrawWrapperClass( inkex.Effect ):
    
    def __init__( self ):
        inkex.Effect.__init__( self )

        self.OptionParser.add_option("--mode",\
            action="store", type="string", dest="mode",\
            default="plot", \
            help="Mode or GUI tab. One of: [plot, layers, align, toggle, manual"\
            + ", sysinfo, version, res_plot, res_home]. Default: plot.")
            
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

        self.OptionParser.add_option("--pen_pos_up",\
            type="int", action="store", dest="pen_pos_up", \
            default=axidraw_conf.pen_pos_up, \
            help="Height of pen when raised (0-100)")

        self.OptionParser.add_option("--pen_pos_down",\
            type="int", action="store", dest="pen_pos_down",\
            default=axidraw_conf.pen_pos_down,\
            help="Height of pen when lowered (0-100)")
        
        self.OptionParser.add_option("--pen_rate_raise",\
            type="int", action="store", dest="pen_rate_raise",\
            default=axidraw_conf.pen_rate_raise,\
            help="Rate of raising pen (1-100)")
         
        self.OptionParser.add_option("--pen_rate_lower",\
            type="int", action="store", dest="pen_rate_lower",\
            default=axidraw_conf.pen_rate_lower, \
            help="Rate of lowering pen (1-100)")
        
        self.OptionParser.add_option("--pen_delay_up",\
            type="int", action="store", dest="pen_delay_up", \
            default=axidraw_conf.pen_delay_up,\
            help="Optional delay after pen is raised (ms)")
           
        self.OptionParser.add_option("--pen_delay_down",\
            type="int", action="store", dest="pen_delay_down",\
            default=axidraw_conf.pen_delay_down,\
            help="Optional delay after pen is lowered (ms)")
            
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
            default=None,\
            help="Port use code (0-3)."\
            +" 0: Plot to first unit found, unless port is specified"\
            + "1: Plot to first AxiDraw Found. "\
            + "2: Plot to specified AxiDraw. "\
            + "3: Plot to all AxiDraw units. ")

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



    def effect( self ):
        '''
        Main entry point
        '''

        self.verbose = False

        if self.options.mode == "options":
            return
        if self.options.mode == "timing":
            return
            
        self.start_time = time.time()
        self.options.mode = self.options.mode.strip("\"")
        
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
        
        
        if self.options.preview:
            self.options.port_config = 1 # Ignore port & multi-machine options in preview


        if self.options.mode in ( "resume", "res_plot", "res_home"):
            if self.options.port_config == 3: # If requested to use all machines,
                self.options.port_config = 1  # Instead, only resume for first machine.
                
        if self.options.port_config == 3: # Use all available AxiDraw units.
            process_list = []
            EBBList = []
            EBBList = ebb_serial.listEBBports()
            
            if EBBList:
                primary_port = None
                if self.options.port is not None:
                    primary_port = ebb_serial.find_named_ebb(self.options.port)
                    
                if self.verbose:
                    for foundPort in EBBList:
                        inkex.errormsg ("Found an EBB:")
                        inkex.errormsg (" Port name:   " + foundPort[0])	# Port name
                        inkex.errormsg (" Description: " + foundPort[1])	# Description
                        inkex.errormsg (" Hardware ID: " + foundPort[2])	# Hardware ID
                if len(EBBList) == 1:
                    if self.verbose:
                        inkex.errormsg ("Found a single AxiDraw via USB.")
                    self.plot_to_axidraw(None, True)
                else:
                    if primary_port is None:
                        primary_port = EBBList[0][0]
                
                    for index, foundPort in enumerate(EBBList):
                        if foundPort[0] == primary_port:
                            if self.verbose:
                                inkex.errormsg ("FoundPort is primary: " + primary_port)
                            continue # We will launch primary after spawning other processes.

                        # Launch subprocess(es) here:
                        if self.verbose:
                            inkex.errormsg ("Launching subprocess to port: " + foundPort[0])
                            
                        if use_multiprocessing:  
                            process = multiprocessing.Process(target=self.plot_to_axidraw, args=(foundPort[0],False))
                        else: # Use multithreading:
                            tname = "thread-" + str(index)
                            process = threading.Thread(group=None, target=self.plot_to_axidraw, name=tname, args=(foundPort[0],False))
                            
                        process_list.append(process)
                        process.start()
                        
                    if self.verbose:
                        inkex.errormsg ("Plotting to primary: " + primary_port)
                        
                    self.plot_to_axidraw(primary_port, True) # Plot to "primary" AxiDraw
                    for process in process_list:
                        if self.verbose:
                            inkex.errormsg ("Joining a process. ") 
                        process.join()
                        
            else: # i.e., if not EBBList
                inkex.errormsg ("No available axidraw units found on USB.")
                inkex.errormsg ("Please check your connection(s) and try again.")
                return
        else:   # All cases except plotting to all available AxiDraw units:
                # This includes: Preview mode and all cases of plotting to a single AxiDraw.
                
            # If we are to use first available unit, blank the "port" variable.
            if self.options.port_config == 1: # Use first available AxiDraw
                self.options.port = None
            self.plot_to_axidraw(self.options.port, True)


    def plot_to_axidraw( self, port, primary):

#         if primary:
#             pass
#         else:
#             inkex.errormsg('Skipping secondary. ' )
#             return # Skip secondary units, without opening class or serial connection

        ad = axidraw.AxiDraw()
        ad.getoptions([])

        if self.verbose:
            if primary:
                prim = " (primary)."
            else:
                prim = " (secondary)."
            inkex.errormsg('plot_to_axidraw started, at port ' + str(port) + prim)

        # Many plotting parameters to pass through:
        ad.options.mode             = self.options.mode
        ad.options.speed_pendown    = self.options.speed_pendown
        ad.options.speed_penup      = self.options.speed_penup
        ad.options.accel            = self.options.accel
        ad.options.pen_pos_up       = self.options.pen_pos_up
        ad.options.pen_pos_down     = self.options.pen_pos_down
        ad.options.pen_rate_raise   = self.options.pen_rate_raise
        ad.options.pen_rate_lower   = self.options.pen_rate_lower
        ad.options.pen_delay_up     = self.options.pen_delay_up
        ad.options.pen_delay_down   = self.options.pen_delay_down
        ad.options.no_rotate        = self.options.no_rotate
        ad.options.const_speed      = self.options.const_speed
        ad.options.report_time      = self.options.report_time
        ad.options.manual_cmd       = self.options.manual_cmd
        ad.options.walk_dist        = self.options.walk_dist
        ad.options.layer            = self.options.layer
        ad.options.copies           = self.options.copies
        ad.options.page_delay       = self.options.page_delay
        ad.options.preview          = self.options.preview
        ad.options.rendering        = self.options.rendering
        ad.options.model            = self.options.model
        ad.options.port             = port
        ad.options.setup_type       = self.options.setup_type
        ad.options.resume_type      = self.options.resume_type
        ad.options.auto_rotate      = self.options.auto_rotate
        ad.options.resolution       = self.options.resolution

        # Special case for this wrapper function:
        # If the port is None, change the port config option
        # to be "use first available AxiDraw":
        if port is None:
            ad.options.port_config = 1 # Use first available AxiDraw
        else:
            ad.options.port_config = 2 # Use AxiDraw specified by port
        
        ad.document = self.document 
        ad.original_document = self.document

        if not primary:
            ad.Secondary = True # Supress general message reporting
            ad.called_externally = True # Supress time reporting.

        # Plot the document using axidraw.py
        ad.effect()
        
        if primary:
            # Collect output from axidraw.py 
            self.document = ad.document
            self.outdoc =  ad.get_output()
        else:
            if ad.error_out:
                try:
                    the_name = ad.nameString
                except:
                    the_name = port
                if port is not None:
                    inkex.errormsg('Error on AxiDraw at port "' + port + '":' + ad.error_out)
                else:
                    inkex.errormsg('Error on secondary AxiDraw: ' + ad.error_out)
                inkex.errormsg(" ")

    def parseFile(self, input_file):
        self.parse(input_file) 

if __name__ == '__main__':
    e = AxiDrawWrapperClass()
    e.affect()
