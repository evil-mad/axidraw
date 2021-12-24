import sys
import time
import math
import re
import xml.etree.ElementTree

sys.path.append('inkscape driver')
import plot_optimizations

xml.etree.ElementTree.register_namespace('', "http://www.w3.org/2000/svg")

class Path:
    start: tuple[float]
    end: tuple[float]
    
    def __init__(self, start, end):
        self.start, self.end = start, end
    
    def first_point(self):
        return self.start
    
    def last_point(self):
        return self.end
    
    def reverse(self):
        self.start, self.end = self.end, self.start

class Layer:
    paths: list[Path]

    def __init__(self, paths):
        self.paths = paths
    
    def penup_distance(self):
        return sum([
            math.hypot(p2.start[0] - p1.end[0], p2.start[1] - p1.end[1])
            for (p1, p2) in zip(self.paths, self.paths[1:])
        ])

class Digest:
    layers: list[Layer]
    def __init__(self, layer):
        self.layers = [layer]
    
layer1 = Layer([
    Path((0, 0), (0, 1)),
    Path((0, 2), (0, 3)),
])
start, raw_distance1 = time.time(), layer1.penup_distance()
plot_optimizations.reorder(Digest(layer1), False)
print(f'1. Done in {time.time() - start:.3f}sec, from {raw_distance1:.1f} to {layer1.penup_distance():.1f}')
assert layer1.penup_distance() <= raw_distance1
assert layer1.penup_distance() == 1.0
    
layer2 = Layer([
    Path((0, 2), (0, 3)),
    Path((0, 0), (0, 1)),
])
start, raw_distance2 = time.time(), layer2.penup_distance()
plot_optimizations.reorder(Digest(layer2), False)
print(f'2. Done in {time.time() - start:.3f}sec, from {raw_distance2:.1f} to {layer2.penup_distance():.1f}')
assert layer2.penup_distance() <= raw_distance2
assert layer2.penup_distance() == 1.0
    
layer3 = Layer([
    Path((0, 0), (0, 1)),
    Path((0, 3), (0, 2)),
])

start, raw_distance3 = time.time(), layer3.penup_distance()
plot_optimizations.reorder(Digest(layer3), False)
print(f'3a. Done in {time.time() - start:.3f}sec, from {raw_distance3:.1f} to {layer3.penup_distance():.1f}')
assert layer3.penup_distance() <= raw_distance3
assert layer3.penup_distance() == 2.0

start = time.time()
plot_optimizations.reorder(Digest(layer3), True)
print(f'3b. Done in {time.time() - start:.3f}sec, from {raw_distance3:.1f} to {layer3.penup_distance():.1f}')
assert layer3.penup_distance() <= raw_distance3
assert layer3.penup_distance() == 1.0
    
layer4 = Layer([
    Path((0, 3), (0, 2)),
    Path((0, 0), (0, 1)),
])

start, raw_distance4 = time.time(), layer4.penup_distance()
plot_optimizations.reorder(Digest(layer4), True)
print(f'4. Done in {time.time() - start:.3f}sec, from {raw_distance4:.1f} to {layer4.penup_distance():.1f}')
assert layer4.penup_distance() <= raw_distance4
assert layer4.penup_distance() == 1.0

def get_svg_layer(path):
    '''
    '''
    path_pattern = re.compile(r'''
        ^M\ (?P<x1>-?\d+(\.\d+)?)\ (?P<y1>-?\d+(\.\d+)?)
        \ .+\ 
        L\ (?P<x2>-?\d+(\.\d+)?)\ (?P<y2>-?\d+(\.\d+)?)
        \ *$
    ''', re.VERBOSE)
    tree = xml.etree.ElementTree.parse(path)
    return Layer([
        Path(
            (float(match.group('x1')), float(match.group('y1'))),
            (float(match.group('x2')), float(match.group('y2'))),
        )
        for match in [
            path_pattern.match(el.attrib['d'])
            for el in tree.iter()
            if el.tag.endswith('}path')
        ]
        if match
    ])

layer5 = get_svg_layer('stroke-10-slateblue.svg')
start, raw_distance5 = time.time(), layer5.penup_distance()
plot_optimizations.reorder(Digest(layer5), False)
print(f'5. Done in {time.time() - start:.3f}sec, from {raw_distance5:.1f} to {layer5.penup_distance():.1f}')
assert layer5.penup_distance() <= raw_distance5
assert layer5.penup_distance() == 0., 'Should see zero distance for single path'

layer6 = get_svg_layer('stroke-11-navy.svg')

start, raw_distance6 = time.time(), layer6.penup_distance()
plot_optimizations.reorder(Digest(layer6), False)
print(f'6a. Done in {time.time() - start:.3f}sec, from {raw_distance6:.1f} to {layer6.penup_distance():.1f}')
assert layer6.penup_distance() <= raw_distance6
assert 1008 < layer6.penup_distance() < 1397

start = time.time()
plot_optimizations.reorder(Digest(layer6), True)
print(f'6b. Done in {time.time() - start:.3f}sec, from {raw_distance6:.1f} to {layer6.penup_distance():.1f}')
assert layer6.penup_distance() <= raw_distance6
assert 1017 < layer6.penup_distance() < 1280

layer7 = get_svg_layer('stroke-8-mediumblue.svg')

start, raw_distance7 = time.time(), layer7.penup_distance()
plot_optimizations.reorder(Digest(layer7), False)
print(f'7a. Done in {time.time() - start:.3f}sec, from {raw_distance7:.1f} to {layer7.penup_distance():.1f}')
assert layer7.penup_distance() <= raw_distance7
assert 28586 < layer7.penup_distance() < 163402

start = time.time()
plot_optimizations.reorder(Digest(layer7), True)
print(f'7b. Done in {time.time() - start:.3f}sec, from {raw_distance7:.1f} to {layer7.penup_distance():.1f}')
assert layer7.penup_distance() <= raw_distance7
assert 12436 < layer7.penup_distance() < 166320
