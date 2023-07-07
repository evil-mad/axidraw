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
dripfeed.py

Manage, or simulate, the process of feeding individual motion segments to the AxiDraw

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

Requires Python 3.7 or newer.

"""

import logging
import time

from axidrawinternal.plot_utils_import import from_dependency_import # plotink
ebb_serial = from_dependency_import('plotink.ebb_serial')  # https://github.com/evil-mad/plotink
ebb_motion = from_dependency_import('plotink.ebb_motion')
plot_utils = from_dependency_import('plotink.plot_utils')

def feed(ad_ref, move_list):
    """
    Feed individual motion actions to the AxiDraw during a plot or preview.
    Take care of housekeeping while doing so, including:
        Checking for pause inputs
        Skipping physical moves while in preview mode
        Skipping physical moves while resuming plots
        Updating previews
        Updating node counts
        Updating CLI progress bar
        Keeping track of total distance traveled, pen-up and pen-down
        Sleeping during long moves
        Reporting errors to the user
    Inputs: AxiDraw reference object, list of movement commands
    """

    if move_list is None:
        return

    spew_dripfeed_debug_data = False # Set True to get entirely too much debugging data

    drip_logger = logging.getLogger('.'.join([__name__, 'dripfeed']))
    if spew_dripfeed_debug_data:
        drip_logger.setLevel(logging.DEBUG) # by default level is INFO

    # drip_logger.debug('\ndripfeed.feed()\n')
    # drip_logger.debug('move_list:\n' + str(move_list)) # Can print full move list

    for move in move_list:
        ad_ref.pause_check()

        if ad_ref.plot_status.stopped:
            ad_ref.plot_status.copies_to_plot = 0
            return
        if ad_ref.pen.phys.xpos is None:
            return # Physical location is not well-defined; stop here.

        if move[0] == 'lower':
            ad_ref.pen.pen_lower(ad_ref)
            continue

        if move[0] == 'raise':
            ad_ref.pen.pen_raise(ad_ref)
            continue

        if move[0] == 'SM':
            feed_sm(ad_ref, move, drip_logger)
            continue


def feed_sm(ad_ref, move, drip_logger):
    """
    Manage the process of sending a single "SM" move command to the AxiDraw,
        and simulate doing so when in preview mode.
    Take care of housekeeping while doing so, including:
        Skipping physical moves while in preview mode
        Updating previews
        Updating progress bar (CLI)
        Keeping track of total distance traveled, pen-up and pen-down
        Sleeping during long moves
        Reporting errors to the user
    """

    # drip_logger.debug('\ndripfeed.feed_SM()\n')

    # 'SM' move is formatted as:
    # ['SM', (move_steps2, move_steps1, move_time), seg_data]
    # where seg_data begins with:
    #   * final x position, float
    #   * final y position, float
    #   * final pen_up state, boolean
    #   * travel distance (inch)

    move_steps2 = move[1][0]
    move_steps1 = move[1][1]
    move_time = move[1][2]
    f_new_x = move[2][0]
    f_new_y = move[2][1]
    move_dist = move[2][3]

    if ad_ref.options.preview:
        ad_ref.plot_status.stats.pt_estimate += move_time
        # log_sm_for_preview(ad_ref, move)

        ad_ref.preview.log_sm_move(ad_ref, move)

    else:
        ebb_motion.doXYMove(ad_ref.plot_status.port, move_steps2, move_steps1,\
            move_time, False)

        if move_time > 50: # Sleep before issuing next command
            if ad_ref.options.mode != "manual":
                time.sleep(float(move_time - 30) / 1000.0)
    # drip_logger.debug('XY move: (%s, %s), in %s ms', move_steps1, move_steps2, move_time)
    # drip_logger.debug('fNew(X,Y): (%.5f, %.5f)', f_new_x, f_new_y)

    ad_ref.plot_status.stats.add_dist(ad_ref.pen.phys.z_up, move_dist) # Distance; inches
    ad_ref.plot_status.progress.update_auto(ad_ref.plot_status.stats)

    ad_ref.pen.phys.xpos = f_new_x  # Update current position
    ad_ref.pen.phys.ypos = f_new_y


def page_layer_delay(ad_ref, between_pages=True, delay_ms=None):
    """
    Execute page delay or layer delay, monitoring for pause signals.
    Set between_pages=True for page delays, false for layer delays.
    delay_ms is only used for layer delays.
    """

    if ad_ref.plot_status.stopped:
        return # No delay if stopped.

    if between_pages:
        if ad_ref.plot_status.copies_to_plot == 0:
            return # No delay after last copy, for page delays.
        ad_ref.plot_status.delay_between_copies = True # Set flag: Delaying between copies
        delay_ms = ad_ref.options.page_delay * 1000

    if not delay_ms: # If delay time is 0 or None, exit.
        return
    if delay_ms >= 1000: # Only launch progress bar for at least 1 s of delay time
        ad_ref.plot_status.progress.launch_sub(ad_ref,
            delay_ms, page=between_pages)

    # Number of rest intervals:
    sleep_interval = 100 # Time period to sleep, ms. Default: 100
    time_remaining = delay_ms

    while time_remaining > 0:
        if ad_ref.plot_status.stopped:
            break # Exit loop if stopped.
        if time_remaining < 150: # If less than 150 ms left to delay,
            sleep_interval = time_remaining     # do it all at once.

        if between_pages:
            ad_ref.plot_status.stats.page_delays += sleep_interval
        else:
            ad_ref.plot_status.stats.layer_delays += sleep_interval

        if ad_ref.options.preview:
            ad_ref.plot_status.stats.pt_estimate += sleep_interval
        else:
            time.sleep(sleep_interval / 1000) # Use short intervals for responsiveness
            ad_ref.plot_status.progress.update_sub_rel(sleep_interval) # update progress bar
            ad_ref.pause_check() # Detect button press while between plots
        time_remaining -= sleep_interval
    ad_ref.plot_status.progress.close_sub()
    delay_between_copies = False
