#
# SVG Path Ordering Extension
# This extension uses a simple TSP algorithm to order the paths so as
# to reduce plotting time by plotting nearby paths consecutively.
#
# 
# While written from scratch, this is a derivative in spirit of the work by 
# Matthew Beckler and Daniel C. Newman for the EggBot project.
#
# The MIT License (MIT)
#
# Copyright (c) 2021 Windell H. Oskay, Evil Mad Science LLC
# www.evilmadscientist.com
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

import math
import sys

from lxml import etree

from axidrawinternal.plot_utils_import import from_dependency_import # plotink
inkex = from_dependency_import('ink_extensions.inkex')
simpletransform = from_dependency_import('ink_extensions.simpletransform')
simplestyle = from_dependency_import('ink_extensions.simplestyle')
exit_status = from_dependency_import('ink_extensions_utils.exit_status')
plot_utils = from_dependency_import('plotink.plot_utils')        # https://github.com/evil-mad/plotink  Requires version 0.15

"""
TODOs:

* Apparent difference in execution time for portrait vs landscape document orientation.
  Seems to be related to the _change_

* Implement path functions

<param name="path_handling" _gui-text="Compound Paths" type="optiongroup">
<_option value=0>Leave as is</_option>
<_option value=1>Reorder subpaths</_option>
<_option value=2>Break apart</_option>
</param>

self.arg_parser.add_argument( "--path_handling",\
action="store", type=int, dest="path_handling",\
default=1,help="How compound paths are handled")


* Consider re-introducing GUI method for rendering:

<param indent="1" name="rendering" type=inkex.boolean_option _gui-text="Preview pen-up travel">
  false</param>


"""

