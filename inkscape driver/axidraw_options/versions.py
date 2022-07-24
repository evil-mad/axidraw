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
versions.py

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

"""

import sys
import ast
from collections import namedtuple
from packaging.version import parse

from axidrawinternal.plot_utils_import import from_dependency_import
ebb_serial = from_dependency_import('plotink.ebb_serial')  # https://github.com/evil-mad/plotink
requests = from_dependency_import('requests')

Versions = namedtuple("Versions", "axidraw_control ebb_firmware dev_axidraw_control")

def get_versions_online():
    ''' check online for current versions. does not require connection to Axidraw,
    but DOES require connection to the internet.

    returns namedtuple with the versions
    raises RuntimeError if online check fails.
    '''
    url = "https://evilmadscience.s3.amazonaws.com/sites/axidraw/versions.txt"
    text = None
    try:
        text = requests.get(url).text
    except (RuntimeError, requests.exceptions.ConnectionError) as err_info:
        raise RuntimeError("Could not contact server to check for updates. " +
                    f"Are you connected to the internet?\n\n(Error details: {err_info})\n")

    if text:
        try:
            dictionary = ast.literal_eval(text)
            online_versions = Versions(axidraw_control=dictionary['AxiDraw Control'],
                                   ebb_firmware=dictionary['EBB Firmware'],
                                   dev_axidraw_control=dictionary['AxiDraw Control (unstable)'])
        except RuntimeError as err_info:
            raise RuntimeError("Could not parse server response. " +
                    f"This is probably the server's fault.\n\n(Error details: {err_info}\n)"
                    ).with_traceback(sys.exc_info()[2])

    return online_versions

def get_fw_version(serial_port):
    '''
    `serial_port` is the serial port to the AxiDraw (which must already be connected)

    returns an ebb version string
    '''
    try:
        fw_version_string = ebb_serial.queryVersion(serial_port)
        fw_version_string = fw_version_string.split("Firmware Version ", 1)
        fw_version_string = fw_version_string[1]
        fw_version_string = fw_version_string.strip() # For number comparisons
        return fw_version_string
    except RuntimeError as err_info:
        raise RuntimeError(f"Error retrieving the EBB firmware version.\n\n(Error: {err_info})\n")


def get_current(serial_port):
    '''
    `serial_port` is the serial port to the AxiDraw (which must already be connected)

    Query the EBB current setpoint and voltage input
    '''
    try:
        if not ebb_serial.min_version(serial_port, "2.2.3"):
            return None, None
        raw_string = (ebb_serial.query(serial_port, 'QC\r'))
        split_string = raw_string.split(",", 1)
        split_len = len(split_string)
        if split_len > 1:
            current_value = int(split_string[0])  # Current setpoint
            voltage_value = int(split_string[1])  # Voltage readout
            return voltage_value, current_value
        return None, None
    except RuntimeError:
        return None, None # presumably, we've already reported connection difficulties.

def log_axidraw_control_version(online_versions, current_version_string, log_fun):
    '''
    `online_versions` is a Versions namedtuple or False,
    e.g. the return value of get_versions_online
    '''
    log_fun(f"This is AxiDraw Control version {current_version_string}.")

    if online_versions:
        if parse(online_versions.axidraw_control) > parse(current_version_string):
            log_fun("An update is available to a newer version, " +
                    f"{online_versions.axidraw_control}.")
            log_fun("Please visit: axidraw.com/sw for the latest software.")
        elif parse(current_version_string) > parse(online_versions.axidraw_control):
            log_fun("~~ An early-release version ~~")
            if parse(online_versions.dev_axidraw_control) > parse(current_version_string):
                log_fun("An update is available to a newer version, " +
                        f"{online_versions.dev_axidraw_control}.")
                log_fun("To update, please contact AxiDraw technical support.")
            elif (parse(online_versions.dev_axidraw_control) == parse(current_version_string)):
                log_fun("This is the newest available development version.")

            log_fun(f'(The current "stable" release is v. {online_versions.axidraw_control}).')
        else:
            log_fun("Your AxiDraw Control software is up to date.")

def log_ebb_version(fw_version_string, online_versions, log_fun):
    '''
    `online_versions` is False if we failed or didn't try to get the online versions
    '''
    # log_fun("\nYour AxiDraw has firmware version {}.".format(fw_version_string))
    log_fun(f"\nYour AxiDraw has firmware version {fw_version_string}.")

    if online_versions:
        if parse(online_versions.ebb_firmware) > parse(fw_version_string):
            log_fun(f"An update is available to EBB firmware v. {online_versions.ebb_firmware};")
            log_fun("To download the updater, please visit: axidraw.com/fw\n")
        else:
            log_fun("Your firmware is up to date; no updates are available.\n")

def log_version_info(serial_port, check_updates, current_version_string, preview,
        message_fun, logger):
    '''
    works whether or not `check_updates` is True, online versions were successfully retrieved,
    or `serial_port` is None (i.e. not connected AxiDraw)
    '''
    online_versions = False
    if check_updates:
        try:
            online_versions = get_versions_online()
        except RuntimeError as err_info:
            msg = f'{err_info}'
            logger.error(msg)
    else:
        message_fun('Note: Online version checking disabled.')

    log_axidraw_control_version(online_versions, current_version_string, message_fun)
    voltage, current = None, None
    if serial_port is not None: # i.e. there is a connected AxiDraw
        try:
            fw_version_string = get_fw_version(serial_port)
            voltage, current = get_current(serial_port)
            log_ebb_version(fw_version_string, online_versions, message_fun)
        except RuntimeError as err_info:
            msg = f"\nUnable to retrieve AxiDraw EBB firmware version. (Error: {err_info}) \n"
            message_fun(msg)
            logger.error(msg)
    elif preview:
        message_fun('\nFirmware version readout not available in preview mode.')

    message_fun('\nAdditional system information:')
    message_fun(sys.version)
    if voltage is not None and current is not None:
        scaled_voltage = 0.3 + voltage * 3.3 * 9.2 / 1023 # Scaling depends on hardware version
        scaled_current = current  * 3.3 / (1023 * 1.76)
        message_fun(f'Voltage readout: {voltage:d} (~ {scaled_voltage:.2f} V).')
        message_fun(f'Current setpoint: {current:d} (~ {scaled_current:.2f} A).')
