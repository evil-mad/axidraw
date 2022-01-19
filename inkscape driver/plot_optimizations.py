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
plot_optimizations.py

Version 1.1.0   -   2022-01-03

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
import math
from axidrawinternal.plot_utils_import import from_dependency_import # plotink

path_objects = from_dependency_import('axidrawinternal.path_objects')
plot_utils = from_dependency_import('plotink.plot_utils')
rtree = from_dependency_import('plotink.rtree')
spatial_grid = from_dependency_import('plotink.spatial_grid')


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

    for layer_item in digest.layers:
        available_count = len(layer_item.paths)

        if available_count <= 1:
            continue # No sortable paths; move on to next layer

        tour_path = []

        endpoints = []
        for path_reference in layer_item.paths:
            endpoints.append([path_reference.first_point(), path_reference.last_point()])

        if reverse:
            grid_bins = 4 + math.floor(math.sqrt(available_count / 25))
        else:
            grid_bins = 4 + math.floor(math.sqrt(available_count / 50))
        grid_index = spatial_grid.Index(endpoints, grid_bins, reverse)

        vertex = [0, 0] # Starting position of plot: (0,0)

        while True:
            nearest_index = grid_index.nearest(vertex)

            if nearest_index is None:
                break # Exhausted paths in the index; tour is complete

            if nearest_index >= available_count:
                nearest_index -= available_count
                rev_path = True
                vertex = endpoints[nearest_index][0] # First vertex of selected path
            else:
                rev_path = False
                vertex = endpoints[nearest_index][1] # Last vertex of selected path

            tour_path.append([nearest_index, rev_path])

            grid_index.remove_path(nearest_index) # Exclude this path's ends from the search

        # Re-ordering is done; Update the list of paths in the layer.
        output_path_temp = []
        for path_number, rev_path in tour_path:
            next_path = layer_item.paths[path_number]
            if rev_path:
                next_path.reverse()
            output_path_temp.append(next_path)
        layer_item.paths = copy.copy(output_path_temp)
