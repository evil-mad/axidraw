# -*- coding: utf-8 -*-
# plot_utils.py
# Common plotting utilities for EiBotBoard
# https://github.com/evil-mad/plotink
#
# Intended to provide some common interfaces that can be used by
# EggBot, WaterColorBot, AxiDraw, and similar machines.
#
# See below for version information
#
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

from math import sqrt

try:
    from plot_utils_import import from_dependency_import
    cspsubdiv = from_dependency_import('ink_extensions.cspsubdiv')
    simplepath = from_dependency_import('ink_extensions.simplepath')
    bezmisc = from_dependency_import('ink_extensions.bezmisc')
    ffgeom = from_dependency_import('ink_extensions.ffgeom')
except:
    import cspsubdiv
    import simplepath
    import bezmisc
    import ffgeom

def version():    # Version number for this document
    return "0.16" # Dated 2019-06-18

__version__ = version()

PX_PER_INCH = 96.0
# This value has changed to 96 px per inch, as of version 0.12 of this library.
# Prior versions used 90 PPI, corresponding the value used in Inkscape < 0.92.
# For use with Inkscape 0.91 (or older), use PX_PER_INCH = 90.0

trivial_svg = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
    <svg
       xmlns:dc="http://purl.org/dc/elements/1.1/"
       xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
       xmlns:svg="http://www.w3.org/2000/svg"
       xmlns="http://www.w3.org/2000/svg"
       version="1.1"
       id="svg15158"
       viewBox="0 0 297 210"
       height="210mm"
       width="297mm">
    </svg>
    """

def checkLimits(value, lower_bound, upper_bound):
    # Limit a value to within a range.
    # Return constrained value with error boolean.
    if value > upper_bound:
        return upper_bound, True
    if value < lower_bound:
        return lower_bound, True
    return value, False


def checkLimitsTol(value, lower_bound, upper_bound, tolerance):
    # Limit a value to within a range.
    # Return constrained value with error boolean.
    # Allow a range of tolerance where we constrain the value without an error message.

    if value > upper_bound:
        if value > (upper_bound + tolerance):
            return upper_bound, True  # Truncate & throw error
        else:
            return upper_bound, False  # Truncate with no error
    if value < lower_bound:
        if value < (lower_bound - tolerance):
            return lower_bound, True  # Truncate & throw error
        else:
            return lower_bound, False  # Truncate with no error
    return value, False  # Return original value without error


def clip_code(x, y, x_min, x_max, y_min, y_max):
    # Encode point position with respect to boundary box
    code = 0
    if x < x_min:
        code = 1  # Left
    if x > x_max:
        code |= 2 # Right
    if y < y_min:
        code |= 4 # Top
    if y > y_max:
        code |= 8 # Bottom
    return code


def clip_segment(segment, bounds):
    """
    Given an input line segment [[x1,y1],[x2,y2]], as well as a
    rectangular bounding region [[x_min,y_min],[x_max,y_max]], clip and
    keep the part of the segment within the bounding region, using the
    Cohen–Sutherland algorithm.
    Return a boolean value, "accept", indicating that the output
    segment is non-empty, as well as truncated segment,
    [[x1',y1'],[x2',y2']], giving the portion of the input line segment
    that fits within the bounds.
    """

    x1 = segment[0][0]
    y1 = segment[0][1]
    x2 = segment[1][0]
    y2 = segment[1][1]

    x_min = bounds[0][0]
    y_min = bounds[0][1]
    x_max = bounds[1][0]
    y_max = bounds[1][1]

    while True: # Repeat until return
        code_1 = clip_code(x1, y1, x_min, x_max, y_min, y_max)
        code_2 = clip_code(x2, y2, x_min, x_max, y_min, y_max)

        # Trivial accept:
        if code_1 == 0 and code_2 == 0:
            return True, segment # Both endpoints are within bounds.
        # Trivial reject, if both endpoints are outside, and on the same side:
        if code_1 & code_2:
            return False, segment # Verify with bitwise AND.

        # Otherwise, at least one point is out of bounds; not trivial.
        if code_1 != 0:
            code = code_1
        else:
            code = code_2

        # Clip at a single boundary; may need to do this up to twice per vertex

        if code & 1: # Vertex on LEFT side of bounds:
            x = x_min  # Find intersection of our segment with x_min
            slope = (y2 - y1) / (x2 - x1)
            y = slope * (x_min - x1) + y1

        elif code & 2:  # Vertex on RIGHT side of bounds:
            x = x_max # Find intersection of our segment with x_max
            slope = (y2 - y1) / (x2 - x1)
            y = slope * (x_max - x1) + y1

        elif code & 4: # Vertex on TOP side of bounds:
            y = y_min  # Find intersection of our segment with y_min
            slope = (x2 - x1) / (y2 - y1)
            x = slope * (y_min - y1) + x1

        elif code & 8: # Vertex on BOTTOM side of bounds:
            y = y_max  # Find intersection of our segment with y_max
            slope = (x2 - x1) / (y2 - y1)
            x = slope * (y_max - y1) + x1

        if code == code_1:
            x1 = x
            y1 = y
        else:
            x2 = x
            y2 = y
        segment = [[x1,y1],[x2,y2]] # Now checking this clipped segment


def constrainLimits(value, lower_bound, upper_bound):
    # Limit a value to within a range.
    return max(lower_bound, min(upper_bound, value))


def distance(x, y):
    """
    Pythagorean theorem
    """
    return sqrt(x * x + y * y)


def dotProductXY(input_vector_first, input_vector_second):
    temp = input_vector_first[0] * input_vector_second[0] + input_vector_first[1] * input_vector_second[1]
    if temp > 1:
        return 1
    elif temp < -1:
        return -1
    else:
        return temp


def getLength(altself, name, default):
    """
    Get the <svg> attribute with name "name" and default value "default"
    Parse the attribute into a value and associated units.  Then, accept
    no units (''), units of pixels ('px'), and units of percentage ('%').
    Return value in px.
    """
    string_to_parse = altself.document.getroot().get(name)

    if string_to_parse:
        v, u = parseLengthWithUnits(string_to_parse)
        if v is None:
            return None
        elif u == '' or u == 'px':
            return float(v)
        elif u == 'in':
            return float(v) * PX_PER_INCH
        elif u == 'mm':
            return float(v) * PX_PER_INCH / 25.4
        elif u == 'cm':
            return float(v) * PX_PER_INCH / 2.54
        elif u == 'Q' or u == 'q':
            return float(v) * PX_PER_INCH / (40.0 * 2.54)
        elif u == 'pc':
            return float(v) * PX_PER_INCH / 6.0
        elif u == 'pt':
            return float(v) * PX_PER_INCH / 72.0
        elif u == '%':
            return float(default) * v / 100.0
        else:
            # Unsupported units
            return None
    else:
        # No width specified; assume the default value
        return float(default)


def getLengthInches(altself, name):
    """
    Get the <svg> attribute with name "name", and parse it as a length,
    into a value and associated units. Return value in inches.

    As of version 0.11, units of 'px' or no units ('') are interpreted
    as imported px, at a resolution of 96 px per inch, as per the SVG
    specification. (Prior versions returned None in this case.)

    This allows certain imported SVG files, (imported with units of px)
    to plot while they would not previously. However, it may also cause
    new scaling issues in some circumstances. Note, for example, that
    Adobe Illustrator uses 72 px per inch, and Inkscape used 90 px per
    inch prior to version 0.92.
    """
    string_to_parse = altself.document.getroot().get(name)
    if string_to_parse:
        v, u = parseLengthWithUnits(string_to_parse)
        if v is None:
            return None
        elif u == 'in':
            return float(v)
        elif u == 'mm':
            return float(v) / 25.4
        elif u == 'cm':
            return float(v) / 2.54
        elif u == 'Q' or u == 'q':
            return float(v) / (40.0 * 2.54)
        elif u == 'pc':
            return float(v) / 6.0
        elif u == 'pt':
            return float(v) / 72.0
        elif u == '' or u == 'px':
            return float(v) / 96.0
        else:
            # Unsupported units, including '%'
            return None


def parseLengthWithUnits(string_to_parse):
    """
    Parse an SVG value which may or may not have units attached.
    There is a more general routine to consider in scour.py if more
    generality is ever needed.
    """
    u = 'px'
    s = string_to_parse.strip()
    if s[-2:] == 'px':  # pixels, at a size of PX_PER_INCH per inch
        s = s[:-2]
    elif s[-2:] == 'in':  # inches
        s = s[:-2]
        u = 'in'
    elif s[-2:] == 'mm':  # millimeters
        s = s[:-2]
        u = 'mm'
    elif s[-2:] == 'cm':  # centimeters
        s = s[:-2]
        u = 'cm'
    elif s[-2:] == 'pt':  # points; 1pt = 1/72th of 1in
        s = s[:-2]
        u = 'pt'
    elif s[-2:] == 'pc':  # picas; 1pc = 1/6th of 1in
        s = s[:-2]
        u = 'pc'
    elif s[-1:] == 'Q' or s[-1:] == 'q':  # quarter-millimeters. 1q = 1/40th of 1cm
        s = s[:-1]
        u = 'Q'
    elif s[-1:] == '%':
        u = '%'
        s = s[:-1]

    try:
        v = float(s)
    except:
        return None, None

    return v, u


def unitsToUserUnits(input_string):
    """
    Custom replacement for the unittouu routine in inkex.py

    Parse the attribute into a value and associated units.
    Return value in user units (typically "px").
    """

    v, u = parseLengthWithUnits(input_string)
    if v is None:
        return None
    elif u == '' or u == 'px':
        return float(v)
    elif u == 'in':
        return float(v) * PX_PER_INCH
    elif u == 'mm':
        return float(v) * PX_PER_INCH / 25.4
    elif u == 'cm':
        return float(v) * PX_PER_INCH / 2.54
    elif u == 'Q' or u == 'q':
        return float(v) * PX_PER_INCH / (40.0 * 2.54)
    elif u == 'pc':
        return float(v) * PX_PER_INCH / 6.0
    elif u == 'pt':
        return float(v) * PX_PER_INCH / 72.0
    elif u == '%':
        return float(v) / 100.0
    else:
        # Unsupported units
        return None


def subdivideCubicPath(sp, flat, i=1):
    """
    Break up a bezier curve into smaller curves, each of which
    is approximately a straight line within a given tolerance
    (the "smoothness" defined by [flat]).

    This is a modified version of cspsubdiv.cspsubdiv(). I rewrote the recursive
    call because it caused recursion-depth errors on complicated line segments.
    """

    while True:
        while True:
            if i >= len(sp):
                return
            p0 = sp[i - 1][1]
            p1 = sp[i - 1][2]
            p2 = sp[i][0]
            p3 = sp[i][1]

            b = (p0, p1, p2, p3)

            if cspsubdiv.maxdist(b) > flat:
                break
            i += 1

        one, two = bezmisc.beziersplitatt(b, 0.5)
        sp[i - 1][2] = one[1]
        sp[i][0] = two[2]
        p = [one[2], one[3], two[1]]
        sp[i:1] = [p]

def max_dist_from_n_points(input):
    """
    Like cspsubdiv.maxdist, but it can check for distances of any number of points >= 0.

    `input` is an ordered collection of points, each point specified as an x- and y-coordinate.
    The first point and the last point define the segment we are finding distances from.

    does not mutate `input`
    """
    assert len(input) >= 3, "There must be points (other than begin/end) to check."

    points = [ffgeom.Point(point[0], point[1]) for point in input]
    segment = ffgeom.Segment(points.pop(0), points.pop())

    distances = [segment.distanceToPoint(point) for point in points]
    return max(distances)

def supersample(vertices, tolerance):
    """
    Given a list of vertices, remove some according to the following algorithm.

    Suppose that the vertex list consists of points A, B, C, D, E, and so forth, which define segments AB, BC, CD, DE, EF, and so on.

    We first test to see if vertex B can be removed, by using perpDistanceToPoint to check whether the distance between B and segment AC is less than tolerance.
    If B can be removed, then check to see if the next vertex, C, can be removed. Both B and C can be removed if the both the distance between B and AD is less than Tolerance and the distance between C and AD is less than Tolerance. Continue removing additional vertices, so long as the perpendicular distance between every point removed and the resulting segment is less than tolerance (and the end of the vertex list is not reached).
