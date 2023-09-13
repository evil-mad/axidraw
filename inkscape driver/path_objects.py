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
path_objects.py

Classes and functions for working with simplified path objects

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

The primary classes defined by this function are:
* DocDigest: An object corresponding to a single SVG document

* PathItem: An object corresponding to a single SVG path

* LayerItem: An object corresponding to a single SVG layer

In each case, the formats supported here are ones that can be mapped
to a very limited subset of SVG.

Also included is a LayerProperties class, which manages parsing of layer names.
"""

from math import sqrt
from enum import Enum
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

class FillRule(Enum):
    """
    Based on SVG fill rules: https://www.w3.org/TR/SVG2/painting.html#WindingRule
    """
    NONZERO = "nonzero"
    EVENODD = "evenodd"

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

    @classmethod
    def from_attrs(cls, **kwargs):
        ''' Populate class from attribute keywords '''
        path_item = cls()
        path_item.subpaths = kwargs.pop("subpaths", None)
        path_item.stroke = kwargs.pop("stroke", None)
        path_item.fill = kwargs.pop("fill", None)
        path_item.fill_rule = kwargs.pop("fill_rule", None)
        path_item.item_id = kwargs.pop("item_id", None)
        return path_item

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

    def length(self):
        """
        Return total path length; the sum of segment lengths for the path object.
        Intended for use on "flat" PathItem objects that only contain a single subpath.
        """
        if self.subpaths is None:
            return 0

        subpath = self.subpaths[0]
        vertex_count = len(subpath)
        vertex_count_less_1 = vertex_count - 1
        total_length = 0
        index = 0
        while index < (vertex_count_less_1):
            d_x = subpath[index+1][0] - subpath[index][0]
            d_y = subpath[index+1][1] - subpath[index][1]
            total_length += sqrt(d_x * d_x + d_y * d_y)
            index += 1
        return total_length


    def crop_by_distance(self, target):
        """
        Trace along the path, calculating the length of each segment, until the specified
            target distance along the path is reached.
        Remove all path segments before the target, and splice the segment where the target
            resides, removing the first vertex of that segment and replacing it with a new
            vertex (now the new first vertex) at the target distance along the original path.

        Intended for use on "flat" PathItem objects that only contain a single subpath.
        """
        if self.subpaths is None:
            return
        if target < 0:
            return
        subpath = self.subpaths[0]
        vertex_count = len(subpath)
        vertex_count_less_1 = vertex_count - 1

        subpath_length = 0
        index = 0
        while index < (vertex_count_less_1):
            d_x = subpath[index+1][0] - subpath[index][0]
            d_y = subpath[index+1][1] - subpath[index][1]
            this_seg_dist = sqrt(d_x * d_x + d_y * d_y)
            if (subpath_length + this_seg_dist) > target:
                break
            index += 1
            subpath_length += this_seg_dist

        if index == vertex_count_less_1:
            subpath[:] = [] # Target is past the end of this subpath; crop entire subpath.
            return

        new_seg_fraction = (target - subpath_length)/this_seg_dist
        d_x = d_x * new_seg_fraction
        d_y = d_y * new_seg_fraction
        subpath[index][0] = subpath[index][0] + d_x
        subpath[index][1] = subpath[index][1] + d_y
        subpath[:] = subpath[index:]


    def closed(self):
        """
        If PathItem contains only a single closed subpath, return True
        Tolerance is of 0.0001 inch
        """
        if self.subpaths:
            if len(self.subpaths) == 1:
                return plot_utils.points_near(self.subpaths[0][0], self.subpaths[0][-1],\
                    .00000001)
        return False

    def has_stroke(self):
        """
        return False if self.stroke is None, "none", "None", etc., else True
        """
        return str(self.stroke).lower() != "none"

    def reverse(self):
        """
        If PathItem contains only a single subpath, reverse it.
        In practice, this reverses the direction that the path will be drawn.
        """
        if self.subpaths:
            if len(self.subpaths) == 1:
                self.subpaths[0].reverse()

    @classmethod
    def equal_lists_of_points(cls, points_a, points_b):
        """
        simple comparison of lists of points
        """
        if len(points_a) != len(points_b):
            return False

        for point_a, point_b in zip(points_a, points_b):
            if not plot_utils.points_equal(point_a, point_b):
                return False
        return True

    def __str__(self):
        ''' For builtin `str(path_item)` and `print(path_item)` to work nicely '''

        return f"{type(self).__name__}(\n  subpaths={self.subpaths},\n" +\
            f"  fill={self.fill},\n  fill_rule={self.fill_rule},\n" +\
            f"  stroke={self.stroke},\n  item_id={self.item_id})"

def find_int(name_string):
    '''
    Find a continuous integer, starting at the given position in a string.
    If found, return integer, remaining string after the integer.
    Else, return None, and the original string.
    '''

    temp_num_string = 'x'
    string_pos = 1
    while string_pos <= len(name_string):
        layer_name_fragment = name_string[:string_pos]
        if layer_name_fragment.isdigit():
            temp_num_string = name_string[:string_pos]
            string_pos += 1
        else:
            break
    if str.isdigit(temp_num_string):
        return int(float(temp_num_string)), name_string[len(temp_num_string):]
    return None, name_string


class LayerProperties: # pylint: disable=too-many-instance-attributes
    """
    Minor class for parsing and storing layer name properties
    https://wiki.evilmadscientist.com/AxiDraw_Layer_Control
    """

    def __init__(self):
        self.skip = False   # If true, a non-printing layer (e.g., documentation or hidden)
        self.number = None  # Layer "number" for the purposes of printing specific layers
        self.pause = False  # If True, force a pause at the beginning of the layer
        self.delay = None   # Delay (ms) at beginning of layer
        self.speed = None   # Defined pen-down speed for the layer
        self.height = None  # Defined pen-down height for the layer
        self.text = ""      # Extra text in the layer name, e.g., human-readable name.

    def parse(self, layer_name):
        '''
        Populate the LayerProperties instance variables from the string layer_name.
        '''

        if not layer_name: # Layer name is None; nothing to do
            return
        layer_name.strip() # Remove whitespace
        if len(layer_name) == 0:
            return # Empty layer name
        if str(layer_name)[0] == '%':
            self.skip = True    # A non-printing "documentation layer"
            self.text = layer_name[1:]
            return
        if str(layer_name)[0] == '!':
            self.pause = True   # Force a pause when beginning this layer
            layer_name = layer_name[1:] # Strip leading '!'

        self.number, remainder = find_int(layer_name)

        while len(remainder) >= 3:
            key = remainder[:2].lower()
            if key in ['+h', '+s', '+d']:
                remainder = remainder[2:]
                number_temp, remainder = find_int(remainder)
                if number_temp is not None:
                    if key == "+d":
                        if number_temp > 0: # Delay time, ms
                            self.delay = number_temp
                    if key == "+h":
                        if 0 <= number_temp <= 100:
                            self.height = number_temp
                    if key == "+s":
                        if 1 <= number_temp <= 110:
                            self.speed = number_temp
            else:
                self.text = remainder
                break

    def compose(self):
        '''
        Return a layer name string in a standardized format.
        '''
        name_string = ""
        if self.skip:
            return "%" + self.text
        if self.pause:
            name_string = "!"
        if self.number is not None:
            name_string += f"{self.number}"
        if self.delay is not None:
            name_string += f"+d{self.delay}"
        if self.height is not None:
            name_string += f"+h{self.height}"
        if self.speed is not None:
            name_string += f"+s{self.speed}"
        return name_string + self.text

class LayerItem: # pylint: disable=too-few-public-methods
    """
    LayerItem: An object corresponding to a single SVG layer

    Each LayerItem instance contains the following elements:
    - name, a string representing the name of the layer
    - paths, a list of PathItem elements in the layer
    - item_id: A unique ID string
    - props: A LayerProperties object, containing properties parsed from the name.

    The "name" variable is for reference. Properties encoded in the layer name
        should be stored in self.props
    """

    def __init__(self):
        self.name = ""                  # Name of the layer, for reference only
        self.paths = []                 # List of PathItem objects in the layer
        self.item_id = None             # ID string
        self.props = LayerProperties()  # LayerProperties object

    @classmethod
    def from_attrs(cls, **kwargs):
        ''' Populate class from attribute keywords '''
        layer_item = cls()
        layer_item.name = kwargs.pop("name", None)
        layer_item.paths = kwargs.pop("paths", None)
        layer_item.item_id = kwargs.pop("item_id", None)
        return layer_item

    def flatten(self):
        """
        Flatten all PathItem objects in the LayerItem, so that each
        PathItem instance represents only a single subpath.
        Remove fill color, fill rule, stroke.
        """

        if not self.paths:
            return # No paths in the layer; nothing to flatten

        new_paths = [] # Empty list for new path items

        for path in self.paths:
            if len(path.subpaths) == 1: # This path is already flat
                path.stroke = None
                path.fill = None
                path.fill_rule = None
                new_paths.append(path)
                continue
            counter = 0
            for subpath in path.subpaths: # Make new PathItem objects
                new_path = PathItem()
                new_path.item_id = path.item_id + "_f" + str(counter)
                counter += 1
                new_path.subpaths = [subpath]
                new_paths.append(new_path)

        self.paths = new_paths

    def parse_name(self, layer_name=None):
        """
        Populate self.props, a LayerProperties object, from the string layer_name or None.
        If None, use self.name as the input string
        Used when parsing SVG document into a digest.
        """
        if layer_name is None:
            self.props.parse(self.name)
        else:
            self.props.parse(layer_name)

    def compose_name(self):
        """
        Return a layer name string in a standardized format, from the values in self.props.
        Used when generating an SVG plob from the digest.
        """
        return self.props.compose()


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

        if self.flat:
            return # Already flat; leave it alone.
        if not self.layers:
            return # No paths in the layer; nothing to flatten

        for layer in self.layers:
            layer.flatten()
        self.flat = True

    def remove_unstroked(self):
        ''' For use with hidden path removal, remove paths without a stroke'''
        for layer in self.layers:
            layer.paths = list(filter(lambda p: str(p.stroke).lower() != "none", layer.paths))


    def layer_filter(self, layer_number):
        """
        If layer_number >= 0, indicating that we are only plotting certain layers,
            remove layers that do not match the pattern.
        """
        if layer_number < 0: # if not plotting in layers mode
            return
        for index in reversed(range(len(self.layers))): # Iterate backwards; removing items!
            layer = self.layers[index]
            if layer.props.number is None or layer.props.number != layer_number:
                del self.layers[index]


    def rotate(self, rotate_ccw = True):
        """
        Rotate the document by 90 degrees, e.g., from portrait to landscape
        aspect ratio.
        """

        old_width = self.width
        self.width = self.height
        self.height = old_width

        self.viewbox = f"0 0 {self.width:f} {self.height:f}"

        for layer_item in self.layers:
            for path in layer_item.paths:
                new_subpaths = []
                for vertex_list in path.subpaths:
                    if len(vertex_list) < 2: # Skip paths with only one vertex
                        vertex_list.clear()
                        continue

                    new_vertex_list = []
                    for vertex in vertex_list:
                        [v_x, v_y] = vertex
                        if rotate_ccw:
                            new_vertex = [v_y, self.height - v_x]
                        else:
                            new_vertex = [self.width - v_y, v_x]
                        new_vertex_list.append(new_vertex)
                    new_subpaths.append(new_vertex_list)
                path.subpaths = new_subpaths

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

        plob.set('width', f"{self.width:f}in")
        plob.set('height', f"{self.height:f}in")

        plob.set('viewBox', str(self.viewbox))
        plob.set(inkex.addNS('docname', 'sodipodi'), self.name)

        if not self.flat:
            self.flatten()

        plob_metadata = etree.SubElement(plob, 'metadata')
        for key, value in self.metadata.items():
            plob_metadata.set(key, str(value))

        plotdata = etree.SubElement(plob, 'plotdata')
        for key, value in self.plotdata.items():
            plotdata.set(key, str(value))

        for layer in self.layers: # path is a LayerItem object.
            new_layer = etree.SubElement(plob, 'g') # Create new layer in root of self.plob
            new_layer.set(inkex.addNS('groupmode', 'inkscape'), 'layer')

            if layer.name == '__digest-root__':
                new_layer.set(inkex.addNS('label', 'inkscape'), layer.name)
            else:
                layer_name_temp = layer.compose_name()
                if layer_name_temp == "":
                    layer_name_temp = f"layer_{layer.item_id}"
                new_layer.set(inkex.addNS('label', 'inkscape'), layer_name_temp)
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
                layer.parse_name()
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

    def crop(self, distance):
        """
        Remove the initial portion of a DocDigest object to prepare for plotting the
        remaining portion. For use only on a flattened digest, after optimizations.

        Inputs:
            distance: Pen-down distance through the plot at which to resume plotting.

        All complete path elements that occur before distance is will be omitted.
        If distance occurs within a path, splice that path and remove the first part of it.

        If we are resuming from the beginning of a layer that has a time delay at
        the beginning of the layer, we do include that time delay (but skip past any
        programmatic pause that may have already occurred). If we are beginning in a
        layer that has a time delay, but *after* the time delay, strip out that delay.
        """
        if distance <= 0:
            return

        dist_so_far = 0 # Distance counter for cropping

        # Step through document by plot digest path distances.
        #   Remove any paths that we are past
        #   Remove any full layers that we are past
        #   Remove pause from the layer that we are resuming at
        #   If we are resuming until some mid-point in a layer (not the beginning),
        #       then remove any time delay at the beginning of that layer.

        splice_made = False
        for layer in self.layers:
            start_index = 0
            for path in layer.paths:

                path_length = path.length()
                skip_length_tol = min(path_length/100, 0.001) # Tighter tolerance for short paths
                if (dist_so_far + path_length) <= (distance + skip_length_tol):
                    dist_so_far += path_length
                    start_index += 1 # This count will be used to slice the path out.
                    layer.props.delay = None # No delay, since not on first path of layer.
                    continue

                if distance > dist_so_far:
                    layer.props.delay = None # No delay, splice is after beginning of path
                    # Crop that path partway, right at our target distance:
                    target = distance - dist_so_far
                    path.crop_by_distance(target)
                layer.props.pause = False
                splice_made = True
                break

            layer.paths = layer.paths[start_index:] # Slice out paths to skip

            if len(layer.paths) == 0:
                layer.name = "__MARKED_FOR_DELETION__"

            if splice_made:
                break

        self.layers[:] = [layer_tmp for layer_tmp in self.layers \
            if layer_tmp.name != "__MARKED_FOR_DELETION__"]


    def length(self):
        """
        Return total path length; the sum of segment lengths for all paths in the digest.
        For use on "flat" DocDigest objects, where each PathItem contains a single subpath.
        """
        total_length = 0
        for layer in self.layers:
            for path in layer.paths:
                total_length += path.length()
        return total_length


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
            output += f"{vertex_list[i][0]:f},{vertex_list[i][1]:f} "
            i += 1
        return output[:-1] # Drop trailing space from string.
    except IndexError:
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
