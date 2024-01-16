''' hidden line hiding--see https://gitlab.com/evil-mad/AxiDraw-Internal/-/issues/3 '''

from abc import ABC, abstractmethod
from copy import copy
from enum import Enum
from itertools import filterfalse
import logging

import pyclipper

from axidrawinternal.path_objects import FillRule
from plotink import plot_utils

print_warnings = False # set to True to see warnings printed

class DeduplicateMessages(logging.Filter):
    def __init__(self):
        self.cache = set()

    def filter(self, log_record):
        if log_record.getMessage() in self.cache:
            return 0 # message already emitted, do not emit again
        else:
            self.cache.add(log_record.getMessage())
            return 1 # emit message

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARN if print_warnings else logging.ERROR)
logger.addFilter(DeduplicateMessages())

class ClipPathsProcess:
    ''' NOTE: does not preserve the direction of the strokes '''
    def __init__(self, clipping_path_cls=None):
        # clipping_path_cls is a class that subclasses AbstractClippingPathItem
        if clipping_path_cls is None:
            clipping_path_cls = _ClippingPathItem_pyclipper

        self.clipping_path_cls=clipping_path_cls

    def run(self, layers, bounds=None, clip_on=True):
        '''
        layers: a list of layers, ordered bottom to top
        bounds: [[x_min, y_min], [x_max, y_max]]  (a rectangle)
        clip_on: if True, perform clipping; else pass through and do nothing

        input paths can have any number of subpaths;
        the output paths can also have any number of subpaths, including unfilled paths

        input paths can be both filled and stroked; output paths may be only filled or stroked
        '''
        # possible optimization: check bounding boxes to see if they overlap at all
        # flatten out layers/paths into list of paths

        paths, layer_dict = self._extract_paths(layers)

        if clip_on:
            paths = self.clip(paths)

        if bounds is not None:
            # clip using the boundary
            paths = self.clipping_path_cls.from_bounds(bounds).clip_many(paths)
        return self._reconstruct_layers(paths, layer_dict, layers)

    @staticmethod
    def clip(paths):
        ''' paths are AbstractClippingPathItems '''
        i = 1 # the lowest path can't clip anything
        clipped_paths = copy(paths)
        while i < len(clipped_paths):
            if clipped_paths[i].is_filled:
                returned_paths = clipped_paths[i].clip_many(clipped_paths[:i])
                clipped_paths[:i] = returned_paths
                i = len(returned_paths)
            i += 1
        return clipped_paths

    @staticmethod
    def calculate_bounds(physical_bounds, svg_height, svg_width,
            clip_to_page=False, rotate_page=False):
        '''
        physical_bounds: [[x_min, y_min], [x_max, y_max]]  (a rectangle)

        returns bounds in the same format, considering the flags
            `clip_to_page`, `rotate_page` and the svg bounds
            (which are inflated by some small amt)
        '''
        if rotate_page:
            doc_bounds = [svg_height + 1e-9, svg_width + 1e-9]
        else:
            doc_bounds = [svg_width + 1e-9, svg_height + 1e-9]

        bounds = copy(physical_bounds)
        if clip_to_page: # clip to svg/doc bounds
            bounds[1][0] = min(doc_bounds[0], bounds[1][0]) # x maximum
            bounds[1][1] = min(doc_bounds[1], bounds[1][1]) # y maximum
        return bounds

    def check_warn_bounds(self, phy_bounds, warn_tol):
        '''
        Not implemented. Checks for certain user warnings, as described in section (3)
        here: https://gitlab.com/evil-mad/AxiDraw-Internal/-/merge_requests/54#note_712033123

        How to implement:
        offset/expand phy_bounds by warn_tol;
        use pyclipper to find difference between phy_bounds & paths;
        if any point has positive numbers, return true; else false '''

    def _extract_paths(self, layers):
        ''' given a list of layers, return a 1-D list of AbstractClippingPathItem '''
        paths = []
        layer_dict = {}
        for layer in layers:
            layer_dict[layer.item_id] = []
            layer_paths = [self.clipping_path_cls.from_path_item(path, layer.item_id)
                           for path in layer.paths]
            paths.extend(layer_paths)

        paths = filter(lambda p: p is not None, paths)

        paths = self._flatten_nonfilled_paths(paths)

        return paths, layer_dict

    @staticmethod
    def _reconstruct_layers(paths, layer_dict, layers):
        # reconstruct layers for returning to caller
        path_id_counts = {}

        for path in paths:
            if path.layer_id in layer_dict:
                if path.path_item.item_id in path_id_counts:
                    path_id_counts[path.path_item.item_id] += 1
                else:
                    path_id_counts[path.path_item.item_id] = 1

                layer_dict[path.layer_id].append(
                    path.to_path_item(path_id_counts[path.path_item.item_id]))
        for layer in layers:
            layer.paths = layer_dict[layer.item_id]

        return layers

    @staticmethod
    def _flatten_nonfilled_paths(paths):
        ''' in certain cases, flattening paths drastically decreases run time.
        Filled paths cannot be flattened without losing information about non-simply
        connected regions, but nonfilled paths can be.'''
        new_paths = []
        for path in paths:
            if path.is_filled: # cannot be flattened
                new_paths.append(path)
                continue

            if len(path.subpaths) == 1:
                new_paths.append(path)
                continue

            for subpath in path.subpaths:
                new_path = _ClippingPathItem_pyclipper.from_cpath(
                        path, [subpath], is_stroked=path.is_stroked, is_filled=False)
                new_paths.append(new_path)

        return new_paths

