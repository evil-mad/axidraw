# coding=utf-8
# ebb_serial.py
# Serial connection utilities for EiBotBoard
# https://github.com/evil-mad/plotink
#
# Intended to provide some common interfaces that can be used by
# EggBot, WaterColorBot, AxiDraw, and similar machines.
#
# See below for version information
#
# Thanks to Shel Michaels for bug fixes and helpful suggestions.
#
# The MIT License (MIT)
#
# Copyright (c) 2019 Windell H. Oskay, Evil Mad Scientist Laboratories
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import gettext

try:
    from plot_utils_import import from_dependency_import
    inkex = from_dependency_import('ink_extensions.inkex')
    serial = from_dependency_import('serial')
except:
    import inkex
    import serial

from distutils.version import LooseVersion

def version():      # Version number for this document
    return "0.14"   # Dated 2019-06-18


def findPort():
    # Find first available EiBotBoard by searching USB ports.
    # Return serial port object.
    try:
        from serial.tools.list_ports import comports
    except ImportError:
        return None
    if comports:
        com_ports_list = list(comports())
        ebb_port = None
        for port in com_ports_list:
            if port[1].startswith("EiBotBoard"):
                ebb_port = port[0]  # Success; EBB found by name match.
                break  # stop searching-- we are done.
        if ebb_port is None:
            for port in com_ports_list:
                if port[2].startswith("USB VID:PID=04D8:FD92"):
                    ebb_port = port[0]  # Success; EBB found by VID/PID match.
                    break  # stop searching-- we are done.
        return ebb_port


def find_named_ebb(port_name):
    # Find a specific EiBotBoard identified by a string giving either:
    #        The enumerated serial port, or
    #        An EBB "Name tag"
    #
    # Names should be 3-16 characters long.
    # Comparisons are not case sensitive.
    #
    # (Name tags may assigned with the ST command on firmware 2.5.5 and later.)
    #
    # If found:     Return serial port name (enumeration)
    # If not found, Return None
    if port_name is not None:
        try:
            from serial.tools.list_ports import comports
        except ImportError:
            return None
        if comports:
            needle = 'SER=' + port_name     # pyserial 3
            needle2 = 'SNR=' + port_name    # pyserial 2.7
            needle3 = '(' + port_name + ')' # e.g., "(COM4)"

            needle = needle.lower()
            needle2 = needle2.lower()
            needle3 = needle3.lower()
            plower = port_name.lower()

            com_ports_list = list(comports())
            ebb_port = None

            for port in com_ports_list:
                p0 = port[0].lower()
                p1 = port[1].lower()
                p2 = port[2].lower()

                if needle in p2:
                    return port[0]  # Success; EBB found by name match.
                if needle2 in p2:
                    return port[0]  # Success; EBB found by name match.
                if needle3 in p1:
                    return port[0]  # Success; EBB found by port match.

                p1 = p1[11:]
                if p1.startswith(plower):
                    return port[0]  # Success; EBB found by name match.
                if p0.startswith(plower):
                    return port[0]  # Success; EBB found by port match.

                needle.replace(" ", "_") # SN on Windows has underscores, not spaces.
                if needle in p2:
                    return port[0]  # Success; EBB found by port match.

                needle2.replace(" ", "_") # SN on Windows has underscores, not spaces.
                if needle2 in p2:
                    return port[0]  # Success; EBB found by port match.


def query_nickname(port_name, verbose=True):
    # Query the EBB nickname and report it.
    # This feature is only supported in firmware versions 2.5.5 and newer.
    # If verbose is True or omitted, the result will be human readable.
    # A short version is returned if verbose is False.
    # http://evil-mad.github.io/EggBot/ebb.html#QT
    if port_name is not None:
        version_status = min_version(port_name, "2.5.5")

        if version_status:
            raw_string = (query(port_name, 'QT\r'))
            if raw_string.isspace():
                if verbose:
                    return "This AxiDraw does not have a nickname assigned."
                else:
                    return None
            else:
                if verbose:
                    return "AxiDraw nickname: " + raw_string
                else:
