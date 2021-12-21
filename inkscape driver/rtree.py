# -*- coding: utf-8 -*-
# text_utils.py
# Common text processing utilities
# https://github.com/evil-mad/plotink
#
# See below for version information
#
# Written by Michal Migurski https://github.com/migurski @michalmigurski
# as a contribution to the AxiDraw project https://github.com/evil-mad/axidraw/
#
# Copyright (c) 2021 Windell H. Oskay, Evil Mad Scientist Laboratories
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

import math

class Index:
    ''' One-shot R-Tree index (no rebalancing, insertions, etc.)
    '''
    bboxes = []
    subtrees = []
    xmin = None
    ymin = None
    xmax = None
    ymax = None

    def __init__(self, bboxes):
        center_x, center_y = 0, 0
        self.xmin, self.ymin = math.inf, math.inf
        self.xmax, self.ymax = -math.inf, -math.inf

        for (_, (xmin, ymin, xmax, ymax)) in bboxes:
            center_x += (xmin/2 + xmax/2) / len(bboxes)
            center_y += (ymin/2 + ymax/2) / len(bboxes)
            self.xmin = min(self.xmin, xmin)
            self.ymin = min(self.ymin, ymin)
            self.xmax = max(self.xmax, xmax)
            self.ymax = max(self.ymax, ymax)

        # Make four lists of bboxes, one for each quadrant around the center point
        # An original bbox may be present in more than one list
        sub_bboxes = [
            [
                (i, (x1, y1, x2, y2)) for (i, (x1, y1, x2, y2)) in bboxes
                if x1 < center_x and y1 < center_y
            ],
            [
                (i, (x1, y1, x2, y2)) for (i, (x1, y1, x2, y2)) in bboxes
                if x2 > center_x and y1 < center_y
            ],
            [
                (i, (x1, y1, x2, y2)) for (i, (x1, y1, x2, y2)) in bboxes
                if x1 < center_x and y2 > center_y
            ],
            [
                (i, (x1, y1, x2, y2)) for (i, (x1, y1, x2, y2)) in bboxes
                if x2 > center_x and y2 > center_y
            ],
        ]

        # Store bboxes or subtrees but not both
        if max(map(len, sub_bboxes)) == len(bboxes):
            # One of the subtrees is identical to the whole tree so just keep all the bboxes
            self.bboxes = bboxes
        else:
            # Make four subtrees, one for each quadrant
            self.subtrees = [Index(sub) for sub in sub_bboxes]

    def intersection(self, bbox):
        ''' Get a set of IDs for a given bounding box
        '''
        ids, (x1, y1, x2, y2) = set(), bbox

        for (i, (xmin, ymin, xmax, ymax)) in self.bboxes:
            is_disjoint = x1 > xmax or y1 > ymax or x2 < xmin or y2 < ymin
            if not is_disjoint:
                ids.add(i)

        for t in self.subtrees:
            is_disjoint = x1 > t.xmax or y1 > t.ymax or x2 < t.xmin or y2 < t.ymin
            if not is_disjoint:
                ids |= t.intersection(bbox)

        return ids
