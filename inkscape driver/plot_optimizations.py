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
plot_optimizations.py

Version 1.1.0   -   2021-12-21

This module provides some plot optimization tools.

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

Requires Python 3.6 or newer.


The included functions operate upon a "flat" DocDigest object.

The "flattened" requirement means that each PathItem in each layer of
the DocDigest contains only a single subpath.


These functions include:
(A) connect_nearby_ends()
    - Search for and join nearby path ends in the layer, within given tolerance
    - If path reversal is enabled, allow paths to be reversed for joining

(B) randomize_start()
    - Randomize start location for closed paths

(C) reorder()
    - Perform nearest neighbor plot reordering, if enabled
    - If path reversal is enabled, allow paths to be reversed when sorting

"""

import random
import copy

from . import rtree
from axidrawinternal.plot_utils_import import from_dependency_import # plotink
path_objects = from_dependency_import('axidrawinternal.path_objects')
plot_utils = from_dependency_import('plotink.plot_utils')

def connect_nearby_ends(digest, reverse, min_gap):
    """
    Step through all PathItem objects in each layer.
    If the ends of two paths are close enough to join, then do so.
    If reverse is True, then allow paths to be reversed as part of
    the checks for whether path ends are close to one another.

    Inputs: digest: a path_objects.DocDigest object
            reverse (boolean) - True if paths can be reversed
            min_gap (float) - Distance below which to join paths
    """
    square_gap = min_gap * min_gap

    if min_gap < 0:  # Do not connect gaps
        return

    for layer_item in digest.layers:

        path_count = len(layer_item.paths)
        if path_count < 2:
            continue # Move on to next layer
        
        # Inflate point by min_gap to xmin, ymin, xmax, ymax rectangular bounds
        point_bounds = lambda x, y: (x - min_gap, y - min_gap, x + min_gap, y + min_gap)

        spatial_index = rtree.Index(
            [
                (index_i, point_bounds(*path.first_point()))
                for (index_i, path) in enumerate(layer_item.paths)
            ] + [
                (index_i + path_count, point_bounds(*path.last_point()))
                for (index_i, path) in enumerate(layer_item.paths)
            ]
        )

        paths_done = []

        index_i = 0
        while index_i < (path_count - 1):

            path_i = layer_item.paths[index_i]
            i_end = path_i.last_point()
            i_matches = list(spatial_index.intersection(point_bounds(*i_end)))
            if reverse:
                i_start = path_i.first_point()
                i_matches += list(spatial_index.intersection(point_bounds(*i_start)))
            
            for index_maybe in i_matches:
                match_found = False
                index_j = index_maybe % path_count

                if index_j <= index_i:
                    continue

                j_start = layer_item.paths[index_j].first_point()
                if reverse:
                    j_end = layer_item.paths[index_j].last_point()

                join_ij = plot_utils.points_near(i_end, j_start, square_gap)

                # Additional local variables to keep track of matches:
                rev_i, rev_j, rev_ij = False, False, False

                if reverse and not join_ij:
                    rev_i = plot_utils.points_near(i_start, j_start, square_gap)
                    rev_j = plot_utils.points_near(i_end, j_end, square_gap)
                    rev_ij = plot_utils.points_near(i_start, j_end, square_gap)

                if join_ij or rev_i or rev_j or rev_ij:
                    path_j = layer_item.paths[index_j]

                    if rev_i:
                        path_i.reverse()
                        i_end = i_start
                    elif rev_j:
                        path_j.reverse()
                        j_start = j_end
                    elif rev_ij:
                        path_i.reverse()
                        i_end = i_start
                        path_j.reverse()
                        j_start = j_end

                    if plot_utils.points_equal(i_end, j_start): # Remove redundant vertex
                        path_j.subpaths[0] = path_i.subpaths[0][:-1] + path_j.subpaths[0]
                    else:
                        path_j.subpaths[0] = path_i.subpaths[0] + path_j.subpaths[0]

                    match_found = True
                    break # End loop over index_j

                index_j += 1 # No paths to join

            if not match_found:
                paths_done.append(path_i) # We are done processing this path
            index_i += 1

        paths_done.append(layer_item.paths[path_count - 1]) # Add final path to our list
        layer_item.paths = paths_done


def randomize_start(digest, seed=None):
    """
    If a list of vertices describes a closed shape, where the start and end
    positions are equal (with a "fuzzy" floating-point comparison), then "rotate"
    the array of vertices to randomize the position where the shape starts and ends.

    When drawing (say) a set of otherwise identical concentric circles with a
    pen, there will be an artifact generated from where the pen touches down
    and retracts. These are small artifacts and may be hard to notice on their own.
    However, if all the start locations line up in a perfect row, the tiny artifacts
    tend to become quite visible.

    You can reduce the visibility of this artifact by randomizing the start
    location for closed paths, and this function does so.

    Inputs: digest: a path_objects.DocDigest object
            seed: Integer random seed
    """

    random.seed(seed) # initialize with given seed or None
    for layer_item in digest.layers:
        for path in layer_item.paths:
            vertex_list = path.subpaths[0]
            list_length = len(vertex_list)
            if list_length < 3:
                continue # No modification to trivially short paths

            if path.closed():
                rotate = random.randrange(list_length - 1)
                # Rotate, removing duplicate endpoint, adding new duplicate endpoint:
                path.subpaths[0] = vertex_list[rotate:] + vertex_list[1:rotate+1]

def reorder(digest, reverse):
    """
    Perform layer-aware path sorting, re-ordering paths within each layer for speed.

    Assume that a plot is a plot of _all layers_ starting at position 0,0
    for the purposes of reordering. This may not be the case in all situations,
    but at least the _first_ layer will have reasonably short travel to the first point.

    While there are still paths left to sort: # Outer loop
        For each remaining path: # Inner loop
            Check to see if the distance from our starting point
            to an endpoint of this path is the lowest of any of the paths.

    Inputs: digest: a path_objects.DocDigest object
            reverse (boolean) - True if paths can be reversed
    """

    last_point = (0, 0) # Represent starting position for a plot.

    for layer_item in digest.layers:

        sorted_paths = []
        reserved_paths = []
        available_paths = layer_item.paths
        available_count = len(available_paths)

        if available_count < 1:
            continue # No paths to sort; move on to next layer

        rev_path = False    # Flag: Should the current poly be reversed, if it is the best?
        rev_best = False    # Flag for if the "best" poly should be reversed
        prev_best = None    # Previous best path. Start with None on each layer

        while available_count > 0:
            min_dist = 1E100   # Initialize with a large number
            new_best = None    # Best path thus far within the inner loop

            for path in available_paths: # INNER LOOP
                best_so_far = False
                start = path.first_point()
                dist = plot_utils.square_dist(last_point, start)
                if dist < min_dist:
                    best_so_far = True
                    min_dist = dist
                    rev_path = False
                if reverse:
                    end = path.last_point()
                    dist_rev = plot_utils.square_dist(last_point, end)
                    if dist_rev < min_dist:
                        best_so_far = True
                        min_dist = dist_rev
                        rev_path = True
                if best_so_far:
                    if new_best is not None:
                        reserved_paths.append(new_best) # Set aside "old" best path
                    new_best = path
                    rev_best = rev_path
                else:
                    reserved_paths.append(path) # Reserve prior best for future use
            # END OF INNER LOOP

            if rev_best: # We have selected the next path; reverse it if flagged to do so.
                new_best.reverse()

            if prev_best is None:
                prev_best = new_best # Store
            else:
                sorted_paths.append(prev_best) # Reserve prior best for future use
                prev_best = new_best

            last_point = new_best.last_point()

            available_paths = copy.copy(reserved_paths)
            available_count = len(available_paths)
            reserved_paths = []

        sorted_paths.append(prev_best) # Add final path to our list
        layer_item.paths = copy.copy(sorted_paths)
