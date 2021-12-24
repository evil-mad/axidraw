import sys
import time
import math

sys.path.append('inkscape driver')
import plot_optimizations

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
    Path((0, 2), (0, 3)),
    Path((0, 0), (0, 1)),
])
start = time.time()
plot_optimizations.reorder(Digest(layer1), False)
print(f'1. Done in {time.time() - start:.3f}sec')
assert layer1.penup_distance() == 1.0
    
layer2 = Layer([
    Path((0, 0), (0, 1)),
    Path((0, 2), (0, 3)),
])
start = time.time()
plot_optimizations.reorder(Digest(layer2), False)
print(f'2. Done in {time.time() - start:.3f}sec')
assert layer2.penup_distance() == 1.0
    
layer3 = Layer([
    Path((0, 0), (0, 1)),
    Path((0, 3), (0, 2)),
])

start = time.time()
plot_optimizations.reorder(Digest(layer3), False)
print(f'3a. Done in {time.time() - start:.3f}sec')
assert layer3.penup_distance() == 2.0

start = time.time()
plot_optimizations.reorder(Digest(layer3), True)
print(f'3b. Done in {time.time() - start:.3f}sec')
assert layer3.penup_distance() == 1.0
