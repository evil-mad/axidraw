import copy
import errno
import os
import runpy
import sys
import warnings

from lxml import etree

OPTION_NAMES = ['mode', 'speed_pendown', 'speed_penup', 'accel', 'pen_pos_down', 'pen_pos_up',
                    'pen_rate_lower', 'pen_rate_raise', 'pen_delay_down', 'pen_delay_up',
                    'random_start', 'hiding', 'reordering', 'no_rotate', 'const_speed',
                    'report_time','manual_cmd', 'dist', 'layer', 'copies', 'page_delay',
                    'preview', 'rendering', 'model', 'penlift', 'port', 'port_config', 'webhook',
                    'webhook_url', 'digest', 'progress']

def handle_info_cases(no_flag_arg, quick_help, cli_version, software_name = None, version = None):
    ''' handles the simple cases like "version" and "help" '''

    if no_flag_arg == "help":
        print(cli_version)
        print(quick_help)
        sys.exit()

    if no_flag_arg == "version":
        print(cli_version)
        sw_string = "Software "
        if software_name:
            sw_string = software_name + " " + sw_string
        if version is not None:
            print (sw_string + version)
        sys.exit()

def check_for_input(input_file, bad_input_message):
    ''' Check for the required input file, quit if not there.
    `None` is an acceptable value because `None` denotes stdin.'''
    bad_filename = input_file is not None and not os.path.isfile(input_file)
    interactive = input_file is None and sys.stdin.isatty()

    if bad_filename or interactive:
        print(bad_input_message)
        sys.exit(1)

def effect_parse(effect, svg_input):
    ''' `effect` is an `inkex.Effect` object, e.g. `AxiDrawControl`
    if `svg_input` is None`, it uses stdin '''
    # hack so inkex handles stdin properly
    # https://github.com/evil-mad/ink_extensions/blob/6a246a5c530491302e155b4d1965e989381438e6/ink_extensions/inkex.py#L194
    effect.svg_file = None
    effect.parse(svg_input)

def output_result(output_file, result, always_output=False):
    ''' if an output file is specified, write to it.
    If an output file is not specified and `always_output` is True, print to stdout'''
    if output_file:
        with open(output_file, 'w') as out: # Open output file for writing
            out.write(result)
    elif always_output:
        sys.stdout.write(result)

def has_output(effect):
    """ True if the effect successfully ran and produced a different document; False otherwise. Based on the `output` function in ink_extensions.inkex.Effect """
    original = etree.tostring(effect.original_document)
    result = etree.tostring(effect.document)
    return original != result


# CONFIGURATION UTILS

def load_configs(config_list):
    ''' config_list is in order of priority, either file names or module names '''

    config_dict = {}

    rev_list = copy.copy(config_list)
    rev_list.reverse() # load in opposite order of priority
    for config in rev_list:
        config_dict.update(load_config(config))

    return config_dict


def load_config(config):
    if config is None:
        return {}

    config_dict = None
    try: # try assuming config is a filename
        config_dict = runpy.run_path(config)
    except SyntaxError as se:
        print('Config file {} contains a syntax error on line {}:'.format(se.filename, se.lineno))
        print('    {}'.format(se.text))
        print('The config file should be a python file (e.g., a file that ends in ".py").')
        sys.exit(1)
    except OSError as ose:
        if len(config) > 3 and config[-3:] == ".py" and ose.errno == errno.ENOENT:
            # if config is a filename ending in ".py" but it doesn't appear to exist
            print("Could not find any file named {}.".format(config))
            print("Check the spelling and/or location.")
            sys.exit(1)
        else:
            # Either config is a config file that doesn't have a .py AND it doesn't exist
            # or config is a module
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                # since technically this is importing "axidrawinternal.axidraw_conf" twice, it would generate a warning, but we can ignore it
                try: # assume config is a module
                    config_dict = runpy.run_module(config)
                except ImportError as ie: # oops, no module named that
                    # config may be a config file that doesn't have a .py AND doesn't exist
                    print("Could not find any file or module named {}.".format(config))
                    sys.exit(1)

    return { key: value for key, value in config_dict.items() if key[0] != "_" }

def assign_option_values(options_obj, command_line, configs, option_names):
    """ `configs` is a list of dicts containing values for the options, in order of priority.
    See get_configured_value.
    `command_line` is the return value of argparse.ArgumentParser.parse_args() or similar
    `options_obj` is the object that will be populated with the final option values.
    """

    for name in option_names:
        # argparse.ArgumentParser.parse_args
        # assigns None to any options that were
        # not defined by the user, so command line arguments are handled differently from
        # configured values (which might be correctly assigned None)
        command_line_value = getattr(command_line, name, None)
        if command_line_value is not None:
            setattr(options_obj, name, command_line_value)
        else:
            setattr(options_obj, name, get_configured_value(name, configs + [options_obj.__dict__]))

def get_configured_value(attr, configs):
    """ configs is a list of configuration dicts, in order of priority.

    e.g. if configs is a list [user_config, other_config], then the default for
    "speed_pendown" will be user_config.speed_pendown if user_config.speed_pendown exists,
    and if not, the default will be other_config.speed_pendown.
    """
    for config in configs:
        if attr in config:
            return config[attr]
    raise ValueError("The given attr ({}) was not found in any of the configurations.".format(attr))

class FakeConfigModule:
    ''' just turns a dict into an object
    so attributes can be set/retrieved object-style '''
    def __init__(self, a_dict):
        self.__dict__ = a_dict