#                     string_temp = str(raw_string).strip()
                    return str(raw_string).strip()
        elif version_status is False:
            if verbose:
                return "AxiDraw naming requires firmware version 2.5.5 or higher."

def write_nickname(port_name, nickname):
    # Write the EBB nickname.
    # This feature is only supported in firmware versions 2.5.5 and newer.
    # http://evil-mad.github.io/EggBot/ebb.html#ST
    if port_name is not None:
        version_status = min_version(port_name, "2.5.5")

        if version_status:
            try:
                cmd = 'ST,' + nickname + '\r'
                command(port_name,cmd)
                return True
            except:
                return False

def reboot(port_name):
    # Reboot the EBB, as though it were just powered on.
    # This feature is only supported in firmware versions 2.5.5 and newer.
    # It has no effect if called on an EBB with older firmware.
    # http://evil-mad.github.io/EggBot/ebb.html#RB
    if port_name is not None:
        version_status = min_version(port_name, "2.5.5")
        if version_status:
            try:
                command(port_name,'RB\r')
            except:
                pass


def list_port_info():
    # Find and return a list of all USB devices and their information.
    try:
        from serial.tools.list_ports import comports
    except ImportError:
        return None
    if comports:
        com_ports_list = list(comports())
        port_info_list = []
        for port in com_ports_list:
            port_info_list.append(port[0]) # port name
            port_info_list.append(port[1]) # Identifier
            port_info_list.append(port[2]) # VID/PID
        if port_info_list:
            return port_info_list


def listEBBports():
    # Find and return a list of all EiBotBoard units
    # connected via USB port.
    try:
        from serial.tools.list_ports import comports
    except ImportError:
        return None
    if comports:
        com_ports_list = list(comports())
        ebb_ports_list = []
        for port in com_ports_list:
            port_has_ebb = False
            if port[1].startswith("EiBotBoard"):
                port_has_ebb = True
            elif port[2].startswith("USB VID:PID=04D8:FD92"):
                port_has_ebb = True
            if port_has_ebb:
                ebb_ports_list.append(port)
        if ebb_ports_list:
            return ebb_ports_list


def list_named_ebbs():
    # Return discriptive list of all EiBotBoard units
    ebb_ports_list = listEBBports()
    if not ebb_ports_list:
        return
    ebb_names_list = []
    for port in ebb_ports_list:
        name_found = False
        p0 = port[0]
        p1 = port[1]
        p2 = port[2]
        if p1.startswith("EiBotBoard"):
            temp_string = p1[11:]
            if (temp_string):
                if temp_string is not None:
                    ebb_names_list.append(temp_string)
                    name_found = True
        if not name_found:
            # Look for "SER=XXXX LOCAT" pattern,
            #  typical of Pyserial 3 on Windows.
            if 'SER=' in p2 and ' LOCAT' in p2:
                index1 = p2.find('SER=') + len('SER=')
                index2 = p2.find(' LOCAT', index1)
                temp_string = p2[index1:index2]
                if len(temp_string) < 3:
                    temp_string = None
                if temp_string is not None:
                    ebb_names_list.append(temp_string)
                    name_found = True
        if not name_found:
            # Look for "...SNR=XXXX" pattern,
            #  typical of Pyserial 2.7 on Windows,
            #  as in Inkscape 0.91 on Windows
            if 'SNR=' in p2:
                index1 = p2.find('SNR=') + len('SNR=')
                index2 = len(p2)
                temp_string = p2[index1:index2]
                if len(temp_string) < 3:
                    temp_string = None
                if temp_string is not None:
                    ebb_names_list.append(temp_string)
                    name_found = True
        if not name_found:
            ebb_names_list.append(p0)
    return ebb_names_list


