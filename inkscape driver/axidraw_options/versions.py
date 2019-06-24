import sys
import ast
from collections import namedtuple
from distutils.version import LooseVersion

import ebb_serial  # Requires v 0.13 in plotink    https://github.com/evil-mad/plotink

Versions = namedtuple("Versions", "axidraw_control ebb_firmware dev_axidraw_control")


def get_versions_online():
    ''' check online for current versions. does not require connection to Axidraw,
    but DOES require connection to the internet.

    returns namedtuple with the versions
    raises RuntimeError if online check fails.
    '''
    url = "http://evilmadscience.s3.amazonaws.com/sites/axidraw/versions.txt"
    text = None
    try:
        if sys.version_info < (3,): 
            import urllib # python 2 version
            text = urllib.urlopen(url).read()
        else:
            import urllib.request # python 3 version
            text = urllib.request.urlopen(url).read().decode('utf8')

    except Exception as e:
        raise RuntimeError("Could not contact server to check for updates. " +
                           "Are you connected to the internet? (Error: {})".format(e))
    if text:
        try:
            dictionary = ast.literal_eval(text)
            online_versions = Versions(axidraw_control=dictionary['AxiDraw Control'],
                                       ebb_firmware=dictionary['EBB Firmware'],
                                       dev_axidraw_control=dictionary['AxiDraw Control (unstable)'])
        except Exception as e:
            raise RuntimeError("Could not parse server response. " +
                               "This is probably the server's fault. (Error: {})".format(e))

    return online_versions


def get_versions_online_new():
    ''' check online for current versions. does not require connection to Axidraw,
    but DOES require connection to the internet.

    returns namedtuple with the versions
    raises RuntimeError if online check fails.
    '''
    url = "https://evilmadscience.s3.amazonaws.com/sites/axidraw/versions.txt"
    text = None
    try:
        text = requests.get(url).text
    except Exception as e:
        raise RuntimeError("Could not contact server to check for updates. " +
                           "Are you connected to the internet? (Error: {})".format(e))
    
    if text:
        try:
            dictionary = ast.literal_eval(text)
            online_versions = Versions(axidraw_control=dictionary['AxiDraw Control'],
                                       ebb_firmware=dictionary['EBB Firmware'],
                                       dev_axidraw_control=dictionary['AxiDraw Control (unstable)'])
        except Exception as e:
            raise RuntimeError("Could not parse server response. " +
                               "This is probably the server's fault. (Error: {})".format(e))

    return online_versions

def get_ebb_version(serial_port):
    '''
    `serial_port` is the serial port to the AxiDraw (which must already be connected)

    returns an ebb version string
    '''
    try:
        ebb_version_string = ebb_serial.queryVersion(serial_port)
        ebb_version_string = ebb_version_string.split("Firmware Version ", 1)
        ebb_version_string = ebb_version_string[1]
        ebb_version_string = ebb_version_string.strip() # For number comparisons
        return ebb_version_string
    except Exception as e:
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
            log_fun("~~ An early-release (beta) version ~~")
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
    
def log_ebb_version(ebb_version_string, online_versions, log_fun):
    '''
    `online_versions` is False if we failed or didn't try to get the online versions
    '''
    log_fun("\nYour AxiDraw has firmware version {}.".format(ebb_version_string))
            
    if online_versions:
        if LooseVersion(online_versions.ebb_firmware) > LooseVersion(ebb_version_string):
            log_fun("An update is available to EBB firmware v. {};".format(
                online_versions.ebb_firmware))
            log_fun("To download the updater, please visit: axidraw.com/fw\n")
        else:
            log_fun("Your firmware is up to date; no updates are available.\n")

def log_version_info(serial_port, check_updates, current_version_string, log_fun, err_log_fun):
    '''
    works whether or not `check_updates` is True, online versions were successfully retrieved,
    or `serial_port` is None (i.e. not connected AxiDraw)
    '''
    online_versions = False
    if check_updates:
        try:
            online_versions = get_versions_online()
        except RuntimeError as e:
            err_log_fun('Unable to check online for latest version numbers. (Error: {})'.format(e))
    else:
        log_fun('Note: Online version checking disabled.')

    log_axidraw_control_version(online_versions, current_version_string, log_fun)

    if serial_port is not None: # i.e. there is a connected AxiDraw
        try:
            ebb_version_string = get_ebb_version(serial_port)
            log_ebb_version(ebb_version_string, online_versions, log_fun)
        except RuntimeError as e:
            err_log_fun("\nUnable to retrieve AxiDraw EBB firmware version. (Error: {}) \n".format(e))

    log_fun('\nAdditional system information:')
    log_fun(sys.version)
