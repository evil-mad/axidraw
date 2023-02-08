from mock import patch
import sys

from pyfakefs.fake_filesystem import PatchMode
from pyfakefs.fake_filesystem_unittest import TestCase

from axidrawinternal import axidraw

from axicli import axidraw_cli

# python -m unittest discover in top-level package dir

class AxiDrawCliTestCase(TestCase):

    def setUp(self):
        self.setUpPyfakefs(patch_open_code=PatchMode.AUTO)
        self.fs.add_real_file('./test/assets/AxiDraw_trivial.svg', target_path='AxiDraw_trivial.svg')

        sys.argv = ['axicli', 'AxiDraw_trivial.svg', '--preview']

    def test_cli_options(self):
        """ Options set via the command line override options set in the default config file """
        adc = axidraw_cli.axidraw_CLI(dev=True)

        self.assertTrue(adc.options.preview) # overridden by the command line (see sys.argv)
        self.assertIn("speed_pendown", adc.options.__dict__) # from the standard conf

    def test_cli_custom_conf_options(self):
        """ cli arguments override custom configs override default configs """
        self._setup_confpy( """
servo_timeout = 'willnotbeoverridden'
preview = False """)

        adc = axidraw_cli.axidraw_CLI(dev=True)

        self.assertTrue(adc.options.preview) # overridden by the command line (see sys.argv)
        self.assertEqual(adc.params.servo_timeout, "willnotbeoverridden")

    @patch.object(axidraw, "AxiDraw")
    def test_noncli_conf_options(self, m_axidraw):
        """ Some values used by axidraw are configurable but not settable via command line. `axidraw` grabs those values directly from the configurations, i.e. without an intermediary `options` object. (see https://gitlab.com/evil-mad/AxiDraw-Internal/-/blob/7e9e27434b3a4356e34ec7dc8858a1c5881fbbc9/axidrawinternal/axidraw.py#L203). Such values that are configured via the custom config (using the `--config` command line option) need to be properly sent to the AxiDraw class and override configured values in the default config file. """
        # set up axidraw mock
        attrs = {'plot_status.stopped': 0}
        m_axidraw().configure_mock(**attrs)

        # test with config
        confpy_name = self._setup_confpy("""
speed_lim_xy_lr = 'testvalue'""")
        adc = axidraw_cli.axidraw_CLI(dev=True)

        for call in m_axidraw.call_args_list:
            if 'params' in call.kwargs:
                self.assertTrue(hasattr(call.kwargs['params'], 'speed_lim_xy_lr'))
                self.assertEqual(call.kwargs['params'].speed_lim_xy_lr, 'testvalue')
                self.assertTrue(hasattr(call.kwargs['params'], 'curve_tolerance'), "the config 'module' must contain attributes that are in the default config but not the custom config")

                return

        self.fail("The AxiDraw class must have been instantiated at least once with a params parameter. That params must have `speed_lim_xy_lr` and `speed_lim_xy_lr` must equal 'testvalue'")

    def _setup_confpy(self, confpy_contents, confpy_name = "custom_conf.py"):
        self.fs.create_file(confpy_name, contents = confpy_contents)
        sys.argv.extend(['--config', confpy_name])
        return confpy_name