class ReorderEffect(inkex.Effect):
    """
    Inkscape effect extension.
    Re-order the objects in the SVG document for faster plotting.
    Respect layers: Initialize a new dictionary of objects for each layer, and sort
        objects within that layer only
    Objects in root of document are treated as being on a _single_ layer, and will all
        be sorted.
        
    """

    def __init__( self ):
        inkex.Effect.__init__( self )

        self.arg_parser.add_argument( "--reordering",\
        action="store", type=int, dest="reordering",\
        default=1,help="How groups are handled")

        self.auto_rotate = True

    def effect(self):
        # Main entry point of the program

        self.svg_width = 0 
        self.svg_height = 0
        self.air_total_default = 0
        self.air_total_sorted = 0
        self.printPortrait = False
        
        # Rendering is available for debug purposes. It only previews
        # pen-up movements that are reordered and typically does not
        # include all possible movement.
        
        self.preview_rendering = False 
        self.layer_index = 0 # index for coloring layers
        
        self.svg = self.document.getroot()
        
        self.DocUnits = "in" # Default
        self.DocUnits = self.getDocumentUnit()
        
        self.unit_scaling = 1

        self.getDocProps()

        """
        Set up the document-wide transforms to handle SVG viewbox 
        """

        matCurrent = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

        viewbox = self.svg.get( 'viewBox' )

        vb = self.svg.get('viewBox')
        if vb:
            p_a_r = self.svg.get('preserveAspectRatio')
            sx,sy,ox,oy = plot_utils.vb_scale(vb, p_a_r, self.svg_width, self.svg_height)
        else: 
            sx = 1.0 / float(plot_utils.PX_PER_INCH) # Handle case of no viewbox
            sy = sx
            ox = 0.0
            oy = 0.0
        
        # Initial transform of document is based on viewbox, if present:
        matCurrent = simpletransform.parseTransform('scale({0:.6E},{1:.6E}) translate({2:.6E},{3:.6E})'.format(sx, sy, ox, oy))
        # Set up x_last, y_last, which keep track of last known pen position
        # The initial position is given by the expected initial pen position 

        self.y_last = 0
        
        if (self.printPortrait):
            self.x_last = self.svg_width
        else:
            self.x_last = 0
        
        parent_vis='visible'

        self.root_nodes = []

        if self.preview_rendering:
            # Remove old preview layers, if rendering is enabled
            for node in self.svg:
                if node.tag == inkex.addNS( 'g', 'svg' ) or node.tag == 'g':
                    if ( node.get( inkex.addNS( 'groupmode', 'inkscape' ) ) == 'layer' ): 
                        LayerName = node.get( inkex.addNS( 'label', 'inkscape' ) )
                        if LayerName == '% Preview':
                            self.svg.remove( node )

            preview_transform = simpletransform.parseTransform(
                'translate({2:.6E},{3:.6E}) scale({0:.6E},{1:.6E})'.format(
                1.0/sx, 1.0/sy, -ox, -oy))
            path_attrs = { 'transform': simpletransform.formatTransform(preview_transform)}
            self.preview_layer = etree.Element(inkex.addNS('g', 'svg'),
                path_attrs, nsmap=inkex.NSS)
                    
                    
            self.preview_layer.set( inkex.addNS('groupmode', 'inkscape' ), 'layer' )
            self.preview_layer.set( inkex.addNS( 'label', 'inkscape' ), '% Preview' )
            self.svg.append( self.preview_layer )


            # Preview stroke width: 1/1000 of page width or height, whichever is smaller
            if self.svg_width < self.svg_height:
                width_du = self.svg_width / 1000.0
            else:
                width_du = self.svg_height / 1000.0

            """
            Stroke-width is a css style element, and cannot accept scientific notation.
            
            Thus, in cases with large scaling (i.e., high values of 1/sx, 1/sy)
            resulting from the viewbox attribute of the SVG document, it may be necessary to use 
            a _very small_ stroke width, so that the stroke width displayed on the screen
            has a reasonable width after being displayed greatly magnified thanks to the viewbox.
            
            Use log10(the number) to determine the scale, and thus the precision needed.
            """

            log_ten = math.log10(width_du)
            if log_ten > 0:  # For width_du > 1
                width_string = "{0:.3f}".format(width_du)
            else:
                prec = int(math.ceil(-log_ten) + 3)
                width_string = "{0:.{1}f}".format(width_du, prec)

            self.p_style = {'stroke-width': width_string, 'fill': 'none',
                'stroke-linejoin': 'round', 'stroke-linecap': 'round'}

        self.svg = self.parse_svg(self.svg, matCurrent)


    def parse_svg(self, input_node, mat_current=None, parent_vis='visible'):
        """
        Input: An SVG node (usually) containing other nodes:
            The SVG root, a layer, sublayer, or other group.
        Output: The re-ordered node. The contents are reordered with the greedy
            algorithm, except:
            - Layers and sublayers are preserved. The contents of each are
                    re-ordered for faster plotting.
            - Groups are either preserved, broken apart, or re-ordered within
                    the group, depending on the value of group_mode.
        """

        coord_dict = {}
        # coord_dict maps a node ID to the following data:
        #    Is the node plottable, first coordinate pair, last coordinate pair.
        #    i.e., Node_id -> (Boolean: plottable, Xi, Yi, Xf, Yf)
        
        group_dict = {}
        # group_dict maps a node ID for a group to the contents of that group.
        # The contents may be a preserved nested group or a flat list, depending
        #  on the selected group handling mode. Example:
        # group_dict = {'id_1': <Element {http://www.w3.org/2000/svg}g at memory_location_1>, 
        #               'id_2': <Element {http://www.w3.org/2000/svg}g at memory_location_2>

        nodes_to_delete = []
        
        counter = 0     # TODO: Replace this with better unique ID system

        # Account for input_node's transform and any transforms above it:
        if mat_current is None:
            mat_current = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        try:    
            matNew = simpletransform.composeTransform( mat_current,
                simpletransform.parseTransform( input_node.get( "transform" )))
        except AttributeError:
            matNew = mat_current
    
        for node in input_node:
            # Step through each object within the top-level input node
            
            
            if node.tag is etree.Comment:
                continue

            try:
                id = node.get( 'id' )
            except AttributeError:
                id = self.uniqueId("1",True)
                node.set( 'id', id)
            if id == None:
                id = self.uniqueId("1",True)
                node.set( 'id', id)


            # First check for object visibility:
            skip_object = False

            # Check for "display:none" in the node's style attribute:
            style = simplestyle.parseStyle(node.get('style'))
            if 'display' in style.keys() and style['display'] == 'none':
                skip_object = True # Plot neither this object nor its children
            
            # The node may have a display="none" attribute as well:
            if node.get( 'display' ) == 'none':
                skip_object = True # Plot neither this object nor its children
            
            # Visibility attributes control whether a given object will plot.
            # Children of hidden (not visible) parents may be plotted if
            # they assert visibility.
            visibility = node.get( 'visibility', parent_vis )    

            if 'visibility' in style.keys():
                visibility = style['visibility'] # Style may override attribute.

            if visibility == 'inherit':
                visibility = parent_vis
            
            if visibility != 'visible':
                skip_object = True  # Skip this object and its children

            # Next, check to see if this inner node is itself a group or layer:
            if node.tag == inkex.addNS( 'g', 'svg' ) or node.tag == 'g':

                # Use the user-given option to decide what to do with subgroups:
                subgroup_mode = self.options.reordering 

