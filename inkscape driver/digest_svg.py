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
digest_svg.py

Routines for digesting an input SVG file into a simplified SVG ("Plob")
formats for easier processing

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

Requires Python 3.7 or newer.
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


class DigestSVG:# pylint: disable=pointless-string-statement
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

        self.doc_digest = path_objects.DocDigest()

        # Variables that will be populated in process_svg():
        self.bezier_tolerance = 0
        self.layer_selection = -2 # All layers; Matches default from plot_status.py

        self.doc_width_100 = 0
        self.doc_height_100 = 0
        self.diagonal_100 = 0

    def process_svg(self, node_list, warnings, digest_params, mat_current=None):
        """
        Wrapper around routine to recursively traverse an SVG document.

        This calls the recursive routine and handles building the digest
        structure around it, as well as reporting any necessary errors.

        Inputs:
        node_list, an lxml etree representing an SVG document
        warnings, a plot_warnings.PlotWarnings object
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
            self.bezier_tolerance]\
            = digest_params

        # Store document information in doc_digest
        self.doc_digest.viewbox = f"0 0 {self.doc_digest.width:f} {self.doc_digest.height:f}"

        self.doc_width_100 = self.doc_digest.width / scale_x    # Width of a "100% width" object
        self.doc_height_100 = self.doc_digest.height / scale_y  # height of a "100% height" object
        self.diagonal_100 = sqrt((self.doc_width_100)**2 + (self.doc_height_100)**2)/sqrt(2)

        docname = node_list.get('{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}docname')
        if docname: # Previously: inkex.addNS('docname', 'sodipodi'),
            self.doc_digest.name = docname

        root_layer = path_objects.LayerItem()
        # Flag to identify layers containing objects from root
        root_layer.name = '__digest-root__'
        root_layer.item_id = str(self.next_id)
        self.next_id += 1
        self.doc_digest.layers.append(root_layer)

        self.current_layer = root_layer # Layer that graphical elements should be added to
        self.current_layer_name = root_layer.name

        self.traverse(node_list, None, warnings, mat_current)
        return self.doc_digest


    def traverse(self, node_list, parent_style, warnings, mat_current):
        """
        Recursively traverse the SVG file and process all of the paths. Keep
        track of the composite transformation applied to each path.

        Inputs:
        node_list, an lxml etree representing an SVG document
        parent_style, dict from inherit_style
        warnings, a plot_warnings.PlotWarnings object
        mat_current, a transformation matrix

        This function handles path, group, line, rect, polyline, polygon,
        circle, ellipse  and use (clone) elements. Notable elements not handled
        include text. Unhandled elements should be converted to paths in
        Inkscape or another vector graphics editor.
        """

        if mat_current is None:
            mat_current = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

        for node in node_list:
            node_visibility = node.get('visibility')
            element_style = simplestyle.parseStyle(node.get('style'))

            # Presentation attributes, which have lower precedence than the style attribute:
            if 'fill' not in element_style: # If the style has not been set...
                element_style['fill'] = node.get('fill')
            if 'stroke' not in element_style: # If the style has not been set...
                element_style['stroke'] = node.get('stroke')
            if 'fill-rule' not in element_style: # If the style has not been set...
                element_style['fill-rule'] = node.get('fill-rule')
            # Since these are added to the style dictionary, a potential problem is that
            # these are now treated on equal footing to CSS styling information.

            style_dict = inherit_style(parent_style, element_style, node_visibility)

            if style_dict['display'] == 'none':
                continue  # Do not plot this object or its children
            if node.get('display') == 'none': # Possible SVG attribute as well
                continue  # Do not plot this object or its children

            # Apply the current matrix transform to this node's transform
            trans = node.get("transform")
            if trans is None:
                mat_new = mat_current
            else:
                mat_new = simpletransform.composeTransform(mat_current, \
                simpletransform.parseTransform(trans))

            if node.tag in ('{http://www.w3.org/2000/svg}g', 'g'):
                old_layer_name = self.current_layer_name
                if old_layer_name == '__digest-root__' and\
                    node.get('{http://www.inkscape.org/namespaces/inkscape}groupmode') == 'layer':
                    # Ensure that sublayers are treated like regular groups only

                    str_layer_name = node.get('{http://www.inkscape.org/namespaces/inkscape}label')
                    if str_layer_name is None:
                        str_layer_name = f"Auto-Layer {self.next_id}"

                    new_layer = path_objects.LayerItem()
                    new_layer.name = str_layer_name
                    new_layer.parse_name()

                    if new_layer.props.skip:
                        continue # Skip Documentation layer and its contents
                    if self.layer_selection >= 0: # Plotting in layers mode
                        if new_layer.props.number is None:
                            continue
                        if self.layer_selection != new_layer.props.number:
                            continue # Skip this layer and its contents

                    new_layer.item_id = str(self.next_id)
                    self.next_id += 1
                    self.doc_digest.layers.append(new_layer)
                    self.current_layer = new_layer
                    self.current_layer_name = str(str_layer_name)

                    self.traverse(node, style_dict, warnings, mat_new)

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
                    self.traverse(node, style_dict, warnings, mat_new)
                continue

            if node.tag in ('{http://www.w3.org/2000/svg}symbol', 'symbol'):
                # A symbol is much like a group, except that it should only
                #       be rendered when called within a "use" tag.
                if self.use_tag_nest_level > 0:
                    self.traverse(node, style_dict, warnings, mat_new)
                continue

            if node.tag in ('{http://www.w3.org/2000/svg}a', 'a'):
                # An 'a' is much like a group, in that it is a generic container element.
                self.traverse(node, style_dict, warnings, mat_new)
                continue

            if node.tag in ('{http://www.w3.org/2000/svg}switch', 'switch'):
                # A 'switch' is much like a group, in that it is a generic container element.
                # We are not presently evaluating conditions on switch elements, but parsing
                # their contents to the extent possible.
                self.traverse(node, style_dict, warnings, mat_new)
                continue

            if node.tag in ('{http://www.w3.org/2000/svg}use', 'use'):
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

                refid = node.get('{http://www.w3.org/1999/xlink}href')
                if refid is not None:
                    # [1:] to ignore leading '#' in reference
                    path = f'//*[@id="{refid[1:]}"]'
                    refnode = node.xpath(path)
                    if refnode is not None:
                        x_val = float(node.get('x', '0'))
                        y_val = float(node.get('y', '0'))
                        # Note: the transform has already been applied
                        if x_val != 0 or y_val != 0:
                            mat_new2 = simpletransform.composeTransform(mat_new,\
                            simpletransform.parseTransform(f'translate({x_val:.6E},{y_val:.6E})'))
                        else:
                            mat_new2 = mat_new
                        self.use_tag_nest_level += 1 # Keep track of nested "use" elements.
                        self.traverse(refnode, style_dict, warnings, mat_new2)
                        self.use_tag_nest_level -= 1
                continue

            # End container elements; begin graphical elements.

            if self.layer_selection >= 0:
                if self.current_layer_name == '__digest-root__':
                    continue # Do not print root elements if layer_selection >= 0

            if style_dict['visibility'] in ('hidden', 'collapse'):
                # Not visible; Do not plot. (This comes after the container tags;
                #   visible children of hidden elements can still plot.)
                continue

            if node.tag == '{http://www.w3.org/2000/svg}path':
                path_d = node.get('d')
                self.digest_path(path_d, style_dict, mat_new)
                continue

            if node.tag in ('{http://www.w3.org/2000/svg}rect', 'rect'):
                """
                Create a path with the outline of the rectangle
                Manually transform  <rect x="X" y="Y" width="W" height="H"/>
                    into            <path d="MX,Y lW,0 l0,H l-W,0 z"/>
                Draw three sides of the rectangle explicitly and the fourth implicitly
                https://www.w3.org/TR/SVG11/shapes.html#RectElement
                """

                x = plot_utils.unitsToUserUnits(node.get('x', '0'), self.doc_width_100)
                y = plot_utils.unitsToUserUnits(node.get('y', '0'), self.doc_height_100)

                r_x, width = [plot_utils.unitsToUserUnits(node.get(attr),
                    self.doc_width_100) for attr in ['rx', 'width']]
                r_y, height = [plot_utils.unitsToUserUnits(node.get(attr),
                    self.doc_height_100) for attr in ['ry', 'height']]

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

                self.digest_path(simplepath.formatPath(instr), style_dict, mat_new)
                continue

            if node.tag in ('{http://www.w3.org/2000/svg}line', 'line'):
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
                self.digest_path(simplepath.formatPath(path_a), style_dict, mat_new)
                continue

            if node.tag in ('{http://www.w3.org/2000/svg}polyline', 'polyline',
                            '{http://www.w3.org/2000/svg}polygon', 'polygon'):
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

                if node.tag in ('{http://www.w3.org/2000/svg}polygon', 'polygon'):
                    path_d += " Z"
                self.digest_path(path_d, style_dict, mat_new)
                continue


            if node.tag in ('{http://www.w3.org/2000/svg}ellipse', 'ellipse',
                            '{http://www.w3.org/2000/svg}circle', 'circle'):
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

                if node.tag in ('{http://www.w3.org/2000/svg}circle', 'circle'):
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
                path_d = f'M {x_1:f},{c_y:f} ' + \
                         f'A {r_x:f},{r_y:f} ' + \
                         f'0 1 0 {x_2:f},{c_y:f} ' + \
                         f'A {r_x:f},{r_y:f} ' + \
                         f'0 1 0 {x_1:f},{c_y:f}'
                self.digest_path(path_d, style_dict, mat_new)
                continue

            if node.tag in ('{http://www.w3.org/2000/svg}metadata', 'metadata'):
                self.doc_digest.metadata.update(dict(node.attrib))
                continue

            if node.tag in ('{http://www.w3.org/2000/svg}plotdata', 'plotdata'):
                self.doc_digest.plotdata.update(dict(node.attrib))
                continue

            if node.tag in ['{http://www.w3.org/2000/svg}defs', 'defs',
                'namedview',
                '{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}namedview',
                'eggbot', 'WCB', 'MergeData', '{http://www.w3.org/2000/svg}eggbot',
                '{http://www.w3.org/2000/svg}WCB', '{http://www.w3.org/2000/svg}MergeData',
                '{http://www.w3.org/2000/svg}title', 'title',
                '{http://www.w3.org/2000/svg}desc', 'desc',
                '{http://www.w3.org/2000/svg}pattern', 'pattern',
                '{http://www.w3.org/2000/svg}radialGradient', 'radialGradient',
                '{http://www.w3.org/2000/svg}linearGradient', 'linearGradient',
                '{http://www.w3.org/2000/svg}style', 'style', #  external style sheet
                '{http://www.w3.org/2000/svg}cursor', 'cursor',
                '{http://www.w3.org/2000/svg}font', 'font',
                '{http://www.inkscape.org/namespaces/inkscape}templateinfo',
                '{http://www.w3.org/2000/svg}color-profile', 'color-profile',
                '{http://www.w3.org/2000/svg}foreignObject', 'foreignObject',
                etree.Comment]:
                continue

            if node.tag in ('{http://www.w3.org/2000/svg}text', 'text',
                            '{http://www.w3.org/2000/svg}flowRoot', 'flowRoot'):
                warnings.add_new('text', self.current_layer_name)
                continue

            if node.tag in ('{http://www.w3.org/2000/svg}image', 'image'):
                warnings.add_new('image', self.current_layer_name)
                continue
            if not isinstance(node.tag, str):
                # This is likely an XML processing instruction such as an XML
                # comment. lxml uses a function reference for such node tags
                # and as such the node tag is likely not a printable string.
                # Converting it to a printable string likely won't be useful.
                continue
            text = str(node.tag).split('}')
            warnings.add_new(str(text[-1]), self.current_layer_name)

    def digest_path(self, path_d, style_dict, mat_transform):
        """
        Parse the path while applying the matrix transformation mat_transform.
        - Input is the "d" string attribute from an SVG path.
        - Turn this path into a cubicsuperpath (list of beziers).
        - Subdivide the cubic path into a list, rendering to straight segments within tolerance.
        - Identify subpaths within each path
        - Build a path_objects.PathItem object and append it to the current layer
        """

        # logger.debug('digest_path()\n')
        # logger.debug('path d: ' + path_d)

        if path_d is None:
            return
        if path_d == "":
            return

        parsed_path = cubicsuperpath.CubicSuperPath(simplepath.parsePath(path_d))

        if len(parsed_path) == 0: # path length is zero, will not be plotted
            return

        # Apply the transformation to each point
        apply_transform_to_path(mat_transform, parsed_path)

        subpaths = []

        # p is now a list of lists of cubic beziers [control pt1, control pt2, endpoint]
        # where the start-point is the last point in the previous segment.
        for subpath in parsed_path: # for subpaths in the path:
            # Divide each path into a set of straight segments:
            plot_utils.subdivideCubicPath(subpath, self.bezier_tolerance)

            if len(subpath) < 2:
                continue        # At least two points required for a path
            # Pick out vertex location information from cubic bezier curve:
            subpaths.append([[vertex[1][0], vertex[1][1]] for vertex in subpath])

        if len(subpaths) == 0:
            return # At least one sub-path required

        new_path = path_objects.PathItem()
        new_path.fill = style_dict['fill']
        new_path.stroke = style_dict['stroke']
        new_path.fill_rule = style_dict['fill-rule']
        new_path.item_id = str(self.next_id)
        self.next_id += 1

        new_path.subpaths = subpaths

        ok_to_fill = False
        for subpath in subpaths:
            if len(subpath) != 2:
                ok_to_fill = True   # As long as at least one path has more than two vertices
                break
        if not ok_to_fill:
            new_path.fill = None # Strip fill, if path has only 2-vertex subpaths

        # Add new list of subpaths to the current "LayerItem" element:
        self.current_layer.paths.append(new_path)

        # logger.debug('End of digest_path()\n')


def apply_transform_to_path(mat, path):
    '''
    A very slightly faster version of simpletransform.applyTransformToPath()
    Possibly move this function to plotink in the future.
    '''
    [mt00, mt01, mt02], [mt10, mt11, mt12] = mat
    for comp in path:
        for ctl in comp:
            for point in ctl: # apply transform to each point:
                pt_x = point[0]
                pt_y = point[1]
                point[0] = mt00*pt_x + mt01*pt_y + mt02
                point[1] = mt10*pt_x + mt11*pt_y + mt12


def inherit_style(parent_style, node_style, visibility):
    '''
    Parse style dict of node for fill and stroke information only.
    Inherit style from parent, but supersede it when a local style is defined.
    Also handle precedence of SVG "visibility" attribute, separate from the style.
    Note that children of hidden parents may be plotted if they assert visibility.
    '''
    default_style = {}
    default_style['fill'] = None
    default_style['stroke'] = None
    default_style['fill-rule'] = None
    default_style['visibility'] = 'visible'
    default_style['display'] = None # A null value; not "display:none".

    if parent_style is None: # Use default values when there is no parent
        parent_style = default_style

    # Use copy, not assignment, so that new_style represents an independent dict:
    new_style = parent_style.copy()

    if visibility: # Update first, allowing it to be overruled by style attributes
        new_style['visibility'] = visibility

    if node_style is None: # No additional new style information provided.
        return new_style

    for attrib in ['fill', 'stroke', 'fill-rule', 'visibility', 'display',]:
        # Valid for "string" attributes that DO NOT have units that need scaling;
        # Do not extend this to other style attributes without accounting for that.
        value = node_style.get(attrib) # Defaults to None, preventing KeyError
        if value:
            if value in ['inherit']:
                new_style[attrib] = parent_style[attrib]
            else:
                new_style[attrib] = value

    return new_style


def verify_plob(svg, model):
    """
    Check to see if the provided SVG is a valid plob that can be automatically converted
    to a plot digest object. Also check that the plob version and hardware model match.
    Styles are *presently allowed* in the plob, for the sake of verification. (They can
        increase the file size, but do not otherwise cause harm.)

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
    for node in svg:
        if node.tag in ['g', '{http://www.w3.org/2000/svg}g']:
            name_temp = node.get('{http://www.inkscape.org/namespaces/inkscape}label')
            if name_temp is None:
                return False # All groups must be named
            if len(str(name_temp)) > 0:
                if str(name_temp)[0] == '%':
                    continue # Skip Documentation layer and its contents
            if node.get("transform"): # No transforms are allowed on plottable layers
                return False
            for subnode in node:
                if subnode.get("transform"): # No transforms are allowed on objects
                    return False
                if subnode.tag in ['polyline', '{http://www.w3.org/2000/svg}polyline']:
                    continue
                return False
        elif node.tag in ['{http://www.w3.org/2000/svg}defs', 'defs', 'metadata',\
                '{http://www.w3.org/2000/svg}metadata',\
                '{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}namedview',\
                'plotdata', '{http://www.w3.org/2000/svg}plotdata']:
            continue
        else:
            return False
    return True