def testPort(port_name):
    """
    Open a given serial port, verify that it is an EiBotBoard,
    and return a SerialPort object that we can reference later.

    This routine only opens the port;
    it will need to be closed as well, for example with closePort( port_name ).
    You, who open the port, are responsible for closing it as well.

    """
    if port_name is not None:
        try:
            serial_port = serial.Serial(port_name, timeout=1.0)  # 1 second timeout!

            serial_port.flushInput()  # deprecated function name;
            # use serial_port.reset_input_buffer()
            # if we can be sure that we have pySerial 3+.

            serial_port.write('v\r'.encode('ascii'))
            str_version = serial_port.readline()
            if str_version and str_version.startswith("EBB".encode('ascii')):
                return serial_port

            serial_port.write('v\r'.encode('ascii'))
            str_version = serial_port.readline()
            if str_version and str_version.startswith("EBB".encode('ascii')):
                return serial_port
            serial_port.close()
        except serial.SerialException:
            pass
        return None


def openPort():
    # Find and open a port to a single attached EiBotBoard.
    # The first port located will be used.
    found_port = findPort()
    serial_port = testPort(found_port)
    if serial_port:
        return serial_port


def open_named_port(port_name):
    # Find and open a port to a single attached EiBotBoard.
    # The first port located will be used.
    found_port = find_named_ebb(port_name)
    serial_port = testPort(found_port)
    if serial_port:
        return serial_port


def closePort(port_name):
    if port_name is not None:
        try:
            port_name.close()
        except serial.SerialException:
            pass


def query(port_name, cmd):
    if port_name is not None and cmd is not None:
        response = ''
        try:
            port_name.write(cmd.encode('ascii'))
            response = port_name.readline().decode('ascii')
            n_retry_count = 0
            while len(response) == 0 and n_retry_count < 100:
                # get new response to replace null response if necessary
                response = port_name.readline()
                n_retry_count += 1
            if cmd.strip().lower() not in ["v", "i", "a", "mr", "pi", "qm"]:
                # Most queries return an "OK" after the data requested.
                # We skip this for those few queries that do not return an extra line.
                unused_response = port_name.readline()  # read in extra blank/OK line
                n_retry_count = 0
                while len(unused_response) == 0 and n_retry_count < 100:
                    # get new response to replace null response if necessary
                    unused_response = port_name.readline()
                    n_retry_count += 1
        except:
            inkex.errormsg(gettext.gettext("Error reading serial data."))
        return response


def command(port_name, cmd):
    if port_name is not None and cmd is not None:
        try:
            port_name.write(cmd.encode('ascii'))
            response = port_name.readline().decode('ascii')
            n_retry_count = 0
            while len(response) == 0 and n_retry_count < 100:
                # get new response to replace null response if necessary
                response = port_name.readline().decode('ascii')
                n_retry_count += 1
            if response.strip().startswith("OK"):
                # Debug option: indicate which command:
                # inkex.errormsg( 'OK after command: ' + cmd )
                pass
            else:
                if response:
                    inkex.errormsg('Error: Unexpected response from EBB.')
                    inkex.errormsg('   Command: {0}'.format(cmd.strip()))
                    inkex.errormsg('   Response: {0}'.format(response.strip()))
                else:
                    inkex.errormsg('EBB Serial Timeout after command: {0}'.format(cmd))
        except:
            if cmd.strip().lower() not in ["rb"]: # Ignore error on reboot (RB) command
	            inkex.errormsg('Failed after command: {0}'.format(cmd))


def bootload(port_name):
    # Enter bootloader mode. Do not try to read back data.
    if port_name is not None:
        try:
            port_name.write('BL\r'.encode('ascii'))
            return True
        except:
            return False


def min_version(port_name, version_string):
    # Query the EBB firmware version for the EBB located at port_name.
    # Return True if the EBB firmware version is at least version_string.
    # Return False if the EBB firmware version is below version_string.
    # Return None if we are unable to determine True or False.

    if port_name is not None:
        ebb_version_string = queryVersion(port_name)  # Full string, human readable
        ebb_version_string = ebb_version_string.split("Firmware Version ", 1)

        if len(ebb_version_string) > 1:
            ebb_version_string = ebb_version_string[1]
        else:
            return None  # We haven't received a reasonable version number response.

        ebb_version_string = ebb_version_string.strip()  # Stripped copy, for number comparisons
        if ebb_version_string is not "none":
            if LooseVersion(ebb_version_string) >= LooseVersion(version_string):
                return True
            else:
                return False


def queryVersion(port_name):
    return query(port_name, 'V\r')  # Query EBB Version String
