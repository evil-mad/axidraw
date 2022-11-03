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
plot_status.py

Classes for managing AxiDraw plot status

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

"""

from tqdm import tqdm

# import time
from axidrawinternal.plot_utils_import import from_dependency_import
text_utils = from_dependency_import('plotink.text_utils')


# class SVGPlotData:  # pylint: disable=too-few-public-methods
#     """
#     PlotData: Class for data items stored in plotdata elements within the SVG file
#     Not in use yet
#
#     """
#
#     ITEM_NAMES = ['layer', 'node', 'last_path', 'node_after_path', 'last_known_x',
#                     'last_known_y', 'paused_x', 'paused_y', 'application',
#                     'plob_version', 'row', 'randseed']
#
#     def __init__(self):
#         for key in self.ITEM_NAMES: # Create instance variables in __init__
#             setattr(self, key, None)
#         self.reset() # Set defaults via reset function
#
#     def reset(self):
#         '''Set default values'''
#         for key in self.ITEM_NAMES: # Set all to 0 except those specified below.
#             setattr(self, key, 0)
#
#         self.svg_layer = -2
#         self.svg_rand_seed = 1
#         self.svg_application = None


# class PlotData:  # pylint: disable=too-few-public-methods
#     """
#     PlotData: Class for managing plotdata elements
#     Not in use yet
#
#     """
#
#     def __init__(self):
#         self.svg_data_read = False
#         self.svg_data_written = False
#         self.as_read = SVGPlotData()
#         self.new_data = SVGPlotData()


class PlotStats: # pylint: disable=too-few-public-methods
    """
    PlotStats: Statistics about this plot; not yet implemented
    """

    def __init__(self):
        self.up_travel_inch = 0 # Pen-up travel distance, inches
        self.down_travel_inch = 0 # Pen-down travel distance, inches
        self.pt_estimate = 0 # Plot time estimate, ms
        self.page_delays = 0 # Delays between pages, ms

    def reset(self):
        ''' Reset attributes to defaults '''
        self.up_travel_inch = 0
        self.down_travel_inch = 0
        self.pt_estimate = 0
        self.page_delays = 0


    def add_dist(self, pen_up, distance_inch):
        """ add_dist: Add distance of the current plot segment to total distances """
        if pen_up:
            self.up_travel_inch += distance_inch
        else:
            self.down_travel_inch += distance_inch

    def report(self, options, message_fun, elapsed_time):
        """ report: Format and print time and distance statistics """

        if not options.report_time:
            return

        d_dist = 0.0254 * self.down_travel_inch
        u_dist = 0.0254 * self.up_travel_inch
        t_dist = d_dist + u_dist # Total distance

        delay_text = ""
        elapsed_text = text_utils.format_hms(elapsed_time)
        if self.page_delays > 0:
            delay_text = ",\nincluding page delays of: " +\
                text_utils.format_hms(self.page_delays, True)

        if options.preview:
            message_fun("Estimated print time: " +\
                text_utils.format_hms(self.pt_estimate, True) + delay_text)
            message_fun(f"Length of path to draw: {d_dist:1.2f} m")
            message_fun(f"Pen-up travel distance: {u_dist:1.2f} m")
            message_fun(f"Total movement distance: {t_dist:1.2f} m")
            message_fun("This estimate took " + elapsed_text + "\n")
        else:
            message_fun("Elapsed time: " + elapsed_text + delay_text)
            message_fun(f"Length of path drawn: {d_dist:1.2f} m")
            message_fun(f"Total distance moved: {t_dist:1.2f} m\n")


class ProgressBar:
    """
    ProgressBar: Class to manage progress bar, currently used only by CLI API.
    """

    def __init__(self):
        self.p_bar = None # Reference to TQDM progress bar object; None if not in use.
        self.total = 0 # Total quantity, representing 100%.
        self.last = 0 # last quantity
        self.enable = False
        self.value_stash = [1, None] # copies, port

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
        self.value_stash = [options.copies, options.digest, status.port]

        # Make changes to configure for the dry run:
        options.preview = True
        options.copies = 1
        options.digest = 0 # Disable digest output
        status.copies_to_plot = 1
        status.port = None
        return True

    def restore(self, status, options):
        '''
        Restore stashed values after dry run. Return estimated time text.
        '''
        options.copies = self.value_stash[0]
        options.digest = self.value_stash[1]
        status.port = self.value_stash[2]
        options.preview = False # Progress bars only run when preview is False.

        # Report estimated print time:
        time_txt = "Estimated print time: " +\
            text_utils.format_hms(status.stats.pt_estimate, True)
        if options.copies == 1:
            return time_txt
        return time_txt +\
            f" per copy, with {options.page_delay} s between copies."


    def launch(self, status, options, delay=False, total_in=None):
        '''
        Launch the progress bar, if enabled. Customize the description
        to indicate which page is being printed.
        The "delay" argument changes the legend text to indicate that
        it's a delay between plots.
        If "total" is None (or left off), use the "backup total" value.
        '''
        if not self.enable:
            return

        self.last = 0

        if total_in is None:
            total_val = self.total
        else:
            total_val = total_in
        if options.copies == 1:
            description='Plot Progress'
        elif options.copies == 0: # continuous plotting
            the_page = -1 * status.copies_to_plot - 1
            if delay:
                description=f'Page delay {the_page}'
            else:
                description=f'Copy number {the_page}'
        else:
            the_page = options.copies - status.copies_to_plot
            if delay:
                description=f'Page delay {the_page} of {options.copies - 1}'
            else:
                description=f'Copy {the_page} of {options.copies}'

        self.p_bar = tqdm(total=total_val, mininterval=0.5, delay=0.5,
            desc=description, initial=0, leave=False, unit=" Nodes", ascii=True)

    def update(self, new_count):
        '''
        Given the new absolute count, update the progress bar with the change since the
        last update. Save the new count as the last one.
        '''
        if self.p_bar is not None:
            value = new_count - self.last
            self.p_bar.update(value)
            self.last = new_count

    def update_rel(self, value):
        '''
        Add an amount to the progress shown on the progress bar
        '''
        if self.p_bar is not None:
            self.p_bar.update(value)

    def close(self):
        '''
        Close the progress bar, if enabled
        '''
        if self.p_bar is not None:
            self.p_bar.close()


class ResumeStatus: # pylint: disable=too-few-public-methods
    """
    ResumeStatus: Data storage class for managing status while preparing to resume a plot
    Some attributes not in use yet
    """

    def __init__(self):
        # self.node_count = 0
        # self.node_target = 0
        self.resume_mode = False
        # self.pathcount = 0

    def reset(self):
        ''' Reset attributes to defaults '''
        # self.node_count = 0
        # self.node_target = 0
        self.resume_mode = False
        # self.pathcount = 0


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
        self.resume.reset() # Not yet in use
