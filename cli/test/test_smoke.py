import unittest

from pyaxidraw import axidraw_control

# python -m unittest discover -s test in top-level package dir

class SmokeTestCase(unittest.TestCase):

    def test_trivial(self):
        adc = axidraw_control.AxiDrawWrapperClass()

        adc.getoptions([])
        adc.options.preview = True # otherwise the actual plotting code is never run

        adc.parseFile('test/assets/AxiDraw_trivial.svg')

        adc.effect()
