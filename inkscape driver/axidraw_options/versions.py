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
import logging

from axidrawinternal.plot_utils_import import from_dependency_import
requests = from_dependency_import('requests')
version = from_dependency_import('packaging.version')

logger = logging.getLogger('axidrawinternal.axidraw.versions')

# keys used for reporting versions relevant to this repo
DEV_AXIDRAW_CONTROL = "AxiDraw Control (unstable)"
AXIDRAW_CONTROL = "AxiDraw Control"

# EBB firmware key
EBB_FIRMWARE = "EBB Firmware"

def get_versions_online(check_updates, message_fun, keys = None):
    '''
    this is easily used by any consumers of AxiDraw-Internal, e.g. hershey-advanced

    keys is a list of software/firmware that we want versions for.
    If keys is None, default to [AXIDRAW_CONTROL, DEV_AXIDRAW_CONTROL, EBB_FIRMWARE]

    returns dict with the versions. list(dict.keys()) will equal the `keys` parameter, if provided.
    '''

    keys = (keys if keys is not None else
            ["AxiDraw Control", "AxiDraw Control (unstable)", "EBB Firmware"])
    online_versions = {}
    if check_updates:
        try:
            online_versions = _query_versions_url(keys)
        except RuntimeError as err_info:
            msg = f'{err_info}'
            logger.error(msg)
    else:
        message_fun('Note: Online version checking disabled.')

    return online_versions

def _query_versions_url(keys):
    ''' check online for current versions. does not require connection to Axidraw,
    but DOES require connection to the internet.

    returns dict with the versions.
    list(dict.keys()) will equal the `keys` parameter
    dict.values() will all be of type packaging.version.Version, or None

    raises RuntimeError if online check fails
    '''
    url = "https://evilmadscience.s3.amazonaws.com/sites/axidraw/versions.txt"
    text = None
    try:
        text = requests.get(url, timeout=15).text
    except requests.exceptions.Timeout as err:
        raise RuntimeError("Unable to check for updates online; connection timed out.\n") from err
    except (RuntimeError, requests.exceptions.ConnectionError) as err_info:
        raise RuntimeError("Could not contact server to check for updates. " +
            f"Are you connected to the internet?\n\n(Error details: {err_info})\n") from err_info

    if text:
        try:
            all_versions = ast.literal_eval(text)
            requested_versions = { key: version.parse(all_versions.get(key)) for key in keys }
            return requested_versions
        except (RuntimeError, ValueError, KeyError, SyntaxError) as err_info:
            raise RuntimeError("Could not parse server response. " +
                    f"This is probably the server's fault.\n\n(Error details: {err_info}\n)"
                    ).with_traceback(sys.exc_info()[2])

    return requested_versions

def get_current(plot_status):
    '''
    this is easily used by any consumers of AxiDraw-Internal, e.g. hershey-advanced

    `serial_port` is the serial port to the AxiDraw (which must already be connected)
    Query the EBB current setpoint and voltage input
    '''
    try:
        # not all consumers of this module require ebb_serial, e.g. hta/hershey_advanced.py
        ebb_serial = from_dependency_import('plotink.ebb_serial')

        if not min_fw_version(plot_status, "2.2.3"):
            return None, None
        raw_string = ebb_serial.query(plot_status.port, 'QC\r')
        split_string = raw_string.split(",", 1)
        split_len = len(split_string)
        if split_len > 1:
            current_value = int(split_string[0])  # Current setpoint
            voltage_value = int(split_string[1])  # Voltage readout
            return voltage_value, current_value
        return None, None
    except RuntimeError:
        return None, None # presumably, we've already reported connection difficulties.

def _report_axidraw_control_version(online_versions, current_version_string, message_fun):
    '''
    `online_versions` is a Versions namedtuple or False,
    e.g. the return value of get_versions_online
    '''
    report_software_version(
            AXIDRAW_CONTROL,
            version.parse(current_version_string),
            online_versions.get(AXIDRAW_CONTROL),
            online_versions.get(DEV_AXIDRAW_CONTROL),
            message_fun,
            stable_updates_url = "axidraw.com/sw"
    )

def report_software_version(
        software_name, local_version, stable_version, dev_version, message_fun,
        stable_updates_url=False):
    '''
    this is easily used by any consumers of AxiDraw-Internal, e.g. hershey-advanced

    `local_version`, `stable_version`, `local_version` are all of type `packaging.version.Version`

    `stable_updates_url` a url where stable version updates can be found online

    `online_versions` is a dict containing relevant keys or False,
    e.g. the return value of get_versions_online
    '''
    update_contact_str = "To update, please contact AxiDraw technical support."

    message_fun(f"This is {software_name} version {local_version}.")

    if stable_version is None or dev_version is None: # no version data was retrieved from web
        return

    if stable_version > local_version:
        message_fun("An update is available to a newer version, " +
                f"{stable_version}.")
        if stable_updates_url: # AxiDraw Control, probably
            message_fun(f"Please visit: {stable_updates_url} for the latest software.")
        else: # hershey or merge, probably
            message_fun(update_contact_str)
    elif local_version > stable_version:
        message_fun("~~ An early-release version~~")
        if dev_version > local_version:
            message_fun("An update is available to a newer version, " +
                    f"{dev_version}.")
            message_fun(update_contact_str)
        elif dev_version == local_version:
            message_fun("This is the newest available development version.")

        message_fun(f'(The current "stable" release is v. {stable_version}).')
    else:
        message_fun(f"Your {software_name} software is up to date.")

def report_ebb_version(fw_version_string, online_versions, message_fun):
    '''
    this is easily used by any consumers of AxiDraw-Internal, e.g. hershey-advanced

    `online_versions` is False if we failed or didn't try to get the online versions
    '''
    message_fun(f"\nYour AxiDraw has firmware version {fw_version_string}.")

    if online_versions:
        if online_versions[EBB_FIRMWARE] > version.parse(fw_version_string):
            message_fun(
                    f"An update is available to EBB firmware v. {online_versions[EBB_FIRMWARE]};")
            message_fun("To download the updater, please visit: axidraw.com/fw\n")
        else:
            message_fun("Your firmware is up to date; no updates are available.\n")

def report_version_info(plot_status, check_updates, current_version_string, preview, message_fun):
    '''
    currently should only be used by AxiDraw-Internal, might change in the future todo decide

    works whether or not `check_updates` is True, online versions were successfully retrieved,
    or `plot_status.port` is None (i.e. not connected AxiDraw)
    '''

    online_versions = get_versions_online(check_updates, message_fun)

    _report_axidraw_control_version(online_versions, current_version_string, message_fun)

    voltage, current = None, None
    if plot_status.port is not None: # i.e. there is a connected AxiDraw
        try:
            fw_version_string = plot_status.fw_version
            voltage, current = get_current(plot_status)
            report_ebb_version(fw_version_string, online_versions, message_fun)
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

def min_fw_version(plot_status, version_string):
    '''
    this is easily used by any consumers of AxiDraw-Internal, e.g. hershey-advanced

    Using already-known firmware version string in plot_status:
    Return True if the EBB firmware version is at least version_string.
    Return False if the EBB firmware version is below version_string.
    Return None if we are unable to determine True or False.
    '''
    fw_version = plot_status.fw_version
    if fw_version is None:
        return None
    if version.parse(fw_version) >= version.parse(version_string):
        return True
    return False