If B cannot be removed, then move onto vertex C, and perform the same checks, until the end of the vertex list is reached.
    """
    if len(vertices) <= 2: # there is nothing to delete
        return vertices

    start_index = 0 # can't remove first vertex
    while start_index < len(vertices) - 2:
        end_index = start_index + 2
        # test the removal of (start_index, end_index), exclusive until we can't advance end_index
        while (max_dist_from_n_points(vertices[start_index:end_index + 1]) < tolerance
               and end_index < len(vertices)):
            end_index += 1 # try removing the next vertex too

        vertices[start_index + 1:end_index - 1] = [] # delete (start_index, end_index), exclusive
        start_index += 1

def userUnitToUnits(distance_uu, unit_string):
    """
    Custom replacement for the uutounit routine in inkex.py

    Parse the attribute into a value and associated units.
    Return value in user units (typically "px").
    """

    if distance_uu is None:  # Couldn't parse the value
        return None
    elif unit_string == '' or unit_string == 'px':
        return float(distance_uu)
    elif unit_string == 'in':
        return float(distance_uu) / PX_PER_INCH
    elif unit_string == 'mm':
        return float(distance_uu) / (PX_PER_INCH / 25.4)
    elif unit_string == 'cm':
        return float(distance_uu) / (PX_PER_INCH / 2.54)
    elif unit_string == 'Q' or unit_string == 'q':
        return float(distance_uu) / (PX_PER_INCH / (40.0 * 2.54))
    elif unit_string == 'pc':
        return float(distance_uu) / (PX_PER_INCH / 6.0)
    elif unit_string == 'pt':
        return float(distance_uu) / (PX_PER_INCH / 72.0)
    elif unit_string == '%':
        return float(distance_uu) * 100.0
    else:
        # Unsupported units
        return None


def vb_scale(vb, p_a_r, doc_width, doc_height):
    """"
    Parse SVG viewbox and generate scaling parameters.
    Reference documentation: https://www.w3.org/TR/SVG11/coords.html
    
    Inputs:
        vb:         Contents of SVG viewbox attribute
        p_a_r:      Contents of SVG preserveAspectRatio attribute
        doc_width:  Width of SVG document
        doc_height: Height of SVG document
        
    Output: sx, sy, ox, oy
        Scale parameters (sx,sy) and offset parameters (ox,oy)
    
    """
    if vb is None:
        return 1,1,0,0 # No viewbox; return default transform
    else:
        vb_array = vb.strip().replace(',', ' ').split()
        
        if len(vb_array) < 4:
            return 1,1,0,0 # invalid viewbox; return default transform
    
        min_x =  float(vb_array[0]) # Viewbox offset: x
        min_y =  float(vb_array[1]) # Viewbox offset: y
        width =  float(vb_array[2]) # Viewbox width
        height = float(vb_array[3]) # Viewbox height

        if width <= 0 or height <= 0:
            return 1,1,0,0 # invalid viewbox; return default transform
        
        d_width = float(doc_width)
        d_height = float(doc_height)

        if d_width <= 0 or d_height <= 0:
            return 1,1,0,0 # invalid document size; return default transform

        ar_doc = d_height / d_width # Document aspect ratio
        ar_vb = height / width      # Viewbox aspect ratio
        
        # Default values of the two preserveAspectRatio parameters:
        par_align = "xmidymid" # "align" parameter (lowercased)
        par_mos = "meet"       # "meetOrSlice" parameter
        
        if p_a_r is not None:
            par_array = p_a_r.strip().replace(',', ' ').lower().split()
            if len(par_array) > 0:
                par0 = par_array[0]
                if par0 == "defer":
                    if len(par_array) > 1:
                        par_align = par_array[1]
                        if len(par_array) > 2:
                            par_mos = par_array[2]
                else:
                    par_align = par0
                    if len(par_array) > 1:
                        par_mos = par_array[1]

        if par_align == "none":
            # Scale document to fill page. Do not preserve aspect ratio.
            # This is not default behavior, nor what happens if par_align
            # is not given; the "none" value must be _explicitly_ specified.

            sx = d_width/ width
            sy = d_height / height
            ox = -min_x
            oy = -min_y
            return sx,sy,ox,oy
            
        """
        Other than "none", all situations fall into two classes:
        
        1)   (ar_doc >= ar_vb AND par_mos == "meet")
               or  (ar_doc < ar_vb AND par_mos == "slice")
            -> In these cases, scale document up until VB fills doc in X.
        
        2)   All other cases, i.e.,
            (ar_doc < ar_vb AND par_mos == "meet")
               or  (ar_doc >= ar_vb AND par_mos == "slice")
            -> In these cases, scale document up until VB fills doc in Y.
        
        Note in cases where the scaled viewbox exceeds the document
        (page) boundaries (all "slice" cases and many "meet" cases where
        an offset value is given) that this routine does not perform 
        any clipping, but subsequent clipping to the page boundary
        is appropriate.
        
        Besides "none", there are 9 possible values of par_align:
            xminymin xmidymin xmaxymin
            xminymid xmidymid xmaxymid
            xminymax xmidymax xmaxymax
        """

        if (((ar_doc >= ar_vb) and (par_mos == "meet"))
            or ((ar_doc < ar_vb) and (par_mos == "slice"))):
            # Case 1: Scale document up until VB fills doc in X.

            sx = d_width / width
            sy = sx # Uniform aspect ratio
            ox = -min_x
            
            scaled_vb_height = ar_doc * width
            excess_height = scaled_vb_height - height

            if par_align in {"xminymin", "xmidymin", "xmaxymin"}:
                # Case: Y-Min: Align viewbox to minimum Y of the viewport.
                oy = -min_y
                # OK: tested with Tall-Meet, Wide-Slice

            elif par_align in {"xminymax", "xmidymax", "xmaxymax"}:
                # Case: Y-Max: Align viewbox to maximum Y of the viewport.
                oy = -min_y + excess_height
                #  OK: tested with Tall-Meet, Wide-Slice

            else: # par_align in {"xminymid", "xmidymid", "xmaxymid"}:
                # Default case: Y-Mid: Center viewbox on page in Y
                oy = -min_y + excess_height / 2
                # OK: Tested with Tall-Meet, Wide-Slice
                
            return sx,sy,ox,oy
        else:
            # Case 2: Scale document up until VB fills doc in Y.
            
            sy = d_height / height
            sx = sy # Uniform aspect ratio
            oy = -min_y

            scaled_vb_width = height / ar_doc
            excess_width = scaled_vb_width - width

            if par_align in {"xminymin", "xminymid", "xminymax"}:
                # Case: X-Min: Align viewbox to minimum X of the viewport.
                ox = -min_x 
                # OK: Tested with Tall-Slice, Wide-Meet

            elif par_align in {"xmaxymin", "xmaxymid", "xmaxymax"}:
                # Case: X-Max: Align viewbox to maximum X of the viewport.
                ox = -min_x + excess_width
                # Need test: Tall-Slice, Wide-Meet

            else: # par_align in {"xmidymin", "xmidymid", "xmidymax"}:
                # Default case: X-Mid: Center viewbox on page in X
                ox = -min_x + excess_width / 2
                # OK: Tested with Tall-Slice, Wide-Meet
                
            return sx,sy,ox,oy
    return 1,1,0,0 # Catch-all: return default transform


def vInitial_VF_A_Dx(v_final, acceleration, delta_x):
    """
    Kinematic calculation: Maximum allowed initial velocity to arrive at distance X
    with specified final velocity, and given maximum linear acceleration.

    Calculate and return the (real) initial velocity, given an final velocity,
        acceleration rate, and distance interval.

    Uses the kinematic equation Vi^2 = Vf^2 - 2 a D_x , where
            Vf is the final velocity,
            a is the acceleration rate,
            D_x (delta x) is the distance interval, and
            Vi is the initial velocity.

    We are looking at the positive root only-- if the argument of the sqrt
        is less than zero, return -1, to indicate a failure.
    """
    initial_v_squared = (v_final * v_final) - (2 * acceleration * delta_x)
    if initial_v_squared > 0:
        return sqrt(initial_v_squared)
    else:
        return -1


def vFinal_Vi_A_Dx(v_initial, acceleration, delta_x):
    """
    Kinematic calculation: Final velocity with constant linear acceleration.

    Calculate and return the (real) final velocity, given an initial velocity,
        acceleration rate, and distance interval.

    Uses the kinematic equation Vf^2 = 2 a D_x + Vi^2, where
            Vf is the final velocity,
            a is the acceleration rate,
            D_x (delta x) is the distance interval, and
            Vi is the initial velocity.

    We are looking at the positive root only-- if the argument of the sqrt
        is less than zero, return -1, to indicate a failure.
    """
    final_v_squared = (2 * acceleration * delta_x) + (v_initial * v_initial)
    if final_v_squared > 0:
        return sqrt(final_v_squared)
    else:
        return -1


def pathdata_first_point(path):
    """
    Return the first (X,Y) point from an SVG path data string

    Input:  A path data string; the text of the 'd' attribute of an SVG path
    Output: Two floats in a list representing the x and y coordinates of the first point
    """

    # Path origin's default values are used to see if we have
    # Written anything to the path_origin variable yet
    MaxLength = len(path)
    ix = 0
    tempString = ''
    x_val = ''
    y_val = ''
    # Check one char at a time
    # until we have the moveTo Command
    while ix < MaxLength:
        if path[ix].upper() == 'M':
            break
        # Increment until we have M
        ix = ix + 1

    # Parse path until we reach a digit, decimal point or negative sign
    while ix < MaxLength:
        if(path[ix].isdigit()) or path[ix] == '.' or path[ix] == '-':
            break
        ix = ix + 1

    # Add digits and decimal points to x_val
    # Stop parsing when next character is neither a digit nor a decimal point
    while ix < MaxLength:
        if  (path[ix].isdigit()):
            tempString = tempString + path[ix]
            x_val = float(tempString )
            ix = ix + 1
        # If next character is a decimal place, save the decimal and continue parsing
        # This allows for paths without leading zeros to be parsed correctly
        elif (path[ix] == '.' or path[ix] == '-'):
            tempString = tempString + path[ix]
            ix = ix + 1
        else:
            ix = ix + 1
            break

    # Reset tempString for y coordinate
    tempString = ''

    # Parse path until we reach a digit or decimal point
    while ix < MaxLength:
        if(path[ix].isdigit()) or path[ix] == '.' or path[ix] == '-':
            break
            ix = ix + 1

    # Add digits and decimal points to y_val
    # Stop parsin when next character is neither a digit nor a decimal point
    while ix < MaxLength:
        if (path[ix].isdigit() ):
            tempString = tempString + path[ix]
            y_val = float(tempString)
            ix = ix + 1
        # If next character is a decimal place, save the decimal and continue parsing
        # This allows for paths without leading zeros to be parsed correctly
        elif (path[ix] == '.' or path[ix] == '-'):
            tempString = tempString + path[ix]
            ix = ix + 1
        else:
            ix = ix + 1
            break
    return [x_val,y_val]


def pathdata_last_point(path):
    """
    Return the last (X,Y) point from an SVG path data string

    Input:  A path data string; the text of the 'd' attribute of an SVG path
    Output: Two floats in a list representing the x and y coordinates of the last point
    """

    command, params = simplepath.parsePath(path)[-1] # parsePath splits path into segments

    if command.upper() == 'Z':
        return pathdata_first_point(path)	# Trivial case

    """
    Otherwise: The last command should be in the set 'MLCQA'
        - All commands converted to absolute by parsePath.
        - Can ignore Z (case handled)
        - Can ignore H,V, since those are converted to L by parsePath.
        - Can ignore S, converted to C by parsePath.
        - Can ignore T, converted to Q by parsePath.

        MLCQA: Commands all ending in (X,Y) pair.
    """

    x_val = params[-2] # Second to last parameter given
    y_val = params[-1] # Last parameter given

    return [x_val,y_val]
