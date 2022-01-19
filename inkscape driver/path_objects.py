# coding=utf-8
#
# Copyright 2021 Windell H. Oskay, Evil Mad Scientist Laboratories
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
path_objects.py

Classes and functions for working with simplified path objects

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

The classes defined by this function are:
* DocDigest: An object corresponding to a single SVG document

* PathItem: An object corresponding to a single SVG path

* LayerItem: An object corresponding to a single SVG layer

In each case, the formats supported here are ones that can be mapped
to a very limited subset of SVG.
"""

from lxml import etree

from axidrawinternal.plot_utils_import import from_dependency_import # plotink
plot_utils = from_dependency_import('plotink.plot_utils')
inkex = from_dependency_import('ink_extensions.inkex')

PLOB_BASE = """<?xml version="1.0" standalone="no"?>
<svg
   xmlns:dc="http://purl.org/dc/elements/1.1/"
   xmlns:cc="http://creativecommons.org/ns#"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:svg="http://www.w3.org/2000/svg"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   version="1.1">
   </svg>
"""

PLOB_VERSION = "1"


class PathItem:
    """
    PathItem: An object corresponding to a single SVG path

    Each PathItem instance contains the following elements:
    - subpaths: A list of vertex lists
    - stroke: stroke color or None
    - fill: fill color or None
    - fill_rule: corresponding to the SVG fill-rule
    - item_id: A unique ID string

    Each element subpaths[i] is a "vertex list"; a list of 2-element vertex
    pairs that represents a "subpath": a single sequence of pen-down motion
    segments without pen lifts. A single subpath contains path data equivalent
    to that in an SVG polyline object. The subpaths[] element represents a list
    of subpaths.

    If an instance of PathItem has only one item in subpaths, then it is said
    to be "flat", and represents a single subpath only.

    Certain class methods like first_point, last_point, reverse, and to_string
    are only useful for use on a "flat" instance of PathItem, which is to say
    that it is one where self.subpaths has length 1.

    fill_rule may be None, "nonzero", or "evenodd". A value of None is
    equivalent to "nonzero", the default behavior.
    """

    def __init__(self):
        self.subpaths = None    # list of lists of 2-element vertices
        self.stroke = None      # stroke color or None
        self.fill = None        # fill color or None
        self.fill_rule = None   # May be None, "nonzero", or "evenodd"
        self.item_id = None     # string

    def to_string(self):
        """
        Convert the list of vertices from the first subpath to an SVG polyline
        "points" attribute string and return that string.
        """
        return vertex_list_to_string(self.subpaths[0])

    def from_string(self, polyline_string):
        """
        Fill the list of vertices, given a svg polyline "points"
        attribute string
        """
        self.subpaths = []
        self.subpaths.append(polyline_string_to_list(polyline_string))

    def first_point(self):
        """
        Return first vertex of first subpath. Intended for use on "flat"
        PathItem objects that only contain a single subpath.
        """
        if self.subpaths is not None:
            return self.subpaths[0][0]
        return None

    def last_point(self):
        """
        Return last vertex of first subpath. Intended for use on "flat"
        PathItem objects that only contain a single subpath.
        """
        if self.subpaths:
            return self.subpaths[0][-1]
        return None

    def closed(self):
        """
        If PathItem contains only a single closed subpath, return True
        """
        if self.subpaths:
            if len(self.subpaths) == 1:
                return plot_utils.points_equal(self.subpaths[0][0], self.subpaths[0][-1])
        return False

    def reverse(self):
        """
        If PathItem contains only a single subpath, reverse it.
        In practice, this reverses the direction that the path will be drawn.
        """
        if self.subpaths:
            if len(self.subpaths) == 1:
                self.subpaths[0].reverse()


class LayerItem:
    """
    LayerItem: An object corresponding to a single SVG layer

    Each LayerItem instance contains the following elements:
    - name, a string representing the name of the layer
    - paths, a list of PathItem elements in the layer
    - item_id: A unique ID string
    """

    def __init__(self):
        self.name = ""          # Name of the layer
        self.paths = []         # List of PathItem objects in the layer
        self.item_id = None     # ID string

    def flatten(self):
        """
        Flatten all PathItem objects in the LayerItem, so that each
        PathItem instance represents only a single subpath.
        Remove fill color and fill rule
        """

        if not self.paths:
            return # No paths in the layer; nothing to flatten

        new_paths = [] # Empty list for new path items

        for path in self.paths:
            if len(path.subpaths) == 1: # This path is already flat
                new_paths.append(path)
                continue
            counter = 0
            for subpath in path.subpaths: # Make new PathItem objects
                new_path = PathItem()
                new_path.stroke=path.stroke # preserve stroke color
                new_path.item_id = path.item_id + "_f" + str(counter)
                counter += 1
                new_path.subpaths = [subpath]
                new_paths.append(new_path)

        self.paths = new_paths


class DocDigest:
    """
    DocDigest: An object corresponding to a single SVG document, supporting
    a limited subset of SVG.

    Each DocDigest instance contains the following elements:
    - name: a string representing the file name or path; may be empty
    - width: a number representing the document width
    - height: a number representing the document height
    - viewbox: a string representing the SVG viewbox of the document
    - metadata: A dict for additional metadata items
    - plotdata: A dict for information about the plot
    - flat: a boolean indicating if the DocDigest has been flattened
    - layers: a list of LayerItem elements in the document

    """

    def __init__(self):
        self.name = ""        # Optional file name or path
        self.width = 0        # Document width, numeric
        self.height = 0       # Document height, numeric
        self.viewbox = ""     # SVG viewbox string
        self.plotdata = {}    # Dict for information about the plot
        self.metadata = {}    # Dict for additional metadata items
        self.flat = False     # Boolean indicating if the instance has been flattened.
        self.layers = []      # List of PathItem objects in the layer

        self.plotdata['plob_version'] = PLOB_VERSION

    def flatten(self):
        """
        Flatten all layers, so that each PathItem instance in each layer
        represents only a single subpath.
        """

        if not self.layers:
            return # No paths in the layer; nothing to flatten

        for layer in self.layers:
            layer.flatten()
        self.flat = True

    def rotate(self, rotate_ccw = True):
        """
        Rotate the document by 90 degrees, e.g., from portrait to landscape
        aspect ratio. Flatten the document prior to rotating if it is not
        already flattened.
        """

        old_width = self.width
        self.width = self.height
        self.height = old_width

        self.viewbox = "0 0 {:f} {:f}".format(self.width, self.height)

        if not self.flat:
            self.flatten()

        for layer_item in self.layers:
            for path in layer_item.paths:
                vertex_list = path.subpaths[0]

                if not vertex_list:
                    vertex_list = []
                    continue
                if len(vertex_list) < 2: # Skip paths with only one vertex
                    vertex_list = []
                    continue

                new_vertex_list = []
                for vertex in vertex_list:
                    [v_x, v_y] = vertex
                    if rotate_ccw:
                        new_vertex = [v_y, self.height - v_x]
                    else:
                        new_vertex = [self.width - v_y, v_x]
                    new_vertex_list.append(new_vertex)
                path.subpaths[0] = new_vertex_list

    def to_plob(self):
        """
        Convert the contents of the DocDigest object into an lxml etree "Plob"
        and return it.

        The Plob (Plot Object) format is a valid but highly-restricted subset
        of SVG. Only layers are allowed in the SVG root. Only polylines are
        allowed in layers. There are no other objects, nor object
        transformations or individual object styles.
        """

        plob = etree.fromstring(PLOB_BASE)
        plob.set('encoding', "UTF-8")

        plob.set('width', "{:f}in".format(self.width))
        plob.set('height', "{:f}in".format(self.height))

        plob.set('viewBox', str(self.viewbox))
        plob.set(inkex.addNS('docname', 'sodipodi'), self.name)

        if not self.flat:
            self.flatten()

        plob_metadata = etree.SubElement(plob, 'metadata')
        for key in self.metadata:
            plob_metadata.set(key, str(self.metadata[key]))

        plotdata = etree.SubElement(plob, 'plotdata')
        for key in self.plotdata:
            plotdata.set(key, self.plotdata[key])

        for layer in self.layers: # path is a LayerItem object.
            new_layer = etree.SubElement(plob, 'g') # Create new layer in root of self.plob
            new_layer.set(inkex.addNS('groupmode', 'inkscape'), 'layer')
            new_layer.set(inkex.addNS('label', 'inkscape'), layer.name)
            new_layer.set('id', layer.item_id)

            for path in layer.paths: # path is a PathItem object.
                poly_string = vertex_list_to_string(path.subpaths[0])
                if poly_string:
                    polyline_node = etree.SubElement(new_layer, 'polyline')
                    polyline_node.set('id', path.item_id)
                    polyline_node.set('points', poly_string)
        return plob

    def from_plob(self, plob):
        """
        Import data from an input "Plob" SVG etree object, and use it to
        populate the contents of this DocDigest object. Clobber any
        existing contents of the DocDigest object.

        This function is for use _only_ on an input etree that is in the Plob
        format, not a full SVG file with arbitrary contents.

        While documentation layers are not allowed as part of the plob,
        we will ignore them. That allows a preview to be run before plotting.
        """

        # Reset instance variables; ensure that they are clobbered.
        self.name = ""        # Optional file name or path
        self.width = 0        # Document width
        self.height = 0       # Document height
        self.viewbox = ""     # SVG viewbox string
        self.plotdata = {}    # Dict for information about the plot
        self.metadata = {}    # Dict for additional metadata items
        self.layers = []      # List of PathItem objects in the layer

        self.flat = True    # The input plob must already be flat.

        docname = plob.get(inkex.addNS('docname', 'sodipodi'))
        if docname:
            self.name = docname

        length_string = plob.get('width')
        if length_string:
            value, _units = plot_utils.parseLengthWithUnits(length_string)
            self.width = value

        length_string = plob.get('height')
        if length_string:
            value, _units = plot_utils.parseLengthWithUnits(length_string)
            self.height = value

        vb_temp = plob.get('viewBox')
        if vb_temp:
            self.viewbox = vb_temp

        for node in plob:
            if node.tag in ['g', inkex.addNS('g', 'svg')]:
                # A group that we treat as a layer
                name_temp = node.get(inkex.addNS('label', 'inkscape'))
                if not name_temp:
                    continue
                layer = LayerItem() # New LayerItem object
                layer.item_id = node.get('id')
                layer.name = name_temp
                if len(str(name_temp)) > 0:
                    if str(name_temp)[0] == '%':
                        continue # Skip Documentation layer and its contents
                for subnode in node:
                    if subnode.tag in ['polyline', inkex.addNS('polyline', 'svg')]:
                        path = PathItem() # New PathItem object
                        path.from_string(subnode.get('points'))
                        path.item_id = subnode.get('id')
                        layer.paths.append(path)
                self.layers.append(layer)
            if node.tag == 'metadata':
                self.metadata = dict(node.attrib)
            if node.tag == 'plotdata':
                self.plotdata = dict(node.attrib)


def vertex_list_to_string(vertex_list):
    """
    Given a list of 2-element lists defining XY coordinates, return a string
    that can be used as the "points" attribute within an SVG polyline.

    Input: list of lists, e.g., [[1, 2], [3, 4], [5, 6]]
    Output: string, e.g., "1,2 3,4 5,6"

    Return None in the case of nonexistent, improperly formatted, or
    too short (< 2 points) input list.
    """

    if not vertex_list:
        return None

    list_length = len(vertex_list)
    if list_length < 2:
        return None

    output = ""
    i = 0
    try:
        while i < (list_length):
            # String conversion: Use default fixed-point precision, 6-digits
            output += "{:f},{:f} ".format(vertex_list[i][0], vertex_list[i][1])
            i += 1
        return output[:-1] # Drop trailing space from string.
        # If there is no last character to drop, the exception will return None.
    except:
        return None


def polyline_string_to_list(polyline_string):
    """
    Given the "points" attribute string from an SVG polyline,
    return a list of 2-element lists that can be iterated over easily

    Input: string, e.g., "1,2 3,4 5,6"
    Output: list of lists, e.g., [[1, 2], [3, 4], [5, 6]]
    """

    if not polyline_string:
        return None

    try:
        return [[float(z) for z in y] for y in (x.split(',') for x in polyline_string.split())]
    except:
        return None
