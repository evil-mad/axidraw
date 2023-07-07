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
plot_status.py

Classes for managing AxiDraw plot status

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

"""

import math
import time
from tqdm import tqdm
from lxml import etree

from axidrawinternal.plot_utils_import import from_dependency_import
text_utils = from_dependency_import('plotink.text_utils')
inkex = from_dependency_import('ink_extensions.inkex')
ebb_motion = from_dependency_import('plotink.ebb_motion')


class SVGPlotData:  # pylint: disable=too-few-public-methods, too-many-instance-attributes
    """
    PlotData: Storage class for data items in plotdata elements within the SVG file
    """

    def __init__(self):
        self.layer = None
        self.pause_dist = None
        self.pause_ref = None
        self.plob_version = None
        self.row = None
        self.rand_seed = None
        self.last_x = None
        self.last_y = None
        self.model = None
        self.application = None
        self.reset() # Set defaults

    def reset(self):
        """ Set or Reset instance attributes to defaults """
        self.layer = -2         # <0 is a flag to *print all layers; -2 indicates default
        self.pause_dist = -1    # <0 is a flag that there is no resume data.
        self.pause_ref = -1    # <0 is a flag that there is no resume data.
        self.plob_version = "n/a"
        self.row = 0
        self.rand_seed = 1
        self.last_x = 0
        self.last_y = 0
        self.model = 0
        self.application = ""

    def clean(self):
        """ Clean up settings when a plot finishes normally; indicate no resume needed """
        self.layer = -2         # <0 is a flag to *print all layers; -2 indicates default
        self.pause_dist = -1    # <0 is a flag that there is no resume data.



class ResumeStatus:
    """
    ResumeStatus: Class for managing status items related to pausing
        and resuming plots, including managing plot data stored in SVG file
    """

    def __init__(self):
        self.read = False       # Boolean: Data has been read from SVG file
        self.written = False    # Boolean: Data written to SVG file
        self.old = SVGPlotData()
        self.new = SVGPlotData()
        self.update_needed = False  # If true, we need to update data in the SVG file
        self.button_timestamp = 0   # Timestamp for last button check
        self.reset() # Set defaults via reset function

    def reset(self):
        '''Set default values'''
        self.read = False       # Boolean: Data has been read from SVG file
        self.written = False    # Boolean: Data written to SVG file
        self.update_needed = False  # If true, we need to update data in the SVG file
        self.button_timestamp = time.time()   # Timestamp for last button check
        self.old.reset()
        self.new.reset()

    def read_from_svg(self, svg_tree):
        """
        Read plot progress data, stored in a custom "plotdata" XML element
        last_x, y stored as float with mm units, but used as inch units within the software.
        pause_dist, pause_ref stored in file as integer with µm units but used as inch units.
        """
        self.read = False
        data_node = None
        nodes = svg_tree.xpath("//*[self::svg:plotdata|self::plotdata]", namespaces=inkex.NSS)
        if nodes:
            data_node = nodes[0]
        if data_node is not None:
            try: # Core data required for resuming plots
                self.old.layer = int(data_node.get('layer'))
                self.old.pause_dist = int(data_node.get('pause_dist')) / 25400
                self.old.pause_ref = int(data_node.get('pause_ref')) / 25400
                self.old.plob_version = data_node.get('plob_version')
                if self.old.plob_version is None:
                    self.old.plob_version = "n/a"
                self.old.row = int(data_node.get('row'))
                self.old.rand_seed = int(float(data_node.get('rand_seed')))
                self.old.last_x = float(data_node.get('last_x')) / 25.4
                self.old.last_y = float(data_node.get('last_y')) / 25.4
                self.old.model = int(data_node.get('model'))
                self.old.application = data_node.get('application')
                self.read = True
            except TypeError: # An error leaves self.read as False.
                svg_tree.remove(data_node) # Remove data node

    def write_to_svg(self, svg_tree):
        """
        Write plot progress data, stored in a custom "plotdata" XML element
        last_x, y stored as float with mm units.
        pause_dist, pause_ref stored as integer with µm units
        """
        if not self.written:
            for node in svg_tree.xpath("//*[self::svg:plotdata|self::plotdata]",\
                namespaces=inkex.NSS):
                node_parent = node.getparent()
                node_parent.remove(node)
            data_node = etree.SubElement(svg_tree, 'plotdata')

            if self.new.application == "":
                self.new.application = "axidraw"  # Name of this program
            data_node.set('application', self.new.application)
            data_node.set('model', str(self.new.model))
            data_node.set('plob_version', str(self.new.plob_version ))
            data_node.set('layer', str(self.new.layer))
            data_node.set('pause_dist', f"{round(self.new.pause_dist * 25400)}") # units µm
            data_node.set('pause_ref',  f"{round(self.new.pause_ref * 25400)}") # units µm
            data_node.set('last_x', f"{self.new.last_x * 25.4}") # float; units mm
            data_node.set('last_y', f"{self.new.last_y * 25.4}") # float; units mm
            data_node.set('rand_seed', f"{self.new.rand_seed}")
            data_node.set('row', f"{self.new.row}")
            self.written = True

    def copy_old(self):
        """ Copy old attributes to new """
        self.new.layer = self.old.layer
        self.new.pause_dist = self.old.pause_dist
        self.new.pause_ref = self.old.pause_ref
        self.new.plob_version = self.old.plob_version
        self.new.row = self.old.row
        self.new.rand_seed = self.old.rand_seed
        self.new.last_x = self.old.last_x
        self.new.last_y = self.old.last_y
        self.new.model = self.old.model
        self.new.application = self.old.application

    def check_button(self, ad_ref):
        """
        Check for button press, if not preview, and not too soon after last check.
        Return: 1 if button pressed, 0 if not (or if we did not check), and -1 in case of error.
        """

        # Uncomment next two lines to force a pause at a specific position
        # if ad_ref.options.mode == "plot" and ad_ref.plot_status.stats.down_travel_inch > 6.0:
        #     return 1

        if ad_ref.options.preview:
            return 0

        time_now = time.time()
        if (time_now - self.button_timestamp) > ad_ref.params.button_interval:
            self.button_timestamp = time_now
            str_button = ebb_motion.QueryPRGButton(ad_ref.plot_status.port, False)
        else:
            return 0

        try:
            pause_button_pressed = int(str_button[0])
        except (IndexError, ValueError): # Generally indicates loss of connection to AxiDraw
            return -1
        return pause_button_pressed

    def clear_button(self, ad_ref):
        """ Query if button pressed, to clear the result and reset timestamp """
        if ad_ref.options.preview:
            return
        self.button_timestamp =  time.time()
        ebb_motion.QueryPRGButton(ad_ref.plot_status.port, False)

    def manage_offset(self, ad_ref):
        """ Read and optionally update pause point in the SVG file """
        self.read_from_svg(ad_ref.svg)
        self.copy_old()

        original_dist_inch = f"{max(self.old.pause_ref, 0):.3f} inches"
        updated_dist_inch =  f"{max(self.old.pause_dist, 0):.3f} inches"
        original_dist_mm = f"{max(self.old.pause_ref, 0) * 25.4 :.3f} mm"
        updated_dist_mm =  f"{max(self.old.pause_dist, 0)* 25.4 :.3f} mm"

        if ad_ref.options.manual_cmd == "res_adj_in":
            original_dist_text = original_dist_inch
            updated_dist_text = updated_dist_inch
            adjustment_text = f"{ad_ref.options.dist:.3f} inches"
            new_pause_dist = ad_ref.options.dist + max(self.old.pause_dist, 0)

            new_pos_text =  f"{new_pause_dist:.3f} inches"
            if new_pause_dist <= 0:
                new_pause_dist = -1
                new_pos_text = "the file beginning"
            self.new.pause_dist = new_pause_dist

        elif ad_ref.options.manual_cmd == "res_adj_mm":
            original_dist_text = original_dist_mm
            updated_dist_text = updated_dist_mm
            adjustment_text = f"{ad_ref.options.dist:.3f} mm"
            new_pause_dist = ad_ref.options.dist / 25.4 + max(self.old.pause_dist, 0)

            new_pos_text =  f"{new_pause_dist * 25.4:.3f} mm"
            if new_pause_dist <= 0:
                new_pause_dist = -1
                new_pos_text = "the file beginning"
            self.new.pause_dist = new_pause_dist

        else: # res_read = "res_read" Dual units and readout only.
            if self.old.pause_dist < 0:
                return "No in-progress plot data found in file.\n"+\
                        "To set up the plot to be resumed at a given point, add an offset."
            original_dist_text = original_dist_mm + " (" + original_dist_inch + ")"
            updated_dist_text = updated_dist_mm + " (" + updated_dist_inch + ")"

        if (self.old.pause_dist < 0) and (self.old.pause_ref < 0):
            return_text = "This document was configured to start plotting"+\
                            " at the beginning of the file.\n"
        elif self.old.pause_ref < 0:
            return_text = "This document was originally configured to start plotting at the "+\
                    "beginning of the file.\nThe resume position was then adjusted to " +\
                    updated_dist_text + ".\n"
        elif self.old.pause_dist == self.old.pause_ref:
            return_text = "Plot was paused after " + original_dist_text + " of pen-down travel.\n"
        else:
            return_text = "Plot was originally paused after " + original_dist_text +\
                    " of pen-down travel. The resume position was then adjusted to " +\
                    updated_dist_text + ".\n"

        if ad_ref.options.manual_cmd in ("res_adj_in", "res_adj_mm"):
            return_text += "After adding a new offset of " + adjustment_text +\
                ", the resume position is now set at " + new_pos_text + ".\n"
            self.write_to_svg(ad_ref.svg)

        return return_text


class PlotStats:
    """ PlotStats: Statistics about this plot"""

    def __init__(self):
        self.up_travel_inch = 0     # Pen-up travel distance on current page, inches
        self.down_travel_inch = 0   # Pen-down travel distance on current page, inches
        self.up_travel_tot = 0      # Total pen-up travel distance, inches
        self.down_travel_tot = 0    # Total pen-down travel distance, inches
        self.pt_estimate = 0        # Plot time estimate (for all pages), ms
        self.page_delays = 0        # Delays between pages, ms
        self.layer_delays = 0       # Delays added at beginnings of layers, ms

    def reset(self):
        ''' Reset certain attributes to defaults '''
        self.up_travel_inch = 0
        self.down_travel_inch = 0
        self.up_travel_tot = 0
        self.down_travel_tot = 0
        self.pt_estimate = 0
        self.page_delays = 0
        self.layer_delays = 0

    def next_page(self):
        ''' Zero out distance traveled for the new page '''
        self.up_travel_tot += self.up_travel_inch
        self.down_travel_tot += self.down_travel_inch
        self.up_travel_inch = 0
        self.down_travel_inch = 0

    def add_dist(self, pen_up, distance_inch):
        """ add_dist: Add distance of the current plot segment to total distances """
        if pen_up:
            self.up_travel_inch += distance_inch
        else:
            self.down_travel_inch += distance_inch

    def report(self, options, message_fun, elapsed_time):
        """ report: Format and print time and distance statistics """

        self.up_travel_tot += self.up_travel_inch
        self.down_travel_tot += self.down_travel_inch

        if (options.copies > 1) and options.preview and not options.random_start:
            # Special case: When not randomizing, each page has identical print time.
            #   ->Estimate print time for a single page and multiply; it's much faster.
            self.down_travel_tot = options.copies * self.down_travel_inch
            self.up_travel_tot = options.copies * self.up_travel_inch
            self.page_delays = 1000 * options.page_delay * (options.copies - 1)
            self.layer_delays *= options.copies
            self.pt_estimate *= options.copies
            self.pt_estimate += self.page_delays

        if not options.report_time: # Portion above this necessary for time computations.
            return

        d_dist = 0.0254 * self.down_travel_tot
        u_dist = 0.0254 * self.up_travel_tot
        t_dist = d_dist + u_dist # Total distance

        delay_text = ""
        elapsed_text = text_utils.format_hms(elapsed_time)

        if self.layer_delays > 0:
            delay_text = ",\nincluding added delays of: " +\
                text_utils.format_hms(self.page_delays + self.layer_delays, True) # Argument is ms
        elif self.page_delays > 0:
            delay_text = ",\nincluding page delays of: " +\
                text_utils.format_hms(self.page_delays, True) # Argument is ms

        if options.preview:
            message_fun("Estimated print time: " +\
                text_utils.format_hms(self.pt_estimate, True) + delay_text)
            message_fun(f"Length of path to draw: {d_dist:1.3f} m")
            message_fun(f"Pen-up travel distance: {u_dist:1.3f} m")
            message_fun(f"Total movement distance: {t_dist:1.3f} m")
            message_fun("This estimate took " + elapsed_text + "\n")
        else:
            message_fun("Elapsed time: " + elapsed_text + delay_text)
            message_fun(f"Length of path drawn: {d_dist:1.2f} m")
            message_fun(f"Total distance moved: {t_dist:1.2f} m\n")
        # message_fun(f"Elapsed time: {elapsed_time}") # When more digits are needed


class ProgressBar:
    """
    ProgressBar: Class to manage progress bar, currently used only by CLI API.
    """

    def __init__(self):
        self.p_bar = None # Reference to TQDM progress bar object; None if not in use.
        self.sub_bar = None # Reference to TQDM progress bar object; None if not in use.
        self.total = 0 # Total quantity, representing 100%, for main progress bar
        self.last = 0 # last quantity, for main progress bar
        self.enable = False
        self.dry_run = False    # Flag that dry run is currently taking place
        self.value_stash = [1, 0, None, 1] # copies, digest, port, copies_left

    def review(self, status, options):
        '''
        Check configuration to see if the progress bar can be enabled.
        If so, stash and change values necessary for the dry run.
        '''

        if not status.cli_api:
            return False
        if not options.progress:
            return False
        if options.preview or options.digest > 1:
            return False
        if options.mode not in [None, "plot", "layers", "res_plot"]:
            return False
        self.enable = True
        self.value_stash = [options.copies, options.digest, status.port, status.copies_to_plot]

        # Make changes to configure for the dry run:
        self.dry_run = True # Flag that this is a dry run; skip programmatic pauses
        options.preview = True
        options.rendering = 0 # Turn off rendering
        options.copies = 1
        status.copies_to_plot = 1
        options.digest = 0 # Disable digest output
        status.port = None
        return True

    def restore(self, ad_ref):
        ''' Restore stashed values after dry run. Return estimated time text.  '''
        self.dry_run = False
        ad_ref.options.copies = self.value_stash[0]
        ad_ref.options.digest = self.value_stash[1]
        ad_ref.plot_status.port = self.value_stash[2]
        ad_ref.plot_status.copies_to_plot = self.value_stash[3]
        ad_ref.options.preview = False # Progress bars only run when preview is False.

        # Total distance for progress bar; Progress units are mm
        total = ad_ref.plot_status.stats.down_travel_inch +\
                ad_ref.plot_status.stats.up_travel_inch # Use values from dry run:

        if ad_ref.options.mode == "res_plot": # Set up progress bar to show resume position.
            total += ad_ref.plot_status.resume.old.pause_dist
            self.last = math.floor(25.4 *  ad_ref.plot_status.resume.old.pause_dist)
        else:
            self.last = 0

        self.total = math.ceil(25.4 * total)

        # Report estimated print time:
        if ad_ref.options.copies > 1:
            total_print_time = ad_ref.plot_status.stats.pt_estimate * ad_ref.options.copies +\
                (ad_ref.options.copies - 1) * 1000 * ad_ref.options.page_delay
        else:
            total_print_time = ad_ref.plot_status.stats.pt_estimate
        time_txt = "Estimated print time: " +\
            text_utils.format_hms(total_print_time, True)

        if ad_ref.options.copies == 1:
            return time_txt
        if ad_ref.options.copies == 0: # Continuous printing
            return time_txt +\
                f" per copy, with {ad_ref.options.page_delay} s between copies."

        page_delays_s = (ad_ref.options.copies - 1) * ad_ref.options.page_delay
        return time_txt + f", including {page_delays_s} s of page delays between copies."


    def launch(self, ad_ref):
        '''
        Launch the main progress bar, if enabled. Customize the description
        to indicate which page is being printed.
        '''
        if not self.enable:
            return

        total_val = math.ceil(self.total)
        if ad_ref.options.copies == 1:
            description='Plot Progress'
        elif ad_ref.options.copies == 0: # continuous plotting
            the_page = -1 * ad_ref.plot_status.copies_to_plot - 1
            description=f'Copy number {the_page}'
        else:
            the_page = ad_ref.options.copies - ad_ref.plot_status.copies_to_plot
            description=f'Copy {the_page} of {ad_ref.options.copies}'

        self.p_bar = tqdm(total=total_val, mininterval=0.5, delay=0.5, position=0,
            desc=description, initial=math.floor(self.last), leave=False, unit=" mm", ascii=True)


    def launch_sub(self, ad_ref, total_in, page=True):
        ''' Launch "delay time" sub-progress bar, customized for the delay '''

        if not self.enable:
            return # If main bar is not enabled
        if total_in < 1000:
            return # Don't launch for < 1 s.

        total_val = math.ceil(total_in)
        if page:
            the_position = 0
            if ad_ref.options.copies == 0: # continuous plotting
                the_page = -1 * ad_ref.plot_status.copies_to_plot - 1
                description=f'Page delay {the_page}'
            else:
                the_page = ad_ref.options.copies - ad_ref.plot_status.copies_to_plot
                description=f'Page delay {the_page} of {ad_ref.options.copies - 1}'
        else: # A *layer* delay
            the_position = 1
            description='Layer delay'

        delay_total_s = f"of {round(total_in / 1000)} s"
        self.sub_bar = tqdm(total=total_val, mininterval=0.5, delay=0.5, position=the_position,
            desc=description, initial=0, leave=False, unit=delay_total_s, ascii=True,
            bar_format = "{desc}: {percentage:3.0f}%|{bar}|  [{elapsed_s:.1f} {unit}]")

    def update_sub_rel(self, update_amount):
        ''' Add an integer amount to the progress shown on the sub-progress bar. '''
        if self.sub_bar is None:
            return
        self.sub_bar.update(update_amount)

    def update_auto(self, status_ref):
        ''' Update the main progress bar with current travel distance '''
        if self.p_bar is None:
            return

        new_dist = 25.4 * (status_ref.down_travel_inch + status_ref.up_travel_inch)
        old_value_int = math.floor(self.last)
        new_value_int = math.floor(new_dist)
        update_amount = new_value_int - old_value_int
        self.last = new_dist
        if update_amount >= 1:
            self.p_bar.update(update_amount)

    def close(self):
        ''' Close main progress bar, if enabled '''
        self.last = 0 # Reset for future use.
        if self.p_bar is not None:
            self.p_bar.close()

    def close_sub(self):
        ''' Close sub- progress bar, if enabled '''
        if self.sub_bar is not None:
            self.sub_bar.close()

class PlotStatus:
    """
    PlotStatus: Data storage class for plot status variables
    """

    CONFIG_ITEMS = ['secondary', 'called_externally', 'cli_api', 'delay_between_copies']
    VERSION_ITEMS = ['fw_version']


    def __init__(self):
        self.port = None
        self.copies_to_plot = 1
        self.stopped = 0 # Status code. If a plot is stopped, record why.
        for key in self.CONFIG_ITEMS: # Create instance variables in __init__
            setattr(self, key, False)
        for key in self.VERSION_ITEMS: # Create instance variables in __init__
            setattr(self, key, None)
        self.apply_defaults() # Apply default values of the above attributes
        self.resume = ResumeStatus()
        self.progress = ProgressBar()
        self.stats = PlotStats()

    def apply_defaults(self):
        ''' Reset attributes to defaults '''
        self.port = None
        self.stopped = 0 # Default value 0 ("not stopped")
        self.delay_between_copies = False

    def reset(self):
        ''' Reset attributes and resume attributes to defaults '''
        self.apply_defaults()
        self.resume.reset()