class AbstractClippingPathItem(ABC):
    ''' subclass this for use with ClipPathsProcess '''

    @abstractmethod
    def clip_many(self, clippees):
        ''' This is the meat of the clipping.
        clip clippees using self as clipping path.
        return a list of self.__class__ '''
        raise NotImplementedError()

    # The following methods are all about converting between
    # PathItem and the AbstractClippingPathItem subclass

    @classmethod
    @abstractmethod
    def from_path_item(cls, path_item, layer_id):
        ''' return an object of this class converted from a PathItem '''
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def from_bounds(cls, bounds):
        ''' return an object of this class converted from the bounds of the drawing space
        bounds = [[x_min, y_min], [x_max, y_max]]  (a rectangle)'''
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def to_path_item(self):
        ''' return an equivalent PathItem object; all PathItem.item_id should be unique '''
        raise NotImplementedError()

class _ClippingPathItem_pyclipper(AbstractClippingPathItem):
    ''' An implementation of AbstractClippingPathItem for use with pyclipper '''
    fill_rule_map = {
        None: pyclipper.PFT_NONZERO, # default
        FillRule.NONZERO: pyclipper.PFT_NONZERO,
        "nonzero": pyclipper.PFT_NONZERO,
        FillRule.EVENODD: pyclipper.PFT_EVENODD,
        "evenodd": pyclipper.PFT_EVENODD,
    }

    def __init__(self, path_item, layer_id, subpaths, is_stroked, is_filled, **kwargs):
        '''Do not use this constructor directly.
        Use the cls.from_* methods'''
        self.path_item = path_item
        self.layer_id = layer_id
        self.subpaths = subpaths
        self.is_stroked = is_stroked
        self.is_filled = is_filled

        self.clip_op = kwargs.pop('clip_op', pyclipper.CT_DIFFERENCE)

        fill_rule = kwargs.pop('fill_rule', pyclipper.PFT_NONZERO)
        if self.is_filled:
            self.fill_rule = fill_rule

        self.adjust_horizontal_segments()

        assert len(kwargs.keys()) == 0

    def adjust_horizontal_segments(self):
        ''' We've encountered a couple of very odd bugs, where clipper/pyclipper doesn't
        handle horizontal line segments very well. '''
        # naive implementation
        X = 0
        Y = 1

        epsilon = 1
        for subpath in self.subpaths:
            i = 1
            while i < len(subpath):
                if subpath[i][Y] == subpath[i - 1][Y]: # y coordinates of this and prev point are equal
                    subpath[i] = (subpath[i][X], subpath[i][Y] + epsilon) # bump the y coordinate a tiny bit
                    epsilon *= -1 # flip the sign of epsilon so inaccuracy doesn't propagate
                i += 1

    @classmethod
    def from_path_item(cls, path_item, layer_id):
        ''' path_item = an item of class PathItem. '''
        assert layer_id is not False
        fill_rule = cls.fill_rule_map[path_item.fill_rule] if path_item.fill else None

        try:
            subpaths = pyclipper.scale_to_clipper(path_item.subpaths)
        except OverflowError:
            logger.warning("(warning) A path was too large to compute. Path was not printed.")
            return None

        is_filled = str(path_item.fill).lower() != "none"

        return cls(
            path_item, layer_id, subpaths,
            is_filled=is_filled, is_stroked=path_item.has_stroke(),
            fill_rule=fill_rule)

    @classmethod
    def from_cpath(cls, cpath, subpaths, is_stroked, is_filled):
        ''' create a new ClippingPathItem_pyclipper based on
        another ClippingPathItem_pyclipper (param `cpath`) '''
        return cls(
            copy(cpath.path_item), cpath.layer_id, subpaths,
            is_stroked, is_filled)

    @classmethod
    def from_bounds(cls, bounds):
        ''' bounds = [[x_min, y_min], [x_max, y_max]]  (a rectangle)'''
        (x_min, y_min), (x_max, y_max) = bounds

        def rectangle_path(x_min, y_min, x_max, y_max):
            return [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max), (x_min, y_min)]

        bounds = rectangle_path(x_min, y_min, x_max, y_max)
        subpaths = [pyclipper.scale_to_clipper(bounds)]
        return cls(
            path_item="bounds", layer_id=False, subpaths=subpaths,
            is_stroked=False, is_filled=True,
            clip_op=pyclipper.CT_INTERSECTION)

    def to_path_item(self, item_id_count=1):
        ''' return an equivalent PathItem object '''
        if self.layer_id is False:
            return None
        path_item = copy(self.path_item)
        path_item.subpaths = pyclipper.scale_from_clipper(self.subpaths)
        path_item.fill = self.path_item.fill if self.is_filled else None
        path_item.fill_rule = self.path_item.fill_rule if self.is_filled else None
        path_item.stroke = self.path_item.stroke if self.is_stroked else None

        # use item_id_count to generate unique item_id's
        if item_id_count == 1:
            path_item.item_id = self.path_item.item_id
        else:
            path_item.item_id = "{}_{}".format(self.path_item.item_id, item_id_count)

        return path_item

    def clip_many(self, clippees):
        ''' clip clippees using self as clipping path. return a list of paths '''
        results = []
        for clippee in clippees:
            results.extend(self.clip_filled(clippee) if clippee.is_filled else [])
            results.extend(self.clip_stroked(clippee) if clippee.is_stroked else [])

        for result in results:
            assert not(result.is_filled and result.is_stroked), result
        return results

    def clip_filled(self, clippee):
        ''' used when clippee is filled '''
        return self.clip(clippee, PathType.FILL, self._complete_the_loop)

    def clip_stroked(self, clippee):
        ''' used when clippee is stroked '''
        results = self.clip(clippee, PathType.STROKE, self._rejoin)
        return results

    def clip(self, clippee, path_type, postclip_process):
        '''
        `path_type` is PathType.FILL or PathType.STROKE
        `postclip_process` is a function that takes & returns a list of points
        '''
        assert path_type in list(PathType)
        # use a dummy fill rule if clippee is not filled
        clippee_fill_rule = clippee.fill_rule if clippee.is_filled else pyclipper.PFT_NONZERO

        results = self._use_pyclipper_to_clip(clippee, clippee_fill_rule, path_type)
        results = postclip_process(results)
        def new_(path):
            return self.__class__.from_cpath(clippee, [path],
                    path_type==PathType.STROKE, path_type==PathType.FILL)

        if len(results) == 1:
            return [ new_(results[0]) ]

        return_value = []
        for i, path in enumerate(results):
            return_value.append(new_(path))

        if len(clippee.subpaths) > 1:
            if len(results) == 0:
                return []
            return [self.__class__.from_cpath(clippee, results, path_type==PathType.STROKE, path_type==PathType.FILL)]

        return return_value

    def _use_pyclipper_to_clip(self, clippee, clippee_fill_rule, path_type):
        try:
            pclip = pyclipper.Pyclipper()

            # pyclipper requires clippers to be "closed", so we use
            # closed=True, even for open, filled paths
            pclip.AddPaths(self.subpaths, pyclipper.PT_CLIP, closed=True)
            pclip.AddPaths(clippee.subpaths, pyclipper.PT_SUBJECT,
                           closed=(path_type==PathType.FILL))

            results = pclip.Execute2(self.clip_op, clippee_fill_rule, self.fill_rule)
            results = pyclipper.PolyTreeToPaths(results)
            return results
        except pyclipper._pyclipper.ClipperException as ce:
            length_zero = True
            for subpath in clippee.subpaths:
                for point in subpath[1:]:
                    if point != subpath[1]:
                        length_zero = False
                        break
            # pyclipper does not handle paths of length zero
            if not length_zero:
                logger.warning("(warning) Clipping process failed for some paths. Skipping those paths.")
            return [sp for sp in clippee.subpaths]


    @staticmethod
    def _complete_the_loop(paths):
        ''' pyclipper returns the closed paths without the last point,
        (which is the same as the first point), but PathItem explicitly states the last point '''
        paths = [pyclipper.CleanPolygon(path) if len(path) > 2 else path for path in paths]
        return [ path + copy(path[:1]) for path in paths ]

    @staticmethod
    def _rejoin(paths):
        ''' if the ends of the paths share a coordinate, mash them together into one path.
        Returns a list. Only for open paths.

        prime candidate for factoring out
        '''
        def join_2(path_a, path_b):
            nonlocal joined
            joined = True
            return path_a + path_b[1:] # so we don't have the same coordinate twice in a row

        def almost_equal(a, b):
            # due to horizontal adjusting, Y coordinates may be off by one
            X, Y = 0, 1
            if a[X] != b[X]:
                return False

            if abs(a[Y] - b[Y]) > 1:
                return False

            return True

        i = 0
        while i < len(paths):
            j = i + 1
            while j < len(paths):
                joined = False
                if almost_equal(paths[i][0], paths[j][0]):
                    paths[i].reverse()
                    paths[i] = join_2(paths[i], paths[j])
                elif almost_equal(paths[i][0], paths[j][-1]):
                    paths[i] = join_2(paths[j], paths[i])
                elif almost_equal(paths[i][-1], paths[j][0]):
                    paths[i] = join_2(paths[i], paths[j])
                elif almost_equal(paths[i][-1], paths[j][-1]):
                    paths[j].reverse()
                    paths[i] = join_2(paths[i], paths[j])

                if joined:
                    paths.pop(j)
                else:
                    j += 1
            i += 1
        return paths

    def __repr__(self):
        template = ("\n{}(\n path_item={},\n layer_id={},\n is_filled={},\n is_stroked={},\n " +
                    "subpaths={})")
        return template.format(type(self).__name__, repr(self.path_item), self.layer_id,
                               self.is_filled, self.is_stroked, self.subpaths)

    def __str__(self):
        source = self.path_item.item_id if hasattr(self.path_item, "item_id") else self.path_item
        template = ("{}:\n  source: {}\n  layer_id: {}\n  is_stroked: {}\n  " +
                    "is_filled: {}\n  subpaths: {}")
        return template.format(type(self).__name__, source, self.layer_id,
                               self.is_stroked, self.is_filled, self.subpaths)

class PathType(Enum):
    FILL = "fill"
    STROKE = "stroke"
