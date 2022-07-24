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
digest_svg.py

Routines for digesting an input SVG file into a simplified SVG ("Plob")
formats for easier processing

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

Requires Python 3.6 or newer and Pyserial 3.5 or newer.
"""

import logging
from math import sqrt

from lxml import etree

from axidrawinternal.plot_utils_import import from_dependency_import # plotink
path_objects = from_dependency_import('axidrawinternal.path_objects')
simplepath = from_dependency_import('ink_extensions.simplepath')
simplestyle = from_dependency_import('ink_extensions.simplestyle')
cubicsuperpath = from_dependency_import('ink_extensions.cubicsuperpath')
simpletransform = from_dependency_import('ink_extensions.simpletransform')
inkex = from_dependency_import('ink_extensions.inkex')
message = from_dependency_import('ink_extensions_utils.message')
# https://github.com/evil-mad/plotink
plot_utils = from_dependency_import('plotink.plot_utils')

logger = logging.getLogger(__name__)


class DigestSVG:
    """
    Main class for parsing SVG document and "digesting" it into a
    path_objects.DocDigest object, a heavily simplified representation of the
    SVG contents.
    """

    logging_attrs = {"default_handler": message.UserMessageHandler()}
    spew_debugdata = False

    def __init__(self, default_logging=True):
        # Create instance variables

        if default_logging:
            logger.setLevel(logging.INFO)
            logger.addHandler(self.logging_attrs["default_handler"])
        if self.spew_debugdata:
            logger.setLevel(logging.DEBUG) # by default level is INFO

        self.use_tag_nest_level = 0
        self.current_layer = None
        self.current_layer_name = ""
        self.next_id = 0
        self.warning_text = ""

        self.doc_digest = path_objects.DocDigest()

        self.style_dict = {}
        self.style_dict['fill'] = None
        self.style_dict['stroke'] = None
        self.style_dict['fill_rule'] = None

        # Variables that will be populated in process_svg():
        self.warnings = {}
        self.bezier_tolerance = 0
        self.supersample_tolerance = 0
        self.layer_selection = 0

        self.doc_width_100 = 0
        self.doc_height_100 = 0
        self.diagonal_100 = 0


    def process_svg(self, node_list, digest_params,  mat_current=None):
        """
        Wrapper around routine to recursively traverse an SVG document.

        This calls the recursive routine and handles building the digest
        structure around it, as well as reporting any necessary errors.

        Inputs:
        node_list, an lxml etree representing an SVG document
        digest_params, a tuple with additional parameters
        mat_current, a transformation matrix

        From the SVG, build and return a path_objects.DocDigest object; a
        python object representing a simplified SVG document. Once flattened,
        the digest can be converted to a Plob file if desired.

        The Plob (Plot Object) format is a highly-restricted subset of SVG.
            Only layers are allowed in the SVG root. Only polylines are allowed
            in layers. There are no other objects, nor object transformations
            or styles.
        """

        [self.doc_digest.width, self.doc_digest.height, scale_x, scale_y, self.layer_selection,\
            self.bezier_tolerance, self.supersample_tolerance, _]\
            = digest_params

        # Store document information in doc_digest
        self.doc_digest.viewbox = "0 0 {:f} {:f}".format(\
            self.doc_digest.width, self.doc_digest.height)

        self.doc_width_100 = self.doc_digest.width / scale_x    # Width of a "100% width" object
        self.doc_height_100 = self.doc_digest.height / scale_y  # height of a "100% height" object
        self.diagonal_100 = sqrt((self.doc_width_100)**2 + (self.doc_height_100)**2)/sqrt(2)

        docname = node_list.get(inkex.addNS('docname', 'sodipodi'), )
        if docname:
            self.doc_digest.name = docname

        root_layer = path_objects.LayerItem()
        # Flag to identify layers containing objects from root
        root_layer.name = '__digest-root__'
        root_layer.item_id = str(self.next_id)
        self.next_id += 1
        self.doc_digest.layers.append(root_layer)

        self.current_layer = root_layer # Layer that graphical elements should be added to
        self.current_layer_name = root_layer.name

        self.traverse(node_list, mat_current)
        return self.doc_digest


    def traverse(self, node_list, mat_current=None,\
            parent_visibility='visible'):
        """
        Recursively traverse the SVG file and process all of the paths. Keep
        track of the composite transformation applied to each path.

        Inputs:
        node_list, an lxml etree representing an SVG document
        mat_current, a transformation matrix
        parent_visibility, string

        This function handles path, group, line, rect, polyline, polygon,
        circle, ellipse  and use (clone) elements. Notable elements not handled
        include text. Unhandled elements should be converted to paths in
        Inkscape or another vector graphics editor.
        """

        # Future work:
        #       Ensure that fill and stroke attributes are correctly inherited
        #       from parents where applicable. E.g., If a group has a stroke.
        #       Guideline: Match Inkscape's style inheritance behavior

        if mat_current is None:
            mat_current = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

        for node in node_list:
            element_style = simplestyle.parseStyle(node.get('style'))

            # Check for "display:none" in the node's style attribute:
            if 'display' in element_style.keys() and element_style['display'] == 'none':
                continue  # Do not plot this object or its children
            # The node may have a display="none" attribute as well:
            if node.get('display') == 'none':
                continue  # Do not plot this object or its children

            # Visibility attributes control whether a given object will plot.
            # Children of hidden (not visible) parents may be plotted if
            # they assert visibility.
            visibility = node.get('visibility', parent_visibility)
            if visibility == 'inherit':
                visibility = parent_visibility

            if 'visibility' in element_style.keys():
                visibility = element_style['visibility'] # Style may override attribute.

            # first apply the current matrix transform to this node's transform
            mat_new = simpletransform.composeTransform(mat_current, \
                simpletransform.parseTransform(node.get("transform")))

            if node.tag == inkex.addNS('g', 'svg') or node.tag == 'g':

                old_layer_name = self.current_layer_name
                if old_layer_name == '__digest-root__' and\
                    node.get(inkex.addNS('groupmode', 'inkscape')) == 'layer':
                    # Ensure that sublayers are treated like regular groups only

                    str_layer_name = node.get(inkex.addNS('label', 'inkscape'))

                    if not str_layer_name:
                        str_layer_name = "Auto-Layer " + str(self.next_id)
                        self.next_id += 1
                    else:
                        str_layer_name.lstrip()  # Remove leading whitespace
                        if len(str(str_layer_name)) > 0:
                            if str(str_layer_name)[0] == '%':
                                continue # Skip Documentation layer and its contents

                    if self.layer_selection >= 0 and len(str(str_layer_name)) > 0: # layers mode
                        layer_match = False
                        layer_name_int = -1
                        temp_num_string = 'x'
                        string_pos = 1

                        layer_name_temp = str(str_layer_name) # Ignore leading '!' in layers mode
                        if str(str_layer_name)[0] == '!':
                            layer_name_temp = str_layer_name[1:]

                        max_length = len(layer_name_temp)
                        while string_pos <= max_length:
                            layer_name_fragment = layer_name_temp[:string_pos]
                            if layer_name_fragment.isdigit():
                                temp_num_string = layer_name_temp[:string_pos]
                                string_pos += 1
                            else:
                                break

                        if str.isdigit(temp_num_string):
                            layer_name_int = int(float(temp_num_string))
                            if self.layer_selection == layer_name_int:
                                layer_match = True
                        if not layer_match:
                            continue # Skip this layer and its contents

                    new_layer = path_objects.LayerItem()
                    new_layer.name = str_layer_name
                    new_layer.item_id = str(self.next_id)
                    self.next_id += 1
                    self.doc_digest.layers.append(new_layer)
                    self.current_layer = new_layer
                    self.current_layer_name = str(str_layer_name)

                    self.traverse(node, mat_new, parent_visibility=visibility)

                    # After parsing a layer, add a new "root layer" for any objects
                    # that may appear in root before the next layer:

                    new_layer = path_objects.LayerItem()
                    new_layer.name = '__digest-root__' # Label this as a "root" layer
                    new_layer.item_id = str(self.next_id)
                    self.next_id += 1
                    self.doc_digest.layers.append(new_layer)
                    self.current_layer = new_layer
                    self.current_layer_name = new_layer.name
                else: # Regular group or sublayer that we treat as a group.
                    self.traverse(node, mat_new, parent_visibility=visibility)
                continue

            if node.tag == inkex.addNS('symbol', 'svg') or node.tag == 'symbol':
                # A symbol is much like a group, except that it should only
                #       be rendered when called within a "use" tag.
                if self.use_tag_nest_level > 0:
                    self.traverse(node, mat_new, parent_visibility=visibility)
                continue

            if node.tag == inkex.addNS('a', 'svg') or node.tag == 'a':
                # An 'a' is much like a group, in that it is a generic container element.
                self.traverse(node, mat_new, parent_visibility=visibility)
                continue

            if node.tag == inkex.addNS('switch', 'svg') or node.tag == 'switch':
                # A 'switch' is much like a group, in that it is a generic container element.
                # We are not presently evaluating conditions on switch elements, but parsing
                # their contents to the extent possible.
                self.traverse(node, mat_new, parent_visibility=visibility)
                continue

            if node.tag == inkex.addNS('use', 'svg') or node.tag == 'use':
                """
                A <use> element refers to another SVG element via an xlink:href="#blah"
                attribute.  We will handle the element by doing an XPath search through
                the document, looking for the element with the matching id="blah"
                attribute.  We then recursively process that element after applying
                any necessary (x,y) translation.

                Notes:
                 1. We ignore the height and g attributes as they do not apply to
                    path-like elements, and
                 2. Even if the use element has visibility="hidden", SVG still calls
                    for processing the referenced element.  The referenced element is
                    hidden only if its visibility is "inherit" or "hidden".
                 3. We may be able to unlink clones using the code in pathmodifier.py
                """

                refid = node.get(inkex.addNS('href', 'xlink'))
                if refid is not None:
                    # [1:] to ignore leading '#' in reference
                    path = '//*[@id="{0}"]'.format(refid[1:])
                    refnode = node.xpath(path)
                    if refnode is not None:
                        x_val = float(node.get('x', '0'))
                        y_val = float(node.get('y', '0'))
                        # Note: the transform has already been applied
                        if x_val != 0 or y_val != 0:
                            mat_new2 = simpletransform.composeTransform(mat_new,\
                            simpletransform.parseTransform(\
                            'translate({0:.6E},{1:.6E})'.format(x_val, y_val)))
                        else:
                            mat_new2 = mat_new
                        visibility = node.get('visibility', visibility)
                        self.use_tag_nest_level += 1 # Keep track of nested "use" elements.
                        self.traverse(refnode, mat_new2, parent_visibility=visibility)
                        self.use_tag_nest_level -= 1
                continue

            # End container elements; begin graphical elements.

            if self.layer_selection >= 0:
                if self.current_layer_name == '__digest-root__':
                    continue # Do not print root elements if layer_selection >= 0

            if visibility in ('hidden', 'collapse'):
                # Do not plot this node if it is not visible.
                # This comes after use, a, and group tags because
                # items within a hidden item may be visible.
                continue

            element_style = simplestyle.parseStyle(node.get('style'))

            if 'fill' in element_style.keys():
                self.style_dict['fill'] = element_style['fill']
            else:
                self.style_dict['fill'] = None

            if 'stroke' in element_style.keys():
                self.style_dict['stroke'] = element_style['stroke']
            else:
                self.style_dict['stroke'] = None

            fill_rule = node.get('fill-rule')
            if fill_rule:
                self.style_dict['fill_rule'] = fill_rule
            else:
                self.style_dict['fill_rule'] = None

            if node.tag == inkex.addNS('path', 'svg'):
                path_d = node.get('d')
                self.digest_path(path_d, mat_new)
                continue
            if node.tag == inkex.addNS('rect', 'svg') or node.tag == 'rect':
                """
                Create a path with the outline of the rectangle
                Manually transform  <rect x="X" y="Y" width="W" height="H"/>
                    into            <path d="MX,Y lW,0 l0,H l-W,0 z"/>
                Draw three sides of the rectangle explicitly and the fourth implicitly
                https://www.w3.org/TR/SVG11/shapes.html#RectElement
                """

                x, r_x, width = [plot_utils.unitsToUserUnits(node.get(attr),
                    self.doc_width_100) for attr in ['x', 'rx', 'width']]
                y, r_y, height = [plot_utils.unitsToUserUnits(node.get(attr),
                    self.doc_height_100) for attr in ['y', 'ry', 'height']]

                def calc_r_attr(attr, other_attr, twice_maximum):
                    value = (attr if attr is not None else
                             other_attr if other_attr is not None else
                             0)
                    return min(value, twice_maximum * .5)

                r_x = calc_r_attr(r_x, r_y, width)
                r_y = calc_r_attr(r_y, r_x, height)

                instr = []
                if (r_x > 0) or (r_y > 0):
                    instr.append(['M ', [x + r_x, y]])
                    instr.append([' L ', [x + width - r_x, y]])
                    instr.append([' A ', [r_x, r_y, 0, 0, 1, x + width, y + r_y]])
                    instr.append([' L ', [x + width, y + height - r_y]])
                    instr.append([' A ', [r_x, r_y, 0, 0, 1, x + width - r_x, y + height]])
                    instr.append([' L ', [x + r_x, y + height]])
                    instr.append([' A ', [r_x, r_y, 0, 0, 1, x, y + height - r_y]])
                    instr.append([' L ', [x, y + r_y]])
                    instr.append([' A ', [r_x, r_y, 0, 0, 1, x + r_x, y]])
                else:
                    instr.append(['M ', [x, y]])
                    instr.append([' L ', [x + width, y]])
                    instr.append([' L ', [x + width, y + height]])
                    instr.append([' L ', [x, y + height]])
                    instr.append([' L ', [x, y]])

                self.digest_path(simplepath.formatPath(instr), mat_new)
                continue
            if node.tag == inkex.addNS('line', 'svg') or node.tag == 'line':
                """
                Convert an SVG line object  <line x1="X1" y1="Y1" x2="X2" y2="Y2/>
                to an SVG path object:      <path d="MX1,Y1 LX2,Y2"/>
                """
                x_1, x_2 = [plot_utils.unitsToUserUnits(node.get(attr, '0'),
                    self.doc_width_100) for attr in ['x1', 'x2']]
                y_1, y_2 = [plot_utils.unitsToUserUnits(node.get(attr, '0'),
                    self.doc_height_100) for attr in ['y1', 'y2']]

                path_a = []
                path_a.append(['M ', [x_1, y_1]])
                path_a.append([' L ', [x_2, y_2]])
                self.digest_path(simplepath.formatPath(path_a), mat_new)
                continue

            if node.tag in [inkex.addNS('polyline', 'svg'), 'polyline',
                              inkex.addNS('polygon', 'svg'), 'polygon']:
                """
                Convert
                 <polyline points="x1,y1 x2,y2 x3,y3 [...]"/>
                OR
                 <polyline points="x1 y1 x2 y2 x3 y3 [...]"/>
                OR
                 <polygon points="x1,y1 x2,y2 x3,y3 [...]"/>
                OR
                 <polygon points="x1 y1 x2 y2 x3 y3 [...]"/>
                to
                  <path d="Mx1,y1 Lx2,y2 Lx3,y3 [...]"/> (with a closing Z on polygons)
                Ignore polylines with no points, or polylines with only a single point.
                """

                pl = node.get('points', '').strip()
                if pl == '':
                    continue
                pa = pl.replace(',', ' ').split() # replace comma with space before splitting
                if not pa:
                    continue
                path_length = len(pa)
                if path_length < 4:  # Minimum of x1,y1 x2,y2 required.
                    continue
                path_d = "M " + pa[0] + " " + pa[1]
                i = 2
                while i < (path_length - 1):
                    path_d += " L " + pa[i] + " " + pa[i + 1]
                    i += 2
                if node.tag in [inkex.addNS('polygon', 'svg'), 'polygon']:
                    path_d += " Z"

                self.digest_path(path_d, mat_new) # Vertices are already in user coordinate system
                continue
            if node.tag in [inkex.addNS('ellipse', 'svg'), 'ellipse',
                              inkex.addNS('circle', 'svg'), 'circle']:
                """
                Convert circles and ellipses to paths as two 180 degree arcs.
                In general (an ellipse), we convert
                  <ellipse rx="RX" ry="RY" cx="X" cy="Y"/>
                to
                  <path d="MX1,CY A RX,RY 0 1 0 X2,CY A RX,RY 0 1 0 X1,CY"/>
                where
                  X1 = CX - RX
                  X2 = CX + RX
                Ellipses or circles with a radius attribute of 0 are ignored
                """

                if node.tag in [inkex.addNS('circle', 'svg'), 'circle']:
                    r_x = plot_utils.unitsToUserUnits(node.get('r', '0'), self.diagonal_100)
                    r_y = r_x
                else:
                    r_x, r_y = [plot_utils.unitsToUserUnits(node.get(attr, '0'),
                        self.diagonal_100) for attr in ['rx', 'ry']]
                if r_x == 0 or r_y == 0:
                    continue

                c_x = plot_utils.unitsToUserUnits(node.get('cx', '0'), self.doc_width_100)
                c_y = plot_utils.unitsToUserUnits(node.get('cy', '0'), self.doc_height_100)

                x_1 = c_x - r_x
                x_2 = c_x + r_x
                path_d = 'M {0:f},{1:f} '.format(x_1, c_y) + \
                         'A {0:f},{1:f} '.format(r_x, r_y) + \
                         '0 1 0 {0:f},{1:f} '.format(x_2, c_y) + \
                         'A {0:f},{1:f} '.format(r_x, r_y) + \
                         '0 1 0 {0:f},{1:f}'.format(x_1, c_y)
                self.digest_path(path_d, mat_new)
                continue
            if node.tag == inkex.addNS('metadata', 'svg') or node.tag == 'metadata':
                self.doc_digest.metadata.update(dict(node.attrib))
                continue
            if node.tag == inkex.addNS('plotdata', 'svg') or node.tag == 'plotdata':
                self.doc_digest.plotdata.update(dict(node.attrib))
                continue
            if node.tag == inkex.addNS('defs', 'svg') or node.tag == 'defs':
                continue
            if node.tag == inkex.addNS('namedview', 'sodipodi') or node.tag == 'namedview':
                continue
            if node.tag in ['eggbot', 'WCB', 'MergeData', inkex.addNS('eggbot', 'svg'),
                 inkex.addNS('WCB', 'svg'), inkex.addNS('MergeData', 'svg'),]:
                continue
            if node.tag == inkex.addNS('title', 'svg') or node.tag == 'title':
                continue
            if node.tag == inkex.addNS('desc', 'svg') or node.tag == 'desc':
                continue
            if node.tag in [inkex.addNS('text', 'svg'), 'text',
                              inkex.addNS('flowRoot', 'svg'), 'flowRoot']:
                if 'text' not in self.warnings:
                    if self.current_layer_name == '__digest-root__':
                        temp_text = ', in the document root.'
                    else:
                        temp_text = ', found in a layer named "' +\
                                        self.current_layer_name + '" .'
                    text = 'Note: This file contains some plain text' + temp_text
                    text += '\nPlease convert your text into paths before drawing, '
                    text += 'using Path > Object to Path.'
                    text += '\nAlternately use Hershey Text to render the text '
                    text += 'with stroke-based fonts.\n'

                    self.warning_text += text
                    self.warnings['text'] = 1
                continue
            if node.tag == inkex.addNS('image', 'svg') or node.tag == 'image':
                if 'image' not in self.warnings:

                    if self.current_layer_name == '__digest-root__':
                        temp_text = ', in the document root.'
                    else:
                        temp_text = ', found in a layer named "' +\
                                        self.current_layer_name + '" .'
                    text = 'Note: This file contains a bitmap image' + temp_text
                    text += 'Please convert images to vectors before drawing. '
                    text += 'Consider using the Path > Trace bitmap tool.\n'
                    self.warning_text += text
                    self.warnings['image'] = 1
                continue
            if node.tag == inkex.addNS('pattern', 'svg') or node.tag == 'pattern':
                continue
            if node.tag == inkex.addNS('radialGradient', 'svg') or node.tag == 'radialGradient':
                continue  # Similar to pattern
            if node.tag == inkex.addNS('linearGradient', 'svg') or node.tag == 'linearGradient':
                continue  # Similar in pattern
            if node.tag == inkex.addNS('style', 'svg') or node.tag == 'style':
                # This is a reference to an external style sheet and not the value
                # of a style attribute to be inherited by child elements
                continue
            if node.tag == inkex.addNS('cursor', 'svg') or node.tag == 'cursor':
                continue
            if node.tag == inkex.addNS('font', 'svg') or node.tag == 'font':
                continue
            if node.tag == inkex.addNS('templateinfo', 'inkscape'):
                continue
            if node.tag == etree.Comment:
                continue
            if node.tag == inkex.addNS('color-profile', 'svg') or node.tag == 'color-profile':
                continue
            if node.tag in [inkex.addNS('foreignObject', 'svg'), 'foreignObject']:
                continue
            if not isinstance(node.tag, str):
                # This is likely an XML processing instruction such as an XML
                # comment. lxml uses a function reference for such node tags
                # and as such the node tag is likely not a printable string.
                # Converting it to a printable string likely won't be useful.
                continue
            if str(node.tag) not in self.warnings:
                text = str(node.tag).split('}')
                if self.current_layer_name == '__digest-root__':
                    layer_description = "found in file. "
                else:
                    layer_description = 'in layer "' + self.current_layer_name + '".'
                text = 'Warning: unable to plot <' + str(text[-1]) + '> object'
                text += layer_description + 'Please convert it to a path first.\n'
                self.warning_text += text
                self.warnings[str(node.tag)] = 1


    def digest_path(self, path_d, mat_transform):
        """
        Parse the path while applying the matrix transformation mat_transform.
        - Input is the "d" string attribute from an SVG path.
        - Turn this path into a cubicsuperpath (list of beziers).
        - Subdivide the cubic path into a list, rendering to straight segments within tolerance.
        - Identify subpaths within each path
        - Build a path_objects.PathItem object and append it to the current layer
        """

        logger.debug('digest_path()\n')
        # logger.debug('path d: ' + path_d)

        if len(simplepath.parsePath(path_d)) == 0:
            logger.debug('path length is zero, will not be plotted.')
            return

        parsed_path = cubicsuperpath.parsePath(path_d)

        # Apply the transformation to each point
        simpletransform.applyTransformToPath(mat_transform, parsed_path)

        subpaths = []

        # p is now a list of lists of cubic beziers [control pt1, control pt2, endpoint]
        # where the start-point is the last point in the previous segment.
        for subpath in parsed_path: # for subpaths in the path:
            vertex_list = []

            # Divide each path into a set of straight segments:
            plot_utils.subdivideCubicPath(subpath, self.bezier_tolerance)

            for vertex in subpath:
                # Pick out vertex location information from cubic bezier curve:
                vertex_list.append([float(vertex[1][0]), float(vertex[1][1])])
            if len(vertex_list) < 2:
                continue # At least two points required for a path
            if self.supersample_tolerance > 0:
                plot_utils.supersample(vertex_list, self.supersample_tolerance)
            if len(vertex_list) < 2:
                continue # At least two points required for a path
            subpaths.append(vertex_list)

        if len(subpaths) == 0:
            return # At least one sub-path required

        new_path = path_objects.PathItem()
        new_path.fill = self.style_dict['fill']
        new_path.stroke = self.style_dict['stroke']
        new_path.fill_rule = self.style_dict['fill_rule']
        new_path.item_id = str(self.next_id)
        self.next_id += 1

        new_path.subpaths = subpaths

        # Add new list of subpaths to the current "LayerItem" element:
        self.current_layer.paths.append(new_path)

        logger.debug('End of digest_path()\n')


def verify_plob(svg, model):
    """
    Check to see if the provided SVG is a valid plob that can be automatically converted
    to a plot digest object. Also check that the plob version and hardware model match.

    Returns True or False.

    We may wish to also check for an application name match in the
    future. At present, that check is not yet necessary.
    """

    data_node = None
    nodes = svg.xpath("//*[self::svg:plotdata|self::plotdata]", namespaces=inkex.NSS)
    if nodes:
        data_node = nodes[0]
    if data_node is not None:
        try:
            svg_model = data_node.get('model')
            svg_plob_version = data_node.get('plob_version')
        except TypeError:
            return False
    else:
        return False # No plot data; Plob cannot be verified.
    if svg_model:
        if int(svg_model) != model:
            return False
    else:
        return False
    if svg_plob_version:
        if svg_plob_version != path_objects.PLOB_VERSION:
            return False
    else:
        return False

    # inkex.errormsg( "Passed plotdata checks") # Optional halfwaypoint check
    tag_list = [inkex.addNS('defs', 'svg'), 'defs', 'metadata', inkex.addNS('metadata', 'svg'),
        inkex.addNS('namedview', 'sodipodi'), 'plotdata', inkex.addNS('plotdata', 'svg'), ]

    for node in svg:
        if node.tag in ['g', inkex.addNS('g', 'svg')]:
            name_temp = node.get(inkex.addNS('label', 'inkscape'))
            if not name_temp:
                return False # All groups must be named
            if len(str(name_temp)) > 0:
                if str(name_temp)[0] == '%':
                    continue # Skip Documentation layer and its contents
            if node.get("transform"): # No transforms are allowed on plottable layers
                return False
            for subnode in node:
                if subnode.get("transform"): # No transforms are allowed on objects
                    return False
                if subnode.tag in ['polyline', inkex.addNS('polyline', 'svg')]:
                    continue
                return False
        elif node.tag in tag_list:
            continue
        else:
            return False
    return True
