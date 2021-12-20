import logging
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

    def __init__(self, bboxes, indent=''):
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
        
        #logging.debug(f'{indent}Count: {len(bboxes)}, Center x, y: {center_x:.2f}, {center_y:.2f}')
        #logging.debug(f'{indent}Bounds: {self.xmin:.2f}, {self.ymin:.2f}, {self.xmax:.2f}, {self.ymax:.2f}')
        
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
            self.subtrees = [Index(sub, indent+'  ') for sub in sub_bboxes]
    
    def intersection(self, bbox):
        ''' Get a set of IDs for a given bounding box
        '''
        ids = set()
        
        for (i, (xmin, ymin, xmax, ymax)) in self.bboxes:
            is_disjoint = bbox[0] > xmax or bbox[1] > ymax or bbox[2] < xmin or bbox[3] < ymin
            if not is_disjoint:
                ids.add(i)
        
        for subtree in self.subtrees:
            is_disjoint = bbox[0] > subtree.xmax or bbox[1] > subtree.ymax or bbox[2] < subtree.xmin or bbox[3] < subtree.ymin
            if not is_disjoint:
                ids |= subtree.intersection(bbox)
        
        return ids
