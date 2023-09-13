'''
axicli - Command Line Interface (CLI) for AxiDraw.

For quick help:
    axicli --help

Full user guide:
    https://axidraw.com/doc/cli_api/


This script is a stand-alone version of AxiDraw Control, accepting
various options and providing a facility for setting default values.

'''


'''
About this software:

The AxiDraw writing and drawing machine is a product of Evil Mad Scientist
Laboratories. https://axidraw.com   https://shop.evilmadscientist.com

This open source software is written and maintained by Evil Mad Scientist
to support AxiDraw users across a wide range of applications. Please help
support Evil Mad Scientist and open source software development by purchasing
genuine AxiDraw hardware.

AxiDraw software development is hosted at https://github.com/evil-mad/axidraw

Additional AxiDraw documentation is available at http://axidraw.com/docs

AxiDraw owners may request technical support for this software through our
github issues page, support forums, or by contacting us directly at:
https://shop.evilmadscientist.com/contact



Copyright 2023 Windell H. Oskay, Evil Mad Scientist Laboratories

The MIT License (MIT)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''

import argparse
import copy
import sys
from lxml import etree
from pyaxidraw.axidraw_options import common_options

from axicli import utils

from plotink.plot_utils_import import from_dependency_import # plotink
exit_status = from_dependency_import("ink_extensions_utils.exit_status")

cli_version = "AxiDraw Command Line Interface 3.9.4"

quick_help = '''
    Basic syntax to plot a file:      axicli svg_in [OPTIONS]

    For a quick list of options, use: axicli --help

    To display current version, use:  axicli --version

    For full user guide, please see: https://axidraw.com/doc/cli_api/

    (c) 2023 Evil Mad Scientist Laboratories
        '''

def axidraw_CLI(dev = False):
    ''' The core of axicli '''

    desc = 'AxiDraw Command Line Interface.'

    parser = argparse.ArgumentParser(description=desc, usage=quick_help)

    parser.add_argument("svg_in", nargs='?', \
            help="The SVG file to be plotted")

    parser.add_argument("-f", "--config", type=str, dest="config",
                        help="Filename for the custom configuration file.")

    parser.add_argument("-m","--mode", \
             metavar='MODENAME', type=str, \
             help="Mode. One of: [plot, layers, align, toggle, cycle, manual, " \
             + "sysinfo, version, res_plot, res_home, reorder (deprecated)]. Default: plot.")

    parser.add_argument("-s","--speed_pendown", \
            metavar='SPEED',  type=int, \
            help="Maximum plotting speed, when pen is down (1-100)")

    parser.add_argument("-S","--speed_penup", \
            metavar='SPEED', type=int, \
            help="Maximum transit speed, when pen is up (1-100)")

    parser.add_argument("-a","--accel", \
            metavar='RATE', type=int, \
            help="Acceleration rate factor (1-100)")

    parser.add_argument("-d","--pen_pos_down", \
            metavar='HEIGHT', type=int, \
            help="Height of pen when lowered (0-100)")

    parser.add_argument("-u","--pen_pos_up", \
            metavar='HEIGHT', type=int,  \
            help="Height of pen when raised (0-100)")

    parser.add_argument("-r","--pen_rate_lower", \
            metavar='RATE', type=int, \
            help="Rate of lowering pen (1-100)")

    parser.add_argument("-R","--pen_rate_raise", \
            metavar='RATE', type=int, \
            help="Rate of raising pen (1-100)")

    parser.add_argument("-z","--pen_delay_down", \
            metavar='DELAY',type=int, \
            help="Optional delay after pen is lowered (ms)")

    parser.add_argument("-Z","--pen_delay_up", \
            metavar='DELAY',type=int, \
            help="Optional delay after pen is raised (ms)")

    parser.add_argument("-N","--no_rotate", \
            action="store_const", const='True', \
            help="Disable auto-rotate; preserve plot orientation")

    parser.add_argument("-C","--const_speed",\
            action="store_const", const='True', \
            help="Use constant velocity when pen is down")

    parser.add_argument("-T","--report_time", \
            action="store_const", const='True', \
            help="Report time elapsed")

    parser.add_argument("-M","--manual_cmd", \
            metavar='COMMAND', type=str, \
            help="Manual command. One of: [fw_version, lower_pen, raise_pen, "\
            + "walk_x, walk_y, walk_mmx, walk_mmy, walk_home, enable_xy, disable_xy, "\
            + "res_read, res_adj_in, res_adj_mm, bootload, strip_data, read_name, "\
            + "list_names,  write_name]. Default: fw_version")

    parser.add_argument("-w","--dist","--walk_dist", \
            metavar='DISTANCE', type=float, \
            help="Distance for manual walk or changing resume position. "\
            + "(The argument name walk_dist is deprecated.)")

    parser.add_argument("-l","--layer", \
            type=int, \
            help="Layer(s) selected for layers mode (1-1000). Default: 1")

    parser.add_argument("-c","--copies", \
            metavar='COUNT', type=int, \
            help="Copies to plot, or 0 for continuous plotting. Default: 1")

    parser.add_argument("-D","--page_delay", \
             metavar='DELAY', type=int,\
             help="Optional delay between copies (s).")

    parser.add_argument("-v","--preview", \
            action="store_const",  const='True', \
            help="Preview mode; simulate plotting only.")

    parser.add_argument("-g","--rendering", \
            metavar='RENDERCODE', type=int, \
            help="Preview mode rendering option (0-3). 0: None. " \
            + "1: Pen-down movement. 2: Pen-up movement. 3: All movement.")

    parser.add_argument("-G","--reordering", \
            metavar='VALUE', type=int, \
            help="SVG reordering option (0-4; 3 deprecated)."\
            + " 0: Least; Only connect adjoining paths."\
            + " 1: Basic; Also reorder paths for speed."\
            + " 2: Full; Also allow path reversal."\
            + " 4: None; Strictly preserve file order.")

    parser.add_argument("-Y","--random_start", \
            action="store_const", const='True', \
            help="Randomize start position of closed paths.")

    parser.add_argument("-H","--hiding", \
            action="store_const", const='True', \
            help="Enable hidden-line removal")

    parser.add_argument("-L","--model",\
            metavar='MODELCODE', type=int,\
            help="AxiDraw Model (1-7). 1: AxiDraw V2, V3, or SE/A4. " \
            + "2: AxiDraw V3/A3 or SE/A3. 3: AxiDraw V3 XLX. " \
            + "4: AxiDraw MiniKit. 5:AxiDraw SE/A1. 6: AxiDraw SE/A2. " \
            + "7: AxiDraw V3/B6." )

    parser.add_argument("-q","--penlift",\
            metavar='LIFTCODE', type=int,\
            help="Pen lift servo configuration (1-3). " \
            + "1: Default for AxiDraw model. " \
            + "2: Standard servo (lowest connector position). " \
            + "3: Narrow-band brushless servo (3rd position up)." )

    parser.add_argument("-p","--port",\
            metavar='PORTNAME', type=str,\
            help="Serial port or named AxiDraw to use")

    parser.add_argument("-P","--port_config",\
            metavar='PORTCODE', type=int,\
            help="Port use code (0-3)."\
            + " 0: Plot to first unit found, unless port is specified"\
            + " 1: Plot to first AxiDraw Found."\
            + " 2: Plot to specified AxiDraw."\
            + " 3: Plot to all AxiDraw units.")

    parser.add_argument("-o","--output_file",\
            metavar='FILE', \
            help="Optional SVG output file name")

    parser.add_argument("-O","--digest",\
            metavar='VALUE', type=int,\
            help="Plot digest output option (0-2)."\
            + " 0: No change to behavior or output (Default)."\
            + " 1: Output 'plob' digest, not full SVG, when saving file."\
            + " 2: Disable plots and previews; generate digest only.")

    parser.add_argument("-W","--webhook", \
            action="store_const",  const='True', \
            help='Enable webhook alerts')

    parser.add_argument("-U","--webhook_url",\
            metavar='URL', type=str,\
            help="URL for webhook alerts")

    parser.add_argument("--version",
            action='store_const', const='True',
            help="Output the version of axicli")

    parser.add_argument("-b","--progress", \
            action="store_const",  const='True', \
            help='Enable CLI progress bar while plotting')

    args = parser.parse_args()

    # Handle trivial cases
    from pyaxidraw import axidraw
    ad = axidraw.AxiDraw()

    info_mode = "version" if args.version else args.svg_in
    utils.handle_info_cases(info_mode, quick_help, cli_version, "AxiDraw", ad.version_string)

    if args.mode == "options":
        quit()

    # Detect certain "trivial" cases that do not require an input file
    use_trivial_file = False
    if args.mode in ("align", "toggle", "cycle", "version", "sysinfo"):
        use_trivial_file = True
    if args.mode == "manual" and args.manual_cmd not in\
            ("strip_data", "res_read","res_adj_in", "res_adj_mm"):
        use_trivial_file = True

    svg_input = args.svg_in

    if not use_trivial_file or args.output_file:
        utils.check_for_input(svg_input,
            """usage: axicli svg_in [OPTIONS]
    Input file required but not found.
    For help, use: axicli --help""")


    if args.mode == "reorder":
        from pyaxidraw import axidraw_svg_reorder

        adc = axidraw_svg_reorder.ReorderEffect()

        adc.getoptions([])
        utils.effect_parse(adc, svg_input)

        if args.reordering is not None:
            adc.options.reordering = args.reordering

        if args.progress is not None:
            # Pass through to AxiDraw Control; this option is CLI specific.
            adc.options.progress = args.progress

        print("Re-ordering SVG File.")
        print("This can take a while for large files.")
        print("(Warning: Reorder mode is deprecated and will be removed in a future version.)")

        exit_status.run(adc.effect)    # Sort the document

        if args.output_file:
            writeFile = open(args.output_file,'w')         # Open output file for writing.
            writeFile.write(adc.get_output())
            writeFile.close()
        print("Done")

        quit()

    # For nontrivial cases, import the axidraw module and go from there:

    # THIS SECTION: SLATED FOR REMOVAL IN AXIDRAW SOFTWARE 4.0
    # Backwards compatibility for custom configuration files including `walk_dist`,
    #   the deprecated predecessor to `dist`
    #
    # If a custom config file specifies walk_dist (deprecated version of dist),
    #   that overrides the value in the default config file.
    # If a custom config file specifies dist, that overrides both:
    config_dict = utils.load_configs([args.config])         # Remove in v 4.0
    new_dist = config_dict.get('dist')                      # Remove in v 4.0
    new_walk_dist = config_dict.get('walk_dist')            # Remove in v 4.0

    config_dict = utils.load_configs([args.config, 'axidrawinternal.axidraw_conf'])

    if new_walk_dist is not None:                           # Remove in v 4.0
        config_dict['dist'] = new_walk_dist                 # Remove in v 4.0
    if new_dist is not None:                                # Remove in v 4.0
        config_dict['dist'] = new_dist                      # Remove in v 4.0

    combined_config = utils.FakeConfigModule(config_dict)

    from pyaxidraw import axidraw_control

    adc = axidraw_control.AxiDrawWrapperClass(params = combined_config)

    adc.getoptions([])

    if use_trivial_file:
        trivial_svg = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <svg
               xmlns:dc="http://purl.org/dc/elements/1.1/"
               xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
               xmlns:svg="http://www.w3.org/2000/svg"
               xmlns="http://www.w3.org/2000/svg"
               version="1.1"
               id="svg15158"
               viewBox="0 0 297 210"
               height="210mm"
               width="297mm">
            </svg>
            """
        svg_string = trivial_svg.encode('utf-8') # Need consistent encoding.
        p = etree.XMLParser(huge_tree=True, encoding='utf-8')
        adc.document = etree.ElementTree(etree.fromstring(svg_string, parser=p))
        adc.original_document = copy.deepcopy(adc.document)
    else:
        utils.effect_parse(adc, svg_input)

    # assign command line options to adc's options.
    # additionally, look inside the config to see if any command line options were set there
    option_names = utils.OPTION_NAMES
    utils.assign_option_values(adc.options, args, [config_dict], option_names)

    adc.cli_api = True # Set flag that this is being called from the CLI.

    exit_status.run(adc.effect)    # Plot the document
    if utils.has_output(adc) and not use_trivial_file:
        utils.output_result(args.output_file, adc.outdoc)

    if adc.status_code >= 100: # Give non-zero exit code.
        sys.exit(1) # No need to be more verbose; we have already printed error messages.

    return adc if dev else None # returning adc is useful for tests
