#!/usr/bin/env python
#
# Copyright (C) 2021 Windell H. Oskay, www.evilmadscientist.com
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
A utility extension to assist with importing AI SVG files.

Version 1.1
"""

from axidrawinternal.plot_utils_import import from_dependency_import # plotink
inkex = from_dependency_import('ink_extensions.inkex')
plot_utils = from_dependency_import('plotink.plot_utils')


class ProcessAI(inkex.Effect):
    """
    Main class of the process_ai extension

    This extension performs the following two actions:
    1) Recognize intended dimensions of original document.
        - If the AI document was set up with a size given in picas, cm, mm, or in,
          and then exported to SVG, no conversion is needed.
        - If the AI document was set up with any other dimensions,
          (point, yard, px, ft/in, ft, or m), then the exported SVG
          will be in units of 72 DPI pixels. This causes an issue,
          as Inkscape uses CSS pixels (px) which are at 96 DPI.
          In this case, we re-interpret the size as 72 DPI points (pt),
          which will convert the artwork to appear at the correct size.
    2) Recognize Adobe Illustrator layers.
        - Group (<g>) elements with non-empty data-name attributes are
          groups in an Illustrator SVG document.
        - We re-label these as layers such that Inkscape will recognize them.

    """
    def effect(self):
        """
        Main entry point of the process_ai extension
        """
        # 1) Recognize intended dimensions of original document.
        the_svg = self.document.getroot()

        width_string = the_svg.get('width')
        height_string = the_svg.get('height')

        if width_string and height_string:
            width_num, width_units = plot_utils.parseLengthWithUnits(width_string)
            height_num, height_units = plot_utils.parseLengthWithUnits(height_string)

            # Note that plot_utils.parseLengthWithUnits will return units of 'px'
            #    for unitless values, not None.

            if width_num:
                if width_units == 'px':
                    the_svg.set('width', str(width_num) + 'pt')
            if height_num:
                if height_units == 'px':
                    the_svg.set('height', str(height_num) + 'pt')

        # 2) Recognize Adobe Illustrator layers.
        for node in the_svg.xpath('//svg:g[@data-name]', namespaces=inkex.NSS ):
            node.set("{http://www.inkscape.org/namespaces/inkscape}groupmode", 'layer')
            node.set("{http://www.inkscape.org/namespaces/inkscape}label", node.get('data-name'))
            del node.attrib["data-name"]

if __name__ == '__main__':
    e = ProcessAI()
    e.affect()
