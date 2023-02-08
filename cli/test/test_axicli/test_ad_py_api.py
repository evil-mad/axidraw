from distutils.version import StrictVersion
import logging
import time
import unittest

from mock import ANY, MagicMock, patch

from pyaxidraw import axidraw

testfile = "test/assets/AxiDraw_trivial.svg"

# from plotink.plot_utils_import import from_dependency_import # plotink
# inkex = from_dependency_import('ink_extensions.inkex')

# python -m unittest discover in top-level package dir

# @patch.object(axidraw.message, "emit")

class AxiDrawPythonAPITestCase(unittest.TestCase):

    def test_import(self):
        print("test pyaxidraw import and params")
        ad = axidraw.AxiDraw()
        ad.params.check_updates = False
        self.assertEqual(ad.params.servo_timeout, 60000)

    def test_plot_setup(self):
        print("test plot_setup")
        ad = axidraw.AxiDraw()
        ad.original_document = None
        ad.original_document = None
        ad.plot_setup()

        self.assertIsNotNone(ad.document)
        self.assertIsNotNone(ad.original_document)
        self.assertNotEqual(ad.document, ad.original_document) # different objects

    @patch.object(axidraw.AxiDraw, "get_output")
    @patch.object(axidraw.AxiDraw, "effect")
    def test_plot_run(self, m_effect, m_get_output):
        print("test plot_run")

        ad = self._setup_axidraw_with_args()
        ad = axidraw.AxiDraw()
        ad.document = MagicMock()

        ad.plot_run()

        m_effect.assert_called_once()
        self.assertFalse(m_get_output.called)

    @patch.object(axidraw.AxiDraw, "get_output")
    @patch.object(axidraw.AxiDraw, "effect")
    def test_plot_run(self, m_effect, m_get_output):
        print("test plot_run check output")
        ad = self._setup_axidraw_with_args()
        ad.document = MagicMock()
        ad.plot_setup()

        ad.plot_run(output=True)

        m_effect.assert_called_once()
        m_get_output.assert_called_once()


    def _setup_axidraw_with_args(self, args=None, m_emit=None):
        ''' returns an AxiDraw '''
        ad = axidraw.AxiDraw() if m_emit is None else axidraw.AxiDraw(user_message_fun=m_emit)
        return ad
