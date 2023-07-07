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
serial_utils.py

This module modularizes some serial functions..

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

Requires Python 3.7 or newer.

"""

import time
from axidrawinternal.plot_utils_import import from_dependency_import
from axidrawinternal.axidraw_options import versions as ad_versions
ebb_serial = from_dependency_import('plotink.ebb_serial')  # https://github.com/evil-mad/plotink
ebb_motion = from_dependency_import('plotink.ebb_motion')

def connect(options, plot_status, message_fun, logger):
    """ Connect to AxiDraw over USB """
    port_name = None
    if options.port_config == 1: # port_config value "1": Use first available AxiDraw.
        options.port = None
    if not options.port: # Try to connect to first available AxiDraw.
        plot_status.port = ebb_serial.openPort()
    elif str(type(options.port)) in (
            "<type 'str'>", "<type 'unicode'>", "<class 'str'>"):
        # This function may be passed a port name to open (and later close).
        options.port = str(options.port).strip('\"')
        port_name = options.port
        the_port = ebb_serial.find_named_ebb(options.port)
        plot_status.port = ebb_serial.testPort(the_port)
        options.port = None  # Clear this input, to ensure that we close the port later.
    else:
        # options.port may be a serial port object of type serial.serialposix.Serial.
        # In that case, interact with that given port object, and leave it open at the end.
        plot_status.port = options.port

    if plot_status.port is None:
        if port_name:
            message_fun('Failed to connect to AxiDraw ' + str(port_name))
        else:
            message_fun("Failed to connect to AxiDraw.")
        return False

    fw_version_string = ebb_serial.queryVersion(plot_status.port) # Full string, human readable
    fw_version_string = fw_version_string.split("Firmware Version ", 1)
    fw_version_string = fw_version_string[1]
    plot_status.fw_version = fw_version_string.strip() # For number comparisons

    if port_name:
        logger.debug('Connected successfully to port: ' + str(port_name))
    else:
        logger.debug(" Connected successfully")
    return True


def query_voltage(options, params, plot_status, warnings):
    """ Check that power supply is detected. """
    if params.skip_voltage_check:
        return
    if plot_status.port is not None and not options.preview:
        voltage_ok = ebb_motion.queryVoltage(plot_status.port, False)
        if not voltage_ok:
            warnings.add_new('voltage')


def exhaust_queue(ad_ref):
    """
    Wait until queued motion commands have finished executing
    Uses the QG query http://evil-mad.github.io/EggBot/ebb.html#QG
    Uses time.sleep to sleep as long as motion commands are still executing.

    Query every 50 ms. Also break on keyboard interrupt (if configured) and
        pause button press.

    Requires EBB firmware version 2.6.2 or newer, returns (without error) otherwise,
        not executing any delay time.
    """

    if not ad_versions.min_fw_version(ad_ref.plot_status, "2.6.2"):
        return
    if ad_ref.plot_status.port is None:
        return
    while True:
        if ad_ref.receive_pause_request(): # Keyboard interrupt detected!
            break
        status_string = ebb_serial.query(ad_ref.plot_status.port, 'QG\r').strip()
        status = int('0x' + status_string, 16)
        if status & 32: # Pause button pressed
            break
        if status & 15 == 0:  # If no commands are queued or executing,
            break               #   and both motors are idle

        time.sleep(0.050) # Use short intervals for responsiveness
