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
boundsclip.py

Functions for clipping

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw
"""

from axidrawinternal.plot_utils_import import from_dependency_import # plotink
plot_utils = from_dependency_import('plotink.plot_utils')

def clip_at_bounds(digest, phy_bounds, doc_bounds, warn_tol, doc_clip=True):
    """
    Step through subpaths in the digest, clipping them at plot
    boundaries, splitting them into additional subpaths if necessary.

    The plot boundary is defined by (0,0) and a maximum X and Y value
    which may be defined by the physical bounds, or both the physical
    bounds and the document bounds. Return a warning message if the
    requested travel exceeds the bounds by greater than the tolerance.

    Inputs:
    digest: A path_objects.DocDigest object
    phy_bounds: Physical bounds. A 4-element list: 
        [[x_min, y_min],[x_max, y_max]], adjusted out for rounding tolerance
    doc_bounds: Document bounds. A 2-element list with (x_max, y_max)
    warn_tol: Distance that motion exceed limits without warning messages
    doc_clip: Boolean. If True, clip at both phy_bounds and doc_bounds

    Output: Warning text or None

    Flatten the document prior to clipping if it is not already flattened.

    This routine performs no rotation; digest orientation should match
    orientation for which the bounds are given.

    Notes on boundaries and warnings about clipping:

    Generate a warning only if the requested motion:
    (1) Exceeds the physical bounds by at least the value of warn_tol, AND
    (2) Is clipped by physical limits, rather than the page size, AND
    (3) Is clipped in the positive direction (not at X = 0 or Y = 0).

    No warning will be generated when travel is limited by a document
    size smaller than the travel, nor at the lower limits of travel.

    Both sets of bounds are typically set slightly past the nominal
    boundaries, by a value typically 1e-9. This ensures that clipping is not
    applied to values that are within float precision of the nominal bounds.
    For example, if a square has a side at Y position at nominal zero but
    numericly  -1.05E-14, we do not want to clip, and thereby omit, that side.
    """
    clip_warn_x = True # Enable warnings about X clipping
    clip_warn_y = True # Enable warnings about Y clipping

    out_of_bounds_flag = False # No warning yet generated

    # Positive limits:
    [x_max, y_max] = phy_bounds[1]

    if doc_clip:
        [page_max_x, page_max_y] = doc_bounds
        if x_max >= page_max_x:
            clip_warn_x = False # Limited by page size, not travel size
            x_max = page_max_x
        if y_max >= page_max_y:
            clip_warn_y = False # Limited by page size, not travel size
            y_max = page_max_y

    clip_bounds = [phy_bounds[0], [x_max, y_max]]

    # Loose tolerance bounds for generating warning messages:
    x_max_warn = x_max + warn_tol
    y_max_warn = y_max + warn_tol

    digest.flatten()

    for layer in digest.layers:    # Each layer is a LayerItem object.
        for path in layer.paths: # Each path is a PathItem object.
            input_subpath = path.subpaths[0]
            new_subpaths = []
            a_subpath = []
            first_point = True
            prev_in_bounds = False
            prev_vertex = []

            for vertex in input_subpath:
                [v_x, v_y] = vertex

                in_bounds = plot_utils.point_in_bounds(vertex, clip_bounds, 0)
                if not in_bounds:
                    # Only check if there's no warning issued yet
                    if not out_of_bounds_flag:
                        if clip_warn_x:
                            if v_x > x_max_warn:
                                out_of_bounds_flag = True
                        if clip_warn_y:
                            if v_y > y_max_warn:
                                out_of_bounds_flag = True
                """
                Clipping logic:

                Possible cases, for first vertex:
                (1) In bounds: Add the vertex to the path.
                (2) Not in bounds: Do not add the vertex.

                Possible cases, for subsequent vertices:
                (1) In bounds, as was previous: Add the vertex.
                  -> No segment between two in-bound points needs clipping.
                (2) In bounds, prev was not: Clip & start new path.
                (3) OOB, prev was in bounds: Clip & end the path.
                (4) OOB, as was previous: Segment _may_ clip corner.
                  -> Either add no points or start & end new path
                """

                if first_point:
                    if in_bounds:
                        a_subpath.append(vertex)
                else:
                    if in_bounds and prev_in_bounds:
                        a_subpath.append(vertex)
                    else:
                        segment =  [prev_vertex, vertex]
                        accept, seg = plot_utils.clip_segment(segment, clip_bounds)
                        if accept:
                            if in_bounds and not prev_in_bounds:
                                if len(a_subpath) > 0:
                                    new_subpaths.append(a_subpath)
                                    a_subpath = [] # start new subpath
                                a_subpath.append([seg[0][0], seg[0][1]])
                                v_x = seg[1][0]
                                v_y = seg[1][1]
                                a_subpath.append([v_x, v_y])
                            if prev_in_bounds and not in_bounds:
                                v_x = seg[1][0]
                                v_y = seg[1][1]
                                a_subpath.append([v_x, v_y])
                                new_subpaths.append(a_subpath) # Save subpath
                                a_subpath = [] # Start new subpath
                            if (not prev_in_bounds) and not in_bounds:
                                if len(a_subpath) > 0:
                                    new_subpaths.append(a_subpath)
                                    a_subpath = [] # start new subpath
                                a_subpath.append([seg[0][0], seg[0][1]])
                                v_x = seg[1][0]
                                v_y = seg[1][1]
                                a_subpath.append([v_x, v_y])
                                new_subpaths.append(a_subpath) # Save subpath
                                a_subpath = [] # Start new subpath
                        else:
                            in_bounds = False
                first_point = False
                prev_vertex = vertex
                prev_in_bounds = in_bounds

            if len(a_subpath) > 0:
                new_subpaths.append(a_subpath)
            path.subpaths = new_subpaths
        layer.flatten() # Re-flatten layer
    return out_of_bounds_flag
