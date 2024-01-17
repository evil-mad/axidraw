import unittest
import copy
import random
import argparse

from mock import patch

from axicli import utils
from axicli.utils import get_configured_value, assign_option_values, load_config

# python -m unittest discover in top-level package dir

class UtilsTestCase(unittest.TestCase):


    def test_get_configured_value_no_configs(self):
        """ If no configs are provided, raise an error """
        with self.assertRaises(BaseException):
            get_configured_value("eggs", [])

    def test_get_configured_value_one_config(self):
        """ look in the config for the correct value """
        config = { "some": "values", "blah": "blue" }

        for attr, value in config.items():
            self.assertEqual(value, get_configured_value(attr, [config]))

    def test_get_configured_value_defined_anything(self):
        """ test case: two configs, and the attr is defined in both.
        The first config should get priority """
        user_config = { "true": True, "zero": 0, "num": 100, "string": "a string" }
        standard_config = { "true": "blap", "zero": 123, "num": "???" }

        for attr, value in user_config.items():
            self.assertEqual(value, get_configured_value(attr, [user_config, standard_config]))

    def test_get_configured_value_undefined_undefined(self):
        """ if the attr is not defined in any configs, raise an error """
        user_config = { "something": 23 }
        standard_config = { "another": "blah" }

        with self.assertRaises(BaseException):
            get_configured_value("something else entirely", [user_config, standard_config])

    def test_get_configured_value_none_anything(self):
        """ if the first config defines the attr as None, return None,
        no matter what the second config says """

        user_config = { "defined": None, "undefined": None }
        standard_config = { "defined": 1 }

        for attr, value in user_config.items():
            self.assertIsNone(get_configured_value(attr, [user_config, standard_config]))

    def test_assign_option_values(self):
        """ test that command line values override configured values """

        option_names = ["not_overridden", "overridden"]
        configured_values = { "not_overridden": "configured value", "overridden": "configured value" }
        command_line_values = argparse.Namespace()
        command_line_values.not_overridden = None
        command_line_values.overridden = "commandline value"
        resulting_options = argparse.Namespace() # will contain the result of running assign_option_values

        assign_option_values(resulting_options, command_line_values, [configured_values], option_names)

        self.assertTrue(hasattr(resulting_options, "not_overridden"))
        self.assertEqual(resulting_options.not_overridden, configured_values["not_overridden"])
        self.assertTrue(hasattr(resulting_options, "overridden"))
        self.assertEqual(resulting_options.overridden, command_line_values.overridden)

    def test_load_config_bad_filename(self):
        config_filenames = ["a_nonexistent_file.py", "another_nonexistent_file"]
        for filename in config_filenames:
            with self.subTest(filename=filename):
                with self.assertRaises(SystemExit) as se:
                    load_config(filename)

                self.assertNotEqual(se.exception.args, (None, ), "program will exit with a zero exit code")
                self.assertNotEqual(se.exception.args, (), "program will exit with a zero exit code")

    @patch.object(utils.runpy, "run_path", side_effect=SyntaxError("bad syntax"))
    def test_load_config_bad_syntax(self, m_run_path):
        with self.assertRaises(SystemExit) as se:
            load_config("whatever.py")

        self.assertNotEqual(se.exception.args, (None, ), "program will exit with a zero exit code")
        self.assertNotEqual(se.exception.args, (), "program will exit with a zero exit code")

