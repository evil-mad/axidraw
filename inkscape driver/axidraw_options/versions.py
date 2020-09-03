import sys
import ast
from collections import namedtuple
from distutils.version import LooseVersion

from axidrawinternal.plot_utils_import import from_dependency_import
ebb_serial = from_dependency_import('plotink.ebb_serial')  # Requires v 0.13 in plotink    https://github.com/evil-mad/plotink

Versions = namedtuple("Versions", "axidraw_control ebb_firmware dev_axidraw_control")

def get_versions_online():
    ''' check online for current versions. does not require connection to Axidraw,
    but DOES require connection to the internet.

    returns namedtuple with the versions
    raises RuntimeError if online check fails.
    '''
    requests = from_dependency_import('requests')

    url = "https://evilmadscience.s3.amazonaws.com/sites/axidraw/versions.txt"
    text = None
    try:
        text = requests.get(url).text
    except RuntimeError as e:
        raise RuntimeError("Could not contact server to check for updates. " +
                           "Are you connected to the internet? (Error: {})".format(e))
    
    if text:
        try:
            dictionary = ast.literal_eval(text)
            online_versions = Versions(axidraw_control=dictionary['AxiDraw Control'],
                                       ebb_firmware=dictionary['EBB Firmware'],
                                       dev_axidraw_control=dictionary['AxiDraw Control (unstable)'])
        except RuntimeError as e:
            raise RuntimeError("Could not parse server response. " +
                               "This is probably the server's fault. (Error: {})".format(e))

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
    except RuntimeError as e:
        raise RuntimeError("There was an error retrieving the EBB firmware version. (Error: {})".format(e))

def log_axidraw_control_version(online_versions, current_version_string, log_fun):
    '''
    `online_versions` is a Versions namedtuple or False,
    e.g. the return value of get_versions_online
    '''
    log_fun("This is AxiDraw Control version {}.".format(current_version_string))

    if online_versions:   
        if LooseVersion(online_versions.axidraw_control) > LooseVersion(current_version_string):
            log_fun("An update is available to a newer version, v. {}.".format(
                online_versions.axidraw_control))
            log_fun("Please visit: axidraw.com/sw for the latest software.")
        elif LooseVersion(current_version_string) > LooseVersion(online_versions.axidraw_control):
            log_fun("~~ An early-release version ~~")
            if (LooseVersion(online_versions.dev_axidraw_control)
                > LooseVersion(current_version_string)):
                log_fun("An update is available to a newer version, v. {}.".format(
                    online_versions.dev_axidraw_control))
                log_fun("To update, please contact AxiDraw technical support.")
            elif (LooseVersion(online_versions.dev_axidraw_control)
                  == LooseVersion(current_version_string)):
                log_fun("This is the newest available development version.")

            log_fun('(The current "stable" release is v. {}).'.format(
                online_versions.axidraw_control))
        else:
            log_fun("Your AxiDraw Control software is up to date.")
    
def log_ebb_version(fw_version_string, online_versions, log_fun):
    '''
    `online_versions` is False if we failed or didn't try to get the online versions
    '''
    log_fun("\nYour AxiDraw has firmware version {}.".format(fw_version_string))
            
    if online_versions:
        if LooseVersion(online_versions.ebb_firmware) > LooseVersion(fw_version_string):
            log_fun("An update is available to EBB firmware v. {};".format(
                online_versions.ebb_firmware))
            log_fun("To download the updater, please visit: axidraw.com/fw\n")
        else:
            log_fun("Your firmware is up to date; no updates are available.\n")

def log_version_info(serial_port, check_updates, current_version_string, preview, message_fun, logger):
    '''
    works whether or not `check_updates` is True, online versions were successfully retrieved,
    or `serial_port` is None (i.e. not connected AxiDraw)
    '''
    online_versions = False
    if check_updates:
        try:
            online_versions = get_versions_online()
        except RuntimeError as e:
            msg = 'Unable to check online for latest version numbers. (Error: {})'.format(e)
            message_fun(msg)
            logger.error(msg)
    else:
        message_fun('Note: Online version checking disabled.')

    log_axidraw_control_version(online_versions, current_version_string, message_fun)

    if serial_port is not None: # i.e. there is a connected AxiDraw
        try:
            fw_version_string = get_fw_version(serial_port)
            log_ebb_version(fw_version_string, online_versions, message_fun)
        except RuntimeError as e:
            msg = "\nUnable to retrieve AxiDraw EBB firmware version. (Error: {}) \n".format(e)
            message_fun(msg)
            logger.error(msg)
    elif preview:
        message_fun('\nFirmware version readout not available in preview mode.')

    message_fun('\nAdditional system information:')
    message_fun(sys.version)
