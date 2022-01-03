# -*- coding: utf-8 -*-
# spatial_grid.py
# part of plotink: https://github.com/evil-mad/plotink
#
# See below for version information
#
# Copyright (c) 2022 Windell H. Oskay, Evil Mad Scientist Laboratories
#
# The MIT License (MIT)
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

"""
spatial_grid.py

Specialized grid spatial index class for calculating nearest neighbors
"""


import math

from axidrawinternal.plot_utils_import import from_dependency_import # plotink
plot_utils = from_dependency_import('plotink.plot_utils')


class Index:
    ''' Grid index class '''
    grid = []           # The grid; list of path ends in each cell
    adjacents = []      # Adjacency list; list of neighboring cells for each cell
    lookup = []         # List of which grid cell each path end can be found inside.
    path_count = 0      # Initial number of paths
    vertices = None     # The list of start, end vertices for each path
    reverse = False     # Boolean: Are path reversals allowed?
    bin_size_x = 1.0    # Width of grid cells
    bin_size_y = 1.0    # Height of grid cells
    xmin = -1.0         # Grid bounds
    ymin = -1.0         # Grid bounds
    bins_per_side = 3   # Number of bins per side of the grid

    def __init__(self, vertices, bins_per_side, reverse):
        '''
        Given an input list of path vertices and number of bins per side,
        populate a 1D list that represents a linearized 2D grid,
        bins_per_side x bins_per_side in size. Each cell contains a list that
        indicates which path numbers have ends that can be found in that cell.

        Also populate an adjacency list where each cell contains a list of
        which cells are that cell or its neighbors; up to 9 possible.

        And, populate a 1D "reverse" lookup list that gives the grid-cell
        location of each path end.

        Input vertices is a 1D list of elements: [first_vertex, last_vertex]
        for each path. Each vertex is a (x,y) tuple.

        self.bins_per_side is an integer, that once squared gives the number of grid
        cells. Practical minimum of 3, for 9 squares.

        reverse is boolean, indicating whether the paths can be reversed.
        '''

        self.vertices = vertices
        self.reverse = reverse
        self.bins_per_side = bins_per_side
        self.path_count = len(vertices)
        max_bin = bins_per_side - 1 # array index of the largest x or y bin

        self.find_adjacents()

        # Calculate extent of grid:
        self.xmin, self.ymin = math.inf, math.inf
        xmax, ymax = -math.inf, -math.inf

        for [x_1, y_1], [x_2, y_2] in self.vertices:
            self.xmin = min(self.xmin, x_1)
            xmax = max(xmax, x_1)
            self.ymin = min(self.ymin, y_1)
            ymax = max(ymax, y_1)
            if reverse:
                self.xmin = min(self.xmin, x_2)
                xmax = max(xmax, x_2)
                self.ymin = min(self.ymin, y_2)
                ymax = max(ymax, y_2)

        # Artificially increase size of grid to avoid vertices on the borders:
        shim = (xmax - self.xmin + ymax - self.ymin) / 200
        self.xmin -= shim
        self.ymin -= shim
        xmax += shim
        ymax += shim

        # Calculate bin sizes:
        self.bin_size_x = (xmax - self.xmin) / bins_per_side
        self.bin_size_y = (ymax - self.ymin) / bins_per_side

        # Initialize the "reverse" lookup list:
        if reverse:
            self.lookup = [0 for temp_var in range(2 * self.path_count)]
        else:
            self.lookup = [0 for temp_var in range(self.path_count)]

        # Initialize the grid, with an empty list in each cell:
        self.grid = [[] for index_i in range(self.bins_per_side * self.bins_per_side)]

        for (index_i, [[x_1, y_1], [x_2, y_2]]) in enumerate(self.vertices):
            x_bin = min(math.floor((x_1 - self.xmin) / self.bin_size_x), max_bin)
            y_bin = min(math.floor((y_1 - self.ymin) / self.bin_size_y), max_bin)
            grid_index = x_bin + self.bins_per_side * y_bin
            self.grid[grid_index].append(index_i)
            self.lookup[index_i] = grid_index # Which grid cell is the path start in?

            if reverse:
                x_bin = min(math.floor((x_2 - self.xmin) / self.bin_size_x), max_bin)
                y_bin = min(math.floor((y_2 - self.ymin) / self.bin_size_y), max_bin)
                grid_index = x_bin + self.bins_per_side * y_bin
                self.grid[grid_index].append(self.path_count + index_i)
                self.lookup[self.path_count + index_i] = grid_index


    def find_adjacents(self):
        '''
        Also populate an adjacency list, where each cell contains a list of
        which cells are that cell or its neighbors; up to 9 possible. 
        '''
        max_bin = self.bins_per_side - 1

        self.adjacents = [[a_s] for a_s in range(self.bins_per_side * self.bins_per_side)]
        for y_row in range(self.bins_per_side):
            for x_col in range(self.bins_per_side):
                index_i = x_col + y_row * (self.bins_per_side)
                if x_col > 0:
                    self.adjacents[index_i].append(index_i - 1) # OK
                    if y_row > 0:
                        self.adjacents[index_i].append(index_i - self.bins_per_side - 1)
                    if y_row < max_bin:
                        self.adjacents[index_i].append(index_i + self.bins_per_side - 1)
                if x_col < max_bin:
                    self.adjacents[index_i].append(index_i + 1)
                    if y_row > 0:
                        self.adjacents[index_i].append(index_i - self.bins_per_side + 1)
                    if y_row < max_bin:
                        self.adjacents[index_i].append(index_i + self.bins_per_side + 1)
                if y_row > 0:
                    self.adjacents[index_i].append(index_i - self.bins_per_side)
                if y_row < max_bin:
                    self.adjacents[index_i].append(index_i + self.bins_per_side)


    def nearest(self, vertex_in):
        '''
        Find the nearest path end to the given vertex and return its index.
        Input last_vertex is a [x, y] list.

        Method:
            * Locate which grid cell the input vertex is located in.
            * For every vertex in that grid cell, plus the (up to) eight surrounding it,
                check to see if it is the nearest neighbor to the input vertex.
                If so, return the index of that closest vertex.

            * If there are no vertices in those (up to) 9 cells, check the entire rest of
                the document, and find the closest (global) point.

            * If no vertices are found at all, return None

        The neighborhood of up 8 cells surrounding the initial cell serves as a crude
        circular region surrounding the vertex. In most (but not all) cases, the
        nearest point within that region will be the nearest point globally.
        The precision of that "circle" could be improved by using a finer grid, and a
        larger number of adjacent cells to check.
        '''

        max_bin = self.bins_per_side - 1

        x_bin = min(math.floor((vertex_in[0] - self.xmin) / self.bin_size_x), max_bin)
        y_bin = min(math.floor((vertex_in[1] - self.ymin) / self.bin_size_y), max_bin)
        last_cell = max(x_bin + self.bins_per_side * y_bin, 0)

        neighborhood_cells = self.adjacents[last_cell].copy()

        best_dist = math.inf
        best_index = None
        for cell in neighborhood_cells:
            for path_index in self.grid[cell]:
                if path_index >= self.path_count: # new path is reversed
                    vertex = self.vertices[path_index - self.path_count][1]
                else:
                    vertex = self.vertices[path_index][0] # Beginning of next path

                dist = plot_utils.square_dist(vertex_in, vertex)
                if dist < best_dist:
                    best_dist = dist
                    best_index = path_index
        if best_index:
            return best_index

        # Fallback: Check remaining cells if no points were found in neighborhood:
        for cell in range (len(self.adjacents)):
            if cell in neighborhood_cells:
                continue
            for path_index in self.grid[cell]:
                if path_index >= self.path_count: # new path is reversed
                    vertex = self.vertices[path_index - self.path_count][1]
                else:
                    vertex = self.vertices[path_index][0]

                dist = plot_utils.square_dist(vertex_in, vertex)
                if dist < best_dist:
                    best_dist = dist
                    best_index = path_index
        return best_index


    def remove_path(self, path_index):
        '''
        Remove the vertex with the given path_index from the spatial index.
        path_index should be less than self.path_count.

        If reversing is enabled, also remove the vertex with index
        path_index + self.path_count
        '''

        cell_number = self.lookup[path_index]
        self.grid[cell_number].remove(path_index)

        if not self.reverse:
            return

        other_index = path_index + self.path_count
        cell_number = self.lookup[other_index]
        self.grid[cell_number].remove(other_index)