#                 Values of the parameter:
#                 subgroup_mode=="1": Preserve groups
#                 subgroup_mode=="2": Reorder within groups
#                 subgroup_mode=="3": Break apart groups

                if node.get(inkex.addNS('groupmode', 'inkscape')) == 'layer':
                    # The node is a layer or sub-layer, not a regular group.
                    # Parse it separately, and re-order its contents. 

                    subgroup_mode = 2 # Always sort within each layer.
                    self.layer_index += 1

                    layer_name = node.get( inkex.addNS( 'label', 'inkscape' ) )

                    layer_name = str(layer_name).lstrip()
                
                    if layer_name:
                        if layer_name[0] == '%': # First character is '%'; This
                            skip_object = True   # is a documentation layer; skip plotting.
                            self.layer_index -= 1 # Set this back to previous value.

                if skip_object:
                    # Do not re-order hidden groups or layers.
                    subgroup_mode = 1 # Preserve this group

                if subgroup_mode == 3:
                    # Break apart this non-layer subgroup and add it to
                    # the set of things to be re-ordered.
    
                    nodes_to_delete.append(node)
                    nodes_inside_group = self.group2NodeDict(node)
    
                    for a_node in nodes_inside_group:
                        try:
                            id = a_node.get( 'id' )
                        except AttributeError:
                            id = self.uniqueId("1",True)
                            a_node.set( 'id', id)
                        if id == None:
                            id = self.uniqueId("1",True)
                            a_node.set( 'id', id)

                        # Use getFirstPoint and getLastPoint on each object:
                        start_plottable, first_point = self.getFirstPoint(a_node, matNew)
                        end_plottable, last_point  = self.getLastPoint(a_node, matNew)
                        
                        coord_dict[id] = (start_plottable and end_plottable,
                            first_point[0], first_point[1], last_point[0], last_point[1] )
                        # Entry in group_dict is this node 
                        group_dict[id] = a_node
                            
                elif subgroup_mode == 2:
                    # Reorder a layer or subgroup with a recursive call.

                    node = self.parse_svg(node, matNew, visibility)

                    # Capture the first and last x,y coordinates of the optimized node
                    start_plottable, first_point = self.group_first_pt(node, matNew)
                    end_plottable, last_point  = self.group_last_pt(node, matNew)

                    # Then add this optimized node to the coord_dict
                    coord_dict[id] = (start_plottable and end_plottable,
                        first_point[0],  first_point[1], last_point[0],  last_point[1] )
                    # Entry in group_dict is this node 
                    group_dict[id] = node
                    
                else: # (subgroup_mode == 1)
                    # Preserve the group, but find its first and last point so
                    #    that it can be re-ordered with respect to other items

                    if skip_object:
                        start_plottable = False
                        end_plottable = False
                        first_point = [(-1.), (-1.)]
                        last_point = [(-1.), (-1.)]
                    else:
                        start_plottable, first_point = self.group_first_pt(node, matNew)
                        end_plottable, last_point  = self.group_last_pt(node, matNew) 

                    coord_dict[id] = (start_plottable and end_plottable,
                        first_point[0],  first_point[1], last_point[0],  last_point[1] )
                    # Entry in group_dict is this node 
                    group_dict[id] = node
    
            else: # Handle objects that are not groups
                if skip_object:
                    start_plottable = False
                    end_plottable = False
                    first_point = [(-1.), (-1.)]
                    last_point = [(-1.), (-1.)]
                else:
                    start_plottable, first_point = self.getFirstPoint(node, matNew)
                    end_plottable, last_point  = self.getLastPoint(node, matNew)

                coord_dict[id] = (start_plottable and end_plottable,
                    first_point[0], first_point[1], last_point[0],  last_point[1] )
                group_dict[id] = node   # Entry in group_dict is this node 

        # Perform the re-ordering:
        ordered_element_list = self.ReorderNodeList(coord_dict, group_dict)

        # Once a better order for the svg elements has been determined,
        # All there is do to is to reintroduce the nodes to the parent in the correct order
        for elt in ordered_element_list:
            # Creates identical node at the correct location according to ordered_element_list
            input_node.append(elt)
        # Once program is finished parsing through 
        for element_to_remove in nodes_to_delete: 
            try:
                input_node.remove(element_to_remove)
            except ValueError:
                inkex.errormsg(str(element_to_remove.get('id'))+" is not a member of " + str(input_node.get('id')))    

        return input_node


    def break_apart_path(self, path): 
        """
        An SVG path may contain multiple distinct portions, that are normally separated
        by pen-up movements.
        
        This function takes the path data string from an SVG path, parses it, and returns
        a dictionary of independent path data strings, each of which represents a single
        pen-down movement. It is equivalent to the Inkscape function Path > Break Apart
            
        Input: path data string, representing a single SVG path
        Output: Dictionary of (separated) path data strings
    
        """
        MaxLength = len(path)
        ix = 0
        move_to_location = []
        path_dictionary = {}
        path_list = []
        path_number = 1
    
        # Search for M or m location
        while ix < MaxLength:
            if(path[ix] == 'm' or path[ix] == 'M'):
                move_to_location.append(ix)    
            ix = ix + 1
        # Iterate through every M or m location in our list of move to instructions
        # Slice the path string according to path beginning and ends as indicated by the
        # location of these instructions
    
        for counter, m in enumerate(move_to_location):
            if (m == move_to_location[-1]):        
                # last entry
                path_list.append(path[m:MaxLength].rstrip())
            else: 
                path_list.append(path[m:move_to_location[counter + 1]].rstrip())
    
        for counter, current_path in enumerate(path_list):
            
            # Enumerate over every entry in the path looking for relative m commands
            if current_path[0] == 'm' and counter > 0:    
                # If path contains relative m command, the best case is when the last command
                # was a Z or z. In this case, all relative operations are performed relative to
                # initial x, y coordinates of the previous path
    
                if path_list[counter -1][-1].upper() == 'Z':
                    current_path_x, current_path_y,index = self.getFirstPoint(current_path, matNew)    
                    prev_path_x, prev_path_y,ignore = self.getFirstPoint(path_list[counter-1])    
                    adapted_x = current_path_x + prev_path_x    
                    adapted_y = current_path_y + prev_path_y    
                    # Now we can replace the path data with an Absolute Move to instruction
                    # HOWEVER, we need to adapt all the data until we reach a different command in the case of a repeating  
                    path_list[counter] = "m "+str(adapted_x)+","+str(adapted_y) + ' ' +current_path[index:]
    
                # If there is no z or absolute commands, we need to parse the entire path 
                else:
    
                    # scan path for absolute coordinates. If present, begin parsing from their index
                    # instead of the beginning
                    prev_path = path_list[counter-1]
                    prev_path_length = len(prev_path)
                    jx = 0
                    x_val, y_val = 0,0    
                    # Check one char at a time 
                    # until we have the moveTo Command
                    last_command = ''
                    is_absolute_command = False
                    repeated_command = False
                    # name of command
                    # how many parameters we need to skip 
                    accepted_commands = {
                        'M':0,
                        'L':0,
                        'H':0,
                        'V':0,
                        'C':4,
                        'S':2,
                        'Q':2,
                        'T':0,
                        'A':5
                    }    
                    
                    # If there is an absolute command which specifies a new initial point 
                    # then we can save time by setting our index directly to its location in the path data
                    # See if an accepted_command is present in the path data. If it is present further in the 
                    # string than any command found before, then set the pointer to that location 
                    # if a command is not found, find() will return a -1. jx is initialized to 0, so if no matches
                    # are found, the program will parse from the beginning to the end of the path
                    
                    for keys in 'MLCSQTA':        # TODO: Compare to last_point; see if we can clean up this part
                        if(prev_path.find(keys) > jx):
                            jx = prev_path.find(keys)        
    
                    while jx < prev_path_length:
    
                        temp_x_val = ''
                        temp_y_val = ''
                        num_of_params_to_skip = 0
                        
                        # SVG Path commands can be repeated 
                        if (prev_path[jx].isdigit() and last_command):
                            repeated_command = True    
                        else:
                            repeated_command = False
    
                        if (prev_path[jx].isalpha() and prev_path[jx].upper() in accepted_commands) or repeated_command:
                                                
                            if repeated_command:
                                #is_relative_command is saved from last iteration of the loop
                                current_command = last_command
                            else:
                                # If the character is accepted, we must parse until reach the x y coordinates
                                is_absolute_command = prev_path[jx].isupper()    
                                current_command = prev_path[jx].upper()
    
                            # Each command has a certain number of parameters we must pass before we reach the
                            # information we care about. We will parse until we know that we have reached them
    
                            # Get to start of next number
                            # We will know we have reached a number if the current character is a +/- sign
                            # or current character is a digit 
                            while jx < prev_path_length:
                                if(prev_path[jx] in '+-' or prev_path[jx].isdigit()):
                                    break
                                jx = jx + 1 
                                    
                            # We need to parse past the unused parameters in our command
                            # The number of parameters to parse past is dependent on the command and stored 
                            # as the value of accepted_command
                            # Spaces and commas are used to deliniate parameters 
                            while jx < prev_path_length and num_of_params_to_skip < accepted_commands[current_command]:
                                if(prev_path[jx].isspace() or prev_path[jx] == ','):
                                    num_of_params_to_skip = num_of_params_to_skip + 1 
                                jx = jx + 1 
                            
                            # Now, we are in front of the x character
        
                            if current_command.upper() == 'V':
                                temp_x_val = 0    
            
                            if current_command.upper() == 'H':
                                temp_y_val = 0    
    
                            # Parse until next character is a digit or +/- character
                            while jx < prev_path_length and current_command.upper() != 'V':
                                if(prev_path[jx] in '+-' or prev_path[jx].isdigit()):
                                    break
                                jx = jx + 1 
                            
                            # Save each next character until we reach a space
                            while jx < prev_path_length and current_command.upper() != 'V' and not (prev_path[jx].isspace() or prev_path[jx] == ','):
                                temp_x_val = temp_x_val + prev_path[jx]
                                jx = jx + 1 
                            
                            # Then we know we have completely parsed the x character
        
                            # Now we are in front of the y character
    
                            # Parse until next character is a digit or +/- character
                            while jx < prev_path_length and current_command.upper() != 'H':
                                if(prev_path[jx] in '+-' or prev_path[jx].isdigit()):
                                    break
                                jx = jx + 1 
    
                            ## Save each next character until we reach a space
                            while jx < prev_path_length and current_command.upper() != 'H' and not (prev_path[jx].isspace() or prev_path[jx] == ','):
                                temp_y_val = temp_y_val + prev_path[jx]
                                jx = jx + 1 
                            
                            # Then we know we have completely parsed the y character
        
                            if is_absolute_command:
    
                                if current_command == 'H':
                                    # Absolute commands create new x,y position 
                                    try:
                                        x_val = float(temp_x_val)
                                    except ValueError:
                                        pass
                                elif current_command == 'V':
                                    # Absolute commands create new x,y position 
                                    try:
                                        y_val = float(temp_y_val)
                                    except ValueError:
                                        pass
                                else:
                                    # Absolute commands create new x,y position 
                                    try:
                                        x_val = float(temp_x_val)
                                        y_val = float(temp_y_val)
                                    except ValueError:
                                        pass
                            else:
        
                                if current_command == 'h':
                                    # Absolute commands create new x,y position 
                                    try:
                                        x_val = x_val + float(temp_x_val)
                                    except ValueError:
                                        pass
                                elif current_command == 'V':
                                    # Absolute commands create new x,y position 
                                    try:
                                        y_val = y_val + float(temp_y_val)
                                    except ValueError:
                                        pass
                                else:
                                    # Absolute commands create new x,y position 
                                    try:
                                        x_val = x_val + float(temp_x_val)
                                        y_val = y_val + float(temp_y_val)
                                    except ValueError:
                                        pass
                            last_command = current_command
                        jx = jx + 1
                    x,y,index = self.getFirstPoint(current_path,None)    
                    path_list[counter] = "m "+str(x_val+x)+","+str(y_val+y) + ' ' + current_path[index:]
                
        for counter, path in enumerate(path_list):
            path_dictionary['ad_path'+ str(counter)] = path 
        
        return path_dictionary


    def getFirstPoint(self, node, matCurrent):
        """
        Input: (non-group) node and parent transformation matrix
        Output: Boolean value to indicate if the svg element is plottable and
            two floats stored in a list representing the x and y coordinates we plot first
        """

        # first apply the current matrix transform to this node's transform
        matNew = simpletransform.composeTransform( matCurrent, simpletransform.parseTransform( node.get( "transform" ) ) )

        point = [float(-1), float(-1)]
        try:
            if node.tag == inkex.addNS( 'path', 'svg' ):
    
                pathdata = node.get('d')
    
                point = plot_utils.pathdata_first_point(pathdata)
                if point:
                    simpletransform.applyTransformToPoint(matNew, point)
                    return True, point
                else:
                    return False, [float(-1), float(-1)]
    
            if node.tag == inkex.addNS( 'rect', 'svg' ) or node.tag == 'rect':
    
                """
                The x,y coordinates for a rect are included in their specific attributes
                If there is a transform, we need translate the x & y coordinates to their
                correct location via applyTransformToPoint.
                """
    
                point[0] = float( node.get( 'x' ) )
                point[1] = float( node.get( 'y' ) )
                
                simpletransform.applyTransformToPoint(matNew, point)
                
                return True, point
    
            if node.tag == inkex.addNS( 'line', 'svg' ) or node.tag == 'line':
                """
                The x1 and y1 attributes are where we will start to draw
                So, get them, apply the transform matrix, and return the point
                """
    
                point[0] = float( node.get( 'x1' ) )
                point[1] = float( node.get( 'y1' ) )
    
                simpletransform.applyTransformToPoint(matNew, point)
                
                return True, point

            elif node.tag in [inkex.addNS('polyline', 'svg'), 'polyline',
                              inkex.addNS('polygon', 'svg'), 'polygon']:
                """
                Polyline and polygon have the same first point.

                We need to extract x1 and y1 from these:
                <polygon points="x1,y1 x2,y2 x3,y3 [...]"/>
                We accomplish this with Python string strip
                and split methods. Then apply transforms
                """
                pl = node.get( 'points', '' ).strip()
                
                if pl == '':
                    return False, point
    
                pa = pl.replace(',',' ').split() # replace comma with space before splitting
    
                if not pa:
                    return False, point
                pathLength = len( pa )
                if (pathLength < 4): # Minimum of x1,y1 x2,y2 required.
                    return False, point
    
                d = "M " + pa[0] + " " + pa[1]
                i = 2
                while (i < (pathLength - 1 )):
                    d += " L " + pa[i] + " " + pa[i + 1]
                    i += 2
                
                point = plot_utils.pathdata_first_point(d)
                simpletransform.applyTransformToPoint(matNew, point)
    
                return True, point
    
            if node.tag == inkex.addNS( 'ellipse', 'svg' ) or \
                node.tag == 'ellipse':
                
                cx = float( node.get( 'cx', '0' ) )
                cy = float( node.get( 'cy', '0' ) )
                rx = float( node.get( 'rx', '0' ) )
    
                point[0] = cx - rx
                point[1] = cy
    
                simpletransform.applyTransformToPoint(matNew, point)
    
                return True, point
    
            if node.tag == inkex.addNS( 'circle', 'svg' ) or \
                node.tag == 'circle':
                cx = float( node.get( 'cx', '0' ) )
                cy = float( node.get( 'cy', '0' ) )
                r = float( node.get( 'r', '0' ) )
                point[0] = cx - r
                point[1] = cy
    
                simpletransform.applyTransformToPoint(matNew, point)
    
                return True, point
            
            if node.tag == inkex.addNS('symbol', 'svg') or node.tag == 'symbol':
                # A symbol is much like a group, except that
                # it's an invisible object.
                return False, point  # Skip this element.
                
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
    
                        x = float(node.get('x', '0'))
                        y = float(node.get('y', '0'))
    
                        # Note: the transform has already been applied
                        if x != 0 or y != 0:
                            mat_new2 = simpletransform.composeTransform(matNew, simpletransform.parseTransform('translate({0:f},{1:f})'.format(x, y)))
                        else:
                            mat_new2 = matNew
                        # Note that the referenced object may be a 'symbol`,
                        # which acts like a group, or it may be a simple
                        # object. 
    
                        if len(refnode) > 0:
                            plottable, the_point = self.group_first_pt(refnode[0], mat_new2)
                        else:
                            plottable, the_point = self.group_first_pt(refnode, mat_new2)
    
                        return plottable, the_point 
        except:
            pass
    
        # Svg Object is not a plottable element
        # In this case, return False to indicate a non-plottable element
        # and a default point
        
        return False, point
    
    def getLastPoint(self, node, matCurrent):
        """
        Input: XML tree node and transformation matrix
        Output: Boolean value to indicate if the svg element is plottable or not and 
                two floats stored in a list representing the x and y coordinates we plot last
        """

        # first apply the current matrix transform to this node's transform
        matNew = simpletransform.composeTransform( matCurrent, simpletransform.parseTransform( node.get( "transform" ) ) )

        # If we return a negative value, we know that this function did not work
        point = [float(-1), float(-1)]
        try:
            if node.tag == inkex.addNS( 'path', 'svg' ):
    
                path = node.get('d')

                point = plot_utils.pathdata_last_point(path)
                if point:
                    simpletransform.applyTransformToPoint(matNew, point)
                    return True, point 
                else:
                    return False, [float(-1), float(-1)]
            if node.tag == inkex.addNS( 'rect', 'svg' ) or node.tag == 'rect':
            
                """
                The x,y coordinates for a rect are included in their specific attributes
                If there is a transform, we need translate the x & y coordinates to their
                correct location via applyTransformToPoint.
                """
    
                point[0] = float( node.get( 'x' ) )
                point[1] = float( node.get( 'y' ) )
                
                simpletransform.applyTransformToPoint(matNew, point)
                
                return True, point    # Same start and end points
    
            if node.tag == inkex.addNS( 'line', 'svg' ) or node.tag == 'line':
    
                """
                The x2 and y2 attributes are where we will end our drawing
                So, get them, apply the transform matrix, and return the point
                """
    
                point[0] = float( node.get( 'x2' ) )
                point[1] = float( node.get( 'y2' ) )
    
                simpletransform.applyTransformToPoint(matNew, point)
                
                return True, point
    
            if node.tag == inkex.addNS( 'polyline', 'svg' ) or node.tag == 'polyline':

                pl = node.get( 'points', '' ).strip()

                if pl == '':
                    return False, point

                pa = pl.replace(',',' ').split()
                if not pa:
                    return False, point
                pathLength = len( pa )
                if (pathLength < 4): # Minimum of x1,y1 x2,y2 required.
                    return False, point

                d = "M " + pa[0] + " " + pa[1]
                i = 2
                while (i < (pathLength - 1 )):
                    d += " L " + pa[i] + " " + pa[i + 1]
                    i += 2

                endpoint = plot_utils.pathdata_last_point(d)    
                simpletransform.applyTransformToPoint(matNew, endpoint)
            
                return True, endpoint

            elif node.tag in [inkex.addNS('polygon', 'svg'), 'polygon']:
                """
                Polygon has same first and last point.
                
                Repeat function to get first point of polyline:
                """
                pl = node.get( 'points', '' ).strip()
                
                if pl == '':
                    return False, point
    
                pa = pl.replace(',',' ').split() # replace comma with space before splitting
    
                if not pa:
                    return False, point
                pathLength = len( pa )
                if (pathLength < 4): # Minimum of x1,y1 x2,y2 required.
                    return False, point
    
                d = "M " + pa[0] + " " + pa[1]
                i = 2
                while (i < (pathLength - 1 )):
                    d += " L " + pa[i] + " " + pa[i + 1]
                    i += 2
                
                point = plot_utils.pathdata_first_point(d)
                simpletransform.applyTransformToPoint(matNew, point)

            if node.tag == inkex.addNS( 'ellipse', 'svg' ) or node.tag == 'ellipse':
                
                cx = float( node.get( 'cx', '0' ) )
                cy = float( node.get( 'cy', '0' ) )
                rx = float( node.get( 'rx', '0' ) )
    
                point[0] = cx - rx 
                point[1] = cy
    
                simpletransform.applyTransformToPoint(matNew, point)
    
                return True, point 
    
            if node.tag == inkex.addNS( 'circle', 'svg' ) or node.tag == 'circle':
                cx = float( node.get( 'cx', '0' ) )
                cy = float( node.get( 'cy', '0' ) )
                r = float( node.get( 'r', '0' ) )
                point[0] = cx - r
                point[1] = cy
    
                simpletransform.applyTransformToPoint(matNew, point)
    
                return True, point 
                
            if node.tag == inkex.addNS('symbol', 'svg') or node.tag == 'symbol':
                # A symbol is much like a group, except that it should only be
                # rendered when called within a "use" tag.
                return False, point  # Skip this element.
                
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
                        x = float(node.get('x', '0'))
                        y = float(node.get('y', '0'))
                        # Note: the transform has already been applied
                        if x != 0 or y != 0:
                            mat_new2 = simpletransform.composeTransform(matNew, simpletransform.parseTransform('translate({0:f},{1:f})'.format(x, y)))
                        else:
                            mat_new2 = matNew
                        if len(refnode) > 0:
                            plottable, the_point = self.group_last_pt(refnode[0], mat_new2)
                        else:
                            plottable, the_point = self.group_last_pt(refnode, mat_new2)
                        return plottable, the_point 
        except:
            pass    
    
        # Svg Object is not a plottable element;
        # Return False and a default point
        return False, point 


    def group_first_pt(self, group, matCurrent = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]):
        """
            Input: A Node which we have found to be a group
            Output: Boolean value to indicate if a point is plottable
                    float values for first x,y coordinates of svg element
        """

        if len(group) == 0: # Empty group -- The object may not be a group.
            return self.getFirstPoint(group, matCurrent)  

        success = False
        point = [float(-1), float(-1)]
        
        # first apply the current matrix transform to this node's transform
        matNew = simpletransform.composeTransform( matCurrent, simpletransform.parseTransform( group.get( "transform" ) ) )

        # Step through the group, we examine each element until we find a plottable object
        for subnode in group:
            # Check to see if the subnode we are looking at in this iteration of our for loop is a group
            # If it is a group, we must recursively call this function to search for a plottable object
            if subnode.tag == inkex.addNS( 'g', 'svg' ) or subnode.tag == 'g':
                # Verify that the nested group has objects within it
                # otherwise we will not parse it 
                if subnode is not None:
                    # Check if group contains plottable elements by recursively calling group_first_pt
                    # If group contains plottable subnode, then it will return that value and escape the loop
                    # Else function continues search for first plottable object
                    success, point = self.group_first_pt(subnode, matNew)
                    if success:
                        # Subnode inside nested group is plottable! 
                        # Break from our loop so we can return the first point of this plottable subnode
                        break
                    else:
                        continue
            else:
                # Node is not a group
                # Get its first (x,y) coordinates 
                # Also get a Boolean value to indicate if the subnode is plottable or not 
                # If subnode is not plottable, continue to next subnode in the group 
                success, point = self.getFirstPoint(subnode, matNew)  
                
                if success:
                    # Subnode inside group is plottable! 
                    # Break from our loop so we can return the first point of this plottable subnode
                    break
                else:
                    continue
        return success, point
    
    
    def group_last_pt(self, group, matCurrent=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]):
        """
        Input: A Node which we have found to be a group
        Output: The last node within the group which can be plotted    
        """
        
        if len(group) == 0: # Empty group -- Did someone send an object that isn't a group?
            return self.getLastPoint(group, matCurrent)  
        
        success = False
        point = [float(-1),float(-1)]
        
        # first apply the current matrix transform to this node's transform
        matNew = simpletransform.composeTransform( matCurrent, simpletransform.parseTransform( group.get( "transform" ) ) )
    
        # Step through the group, we examine each element until we find a plottable object
        for subnode in reversed(group):
            # Check to see if the subnode we are looking at in this iteration of our for loop is a group
            # If it is a group, we must recursively call this function to search for a plottable object
            if subnode.tag == inkex.addNS( 'g', 'svg' ) or subnode.tag == 'g':
                # Verify that the nested group has objects within it
                # otherwise we will not parse it 
                if subnode is not None:
                    # Check if group contains plottable elements by recursively calling group_last_pt
                    # If group contains plottable subnode, then it will return that value and escape the loop
                    # Else function continues search for last plottable object
                    success, point = self.group_last_pt(subnode, matNew)
                    if success:
                        # Subnode inside nested group is plottable! 
                        # Break from our loop so we can return the first point of this plottable subnode
                        break
                    else:
                        continue
            else:
                # Node is not a group
                # Get its first (x,y) coordinates 
                # Also get a Boolean value to indicate if the subnode is plottable or not 
                # If subnode is not plottable, continue to next subnode in the group 
                success, point = self.getLastPoint(subnode, matNew)  
                if success:
    
                    # Subode inside nested group is plottable! 
                    # Break from our loop so we can return the first point of this plottable subnode
                    break
                else:
                    continue
        return success, point    


    def group2NodeDict(self, group, mat_current=None):

        if mat_current is None:
            mat_current = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
            
        # first apply the current matrix transform to this node's transform
        matNew = simpletransform.composeTransform( mat_current, simpletransform.parseTransform( group.get( "transform" ) ) )
    
        nodes_in_group = []
    
        # Step through the group, we examine each element until we find a plottable object
        for subnode in group:
            # Check to see if the subnode we are looking at in this iteration of our for loop is a group
            # If it is a group, we must recursively call this function to search for a plottable object
            if subnode.tag == inkex.addNS( 'g', 'svg' ) or subnode.tag == 'g':
                # Verify that the nested group has objects within it
                # otherwise we will not parse it 
                if subnode is not None:
                    # Check if group contains plottable elements by recursively calling group_first_pt
                    # If group contains plottable subnode, then it will return that value and escape the loop
                    # Else function continues search for first plottable object
                    nodes_in_group.extend(self.group2NodeDict(subnode, matNew))
            else:
                simpletransform.applyTransformToNode(matNew, subnode)
                nodes_in_group.append(subnode)
        return nodes_in_group


    def ReorderNodeList(self, coord_dict, group_dict):
        # Re-order the given set of SVG elements, using a simple "greedy" algorithm.
        # The first object will be the element closest to the origin
        # After this choice, the algorithm loops through all remaining elements looking for the element whose first x,y
        # coordinates are closest to the the previous choice's last x,y coordinates
        # This process continues until all elements have been sorted into ordered_element_list and removed from group_dict    
        
        ordered_layer_element_list = []
            
        # Continue until all elements have been re-ordered
        while group_dict:
            
            nearest_dist = float('inf')
            for key,node in group_dict.items():    
                # Is this node non-plottable?
                # If so, exit loop and append element to ordered_layer_element_list
                if not coord_dict[key][0]:
                    # Object is not Plottable
                    nearest = node 
                    nearest_id = key 
                    continue
                
                # If we reach this point, node is plottable and needs to be considered in our algo
                entry_x = coord_dict[key][1] # x-coordinate of first point of the path
                entry_y = coord_dict[key][2] # y-coordinate of first point of the path

                exit_x = coord_dict[key][3] # x-coordinate of last point of the path
                exit_y = coord_dict[key][4] # y-coordinate of last point of the path

                object_dist = (entry_x-self.x_last)*(entry_x-self.x_last) + (entry_y-self.y_last) * (entry_y-self.y_last)
                # This is actually the distance squared; calculating it rather than the pythagorean distance
                #  saves a square root calculation. Right now, we only care about _which distance is less_
                #  not the exact value of it, so this is a harmless shortcut.
                # If this distance is smaller than the previous element's distance, then replace the previous
                # element's entry with our current element's distance 
                if nearest_dist >= object_dist:
                    # We have found an element closer than the previous closest element 
                    nearest = node
                    nearest_id = key 
                    nearest_dist = object_dist
                    nearest_start_x = entry_x
                    nearest_start_y = entry_y

            # Now that the closest object has been determined, it is time to add it to the 
            # optimized list of closest objects
            ordered_layer_element_list.append(nearest)
    
            # To determine the closest object in the next iteration of the loop, 
            # we must save the last x,y coor of this element
            # If this element is plottable, then save the x,y coordinates
            # If this element is non-plottable, then do not save the x,y coordinates
            if coord_dict[nearest_id][0]:
            
                # Also, draw line indicating that we've found a new point.
                if self.preview_rendering: 
                    preview_path = []    # pen-up path data for preview 

                    preview_path.append("M{0:.3f} {1:.3f}".format(
                        self.x_last, self.y_last))
                    preview_path.append("{0:.3f} {1:.3f}".format(
                        nearest_start_x, nearest_start_y))
                    self.p_style.update({'stroke': self.color_index(self.layer_index)})  
                    path_attrs = {
                        'style': simplestyle.formatStyle( self.p_style ),
                        'd': " ".join(preview_path)}
                        
                    etree.SubElement( self.preview_layer,
                        inkex.addNS( 'path', 'svg '), path_attrs, nsmap=inkex.NSS )

                self.x_last = coord_dict[nearest_id][3]
                self.y_last = coord_dict[nearest_id][4]

            # Remove this element from group_dict to indicate it has been optimized
            del group_dict[nearest_id]
    
        # Once all elements have been removed from the group_dictionary
        # Return the optimized list of svg elements in the layer
        return ordered_layer_element_list

    
    def color_index(self, index):
        index = index % 9
        
        if index == 0:
            return "rgb(255, 0, 0))"
        elif index == 1:
            return "rgb(170, 85, 0))"
        elif index == 2:
            return "rgb(85, 170, 0))"
        elif index == 3:
            return "rgb(0, 255, 0))"
        elif index == 4:
            return "rgb(0, 170, 85))"
        elif index == 5:
            return "rgb(0, 85, 170))"
        elif index == 6:
            return "rgb(0, 0, 255))"
        elif index == 7:
            return "rgb(85, 0, 170))"
        else:
            return "rgb(170, 0, 85))"


    def getDocProps(self):
        """
        Get the document's height and width attributes from the <svg> tag.
        Use a default value in case the property is not present or is
        expressed in units of percentages.
        """

        self.svg_height = plot_utils.getLengthInches(self, 'height')
        self.svg_width = plot_utils.getLengthInches(self, 'width')

        width_string = self.svg.get('width')
        if width_string:
            value, units = plot_utils.parseLengthWithUnits(width_string)
            self.doc_units = units

        if self.auto_rotate and (self.svg_height > self.svg_width):
            self.printPortrait = True
        if self.svg_height is None or self.svg_width is None:
            return False
        else:
            return True


    def get_output(self):
        # Return serialized copy of svg document output
        result = etree.tostring(self.document)
        return result.decode("utf-8")

# Create effect instance and apply it.

if __name__ == '__main__':
    effect = ReorderEffect()
    exit_status.run(effect.affect)
