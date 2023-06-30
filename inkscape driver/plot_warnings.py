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
plot_warnings.py

Classes for managing and outputting AxiDraw text warnings

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

"""

def layer_name_text(layer_name):
    '''Format layer name text for displaying in warning messages'''
    if layer_name == '__digest-root__':
        return " found in the document root."
    if layer_name.strip() == '':
        return "."
    return " in a layer named " + layer_name.strip() + "."

class PlotWarnings:
    """
    PlotWarnings: Class for managing and outputting warning text messages
    """

    def __init__(self):
        self.warning_dict = {} # Dict for warnings; only store the first warning of each type.
        self.suppress_list = [] # List of warnings that will be suppressed (not reported).

    def reset(self):
        '''Clear the warnings dictionary'''
        self.warning_dict.clear()

    def add_new(self, warning_name, value="1"):
        '''
        Add a warning if that warning type is not already in the dictionary.
        The default value "1" will cause error types of voltage, bounds to be reported.
        For other types (image, text, unknown object), the value should reference the
        SVG layer where the object was detected.
        '''
        if warning_name not in self.warning_dict:
            self.warning_dict[warning_name] = value

    def suppress(self, warning_name):
        '''
        Disable reporting of a specific warning type.
        Use "__all__" as the warning name argument to suppress *all* warnings.
        '''
        self.suppress_list.append(warning_name)

    def return_text_list(self):
        '''Return a list of formatted warning strings'''
        warning_text_list = []

        if '__all__' in self.suppress_list:
            return warning_text_list

        if 'voltage' in self.warning_dict:
            if 'voltage' not in self.suppress_list:
                warning_text_list.append(
                    "Note (voltage): Low voltage detected.\n" +
                    "Check that power supply is plugged in.\n"
                )
            self.warning_dict.pop('voltage')

        if 'bounds' in self.warning_dict:
            if 'bounds' not in self.suppress_list:
                warning_text_list.append(
                    "Warning (bounds): AxiDraw movement was limited by its" +
                    "\nphysical range of motion. If everything else looks" +
                    "\ncorrect, there may be an issue with the document size," +
                    "\nor the wrong model of AxiDraw may be selected." +
                    "\nPlease contact technical support if you need assistance.\n"
                )
            self.warning_dict.pop('bounds')

        if 'image' in self.warning_dict:
            if 'image' not in self.suppress_list:
                warning_text_list.append(
                    'Note (image): This file contains a bitmap image' +
                    layer_name_text(self.warning_dict['image']) +
                    "\nPlease convert images to vectors before plotting." +
                    "\nConsider using the Inkscape Path > Trace Bitmap tool.\n"
                    )
            self.warning_dict.pop('image')

        if 'text' in self.warning_dict:
            if 'text' not in self.suppress_list:
                warning_text_list.append(
                    'Note (plain-text): This file contains some plain text\n' +
                    layer_name_text(self.warning_dict['text']) +
                    "\nPlease convert text into vector paths before plotting." +
                    "\nConsider using the Inkscape Path > Object to Path tool." +
                    "\nAlternately, consider using Hershey Text to render your" +
                    "\ntext with stroke-based fonts.\n"
                )
            self.warning_dict.pop('text')

        for object_type, layer_location in self.warning_dict.items():
            # Handle any remaining unknown objects
            if object_type in self.suppress_list:
                continue
            warning_text_list.append(
                'Note (object): Unable to plot ' + object_type + ' object' +
                layer_name_text(layer_location) +
                "\nPlease convert it to a path prior to plotting, and/or " +
                "contact technical support if you need assistance.\n"
            )

        return warning_text_list

    def report(self, suppress, message_fun):
        '''Print warning messages to the given message function'''
        if not suppress:
            for warning_message in self.return_text_list():
                message_fun(warning_message)
