import argparse

from ink_extensions import inkex

def core_axidraw_options(config):
    mode_options = core_mode_options(config)
    options = core_options(config)
    return argparse.ArgumentParser(add_help = False, parents = [mode_options, options])

def core_options(config):
    ''' options that are used in extensions in this library, as well as in hershey-advanced and
    potentially others '''
    options = argparse.ArgumentParser(add_help = False) # parent parser

    options.add_argument("--speed_pendown",\
                        type=int, action="store", dest="speed_pendown", \
                        default=config["speed_pendown"], \
                        help="Maximum plotting speed, when pen is down (1-100)")

    options.add_argument("--speed_penup",\
                        type=int, action="store", dest="speed_penup", \
                        default=config["speed_penup"], \
                        help="Maximum transit speed, when pen is up (1-100)")

    options.add_argument("--accel",\
                        type=int, action="store", dest="accel", \
                        default=config["accel"], \
                        help="Acceleration rate factor (1-100)")

    options.add_argument("--pen_pos_down",\
                        type=int, action="store", dest="pen_pos_down",\
                        default=config["pen_pos_down"],\
                        help="Height of pen when lowered (0-100)")

    options.add_argument("--pen_pos_up",\
                        type=int, action="store", dest="pen_pos_up", \
                        default=config["pen_pos_up"], \
                        help="Height of pen when raised (0-100)")

    options.add_argument("--pen_rate_lower",\
                        type=int, action="store", dest="pen_rate_lower",\
                        default=config["pen_rate_lower"], \
                        help="Rate of lowering pen (1-100)")

    options.add_argument("--pen_rate_raise",\
                        type=int, action="store", dest="pen_rate_raise",\
                        default=config["pen_rate_raise"],\
                        help="Rate of raising pen (1-100)")

    options.add_argument("--pen_delay_down",\
                        type=int, action="store", dest="pen_delay_down",\
                        default=config["pen_delay_down"],\
                        help="Optional delay after pen is lowered (ms)")

    options.add_argument("--pen_delay_up",\
                        type=int, action="store", dest="pen_delay_up", \
                        default=config["pen_delay_up"],\
                        help="Optional delay after pen is raised (ms)")

    options.add_argument("--no_rotate",\
                        type=inkex.boolean_option, action="store", dest="no_rotate",\
                        default=False,\
                        help="Disable auto-rotate; preserve plot orientation")

    options.add_argument("--const_speed",\
                        type=inkex.boolean_option, action="store", dest="const_speed",\
                        default=config["const_speed"],\
                        help="Use constant velocity when pen is down")

    options.add_argument("--report_time",\
                        type=inkex.boolean_option, action="store", dest="report_time",\
                        default=config["report_time"],\
                        help="Report time elapsed")

    options.add_argument("--page_delay",\
                        type=int, action="store", dest="page_delay",\
                        default=config["page_delay"],\
                        help="Optional delay between copies (s).")

    options.add_argument("--preview",\
                        type=inkex.boolean_option, action="store", dest="preview",\
                        default=config["preview"],\
                        help="Preview mode; simulate plotting only.")

    options.add_argument("--rendering",\
                        type=int, action="store", dest="rendering",\
                        default=config["rendering"],\
                        help="Preview mode rendering option (0-3). 0: None. " \
                        + "1: Pen-down movement. 2: Pen-up movement. 3: All movement.")

    options.add_argument("--model",\
                        type=int, action="store", dest="model",\
                        default=config["model"],\
                        help="AxiDraw Model (1-6). 1: AxiDraw V2 or V3. " \
                        + "2: AxiDraw V3/A3 or SE/A3. 3: AxiDraw V3 XLX. " \
                        + "4: AxiDraw MiniKit. 5: AxiDraw SE/A1. 6: AxiDraw SE/A2.")

    options.add_argument("--penlift",\
                        type=int, action="store", dest="penlift",\
                        default=config["penlift"],\
                        help="pen lift servo configuration (1-3). " \
                        + "1: Default for AxiDraw model. " \
                        + "2: Standard servo (lowest connector position). " \
                        + "3: Narrow-band brushless servo (3rd position up).")

    options.add_argument("--port_config",\
                        type=int, action="store", dest="port_config",\
                        default=config["port_config"],\
                        help="Port use code (0-3)."\
                        +" 0: Plot to first unit found, unless port is specified."\
                        + "1: Plot to first AxiDraw Found. "\
                        + "2: Plot to specified AxiDraw. "\
                        + "3: Plot to all AxiDraw units. ")

    options.add_argument("--port",\
                        type=str, action="store", dest="port",\
                        default=config["port"],\
                        help="Serial port or named AxiDraw to use")

    options.add_argument("--setup_type",\
                        type=str, action="store", dest="setup_type",\
                        default="align",\
                        help="Setup option selected (GUI Only)")

    options.add_argument("--resume_type",\
                        type=str, action="store", dest="resume_type",\
                        default="plot",
                        help="The resume option selected (GUI Only)")

    options.add_argument("--auto_rotate",\
                        type=inkex.boolean_option, action="store", dest="auto_rotate",\
                        default=config["auto_rotate"], \
                        help="Auto select portrait vs landscape orientation")

    options.add_argument("--random_start",\
                        type=inkex.boolean_option, action="store", dest="random_start",\
                        default=config["random_start"], \
                        help="Randomize start locations of closed paths")

    options.add_argument("--hiding",\
                        type=inkex.boolean_option, action="store", dest="hiding",\
                        default=config["hiding"], \
                        help="Hidden-line removal")

    options.add_argument("--reordering",\
                        type=int, action="store", dest="reordering",\
                        default=config["reordering"],\
                        help="SVG reordering option (0-4; 3 deprecated)."\
                        + " 0: Least: Only connect adjoining paths."\
                        + " 1: Basic: Also reorder paths for speed."\
                        + " 2: Full: Also allow path reversal."\
                        + " 4: None: Strictly preserve file order.")

    options.add_argument("--resolution",\
                        type=int, action="store", dest="resolution",\
                        default=config["resolution"],\
                        help="Resolution option selected")

    options.add_argument("--digest",\
                        type=int, action="store", dest="digest",\
                        default=config["digest"],\
                        help="Plot optimization option (0-2)."\
                        + "0: No change to behavior or output (Default)."\
                        + "1: Output 'plob' digest, not full SVG, when saving file. "\
                        + "2: Disable plots and previews; generate digest only. ")

    options.add_argument("--webhook",\
                        type=inkex.boolean_option, action="store", dest="webhook",\
                        default=config["webhook"],\
                        help="Enable webhook callback when a plot finishes")

    options.add_argument("--webhook_url",\
                        type=str, action="store", dest="webhook_url",\
                        default=config["webhook_url"],\
                        help="Webhook URL to be used if webhook is enabled")

    options.add_argument("--submode",\
                        action="store", type=str, dest="submode",\
                        default="none", \
                        help="Secondary GUI tab.")

    return options

def core_mode_options(config):
    ''' these are also common options, but unlike options in `core_options`, these
    are options that are more specific to this repo '''
    options = argparse.ArgumentParser(add_help = False) # parent parser

    options.add_argument("--mode",\
                        action="store", type=str, dest="mode",\
                        default=config["mode"], \
                        help="Mode or GUI tab. One of: [plot, layers, align, toggle, cycle"\
                        + ", manual, sysinfo, version, res_plot, res_home]. Default: plot.")

    options.add_argument("--manual_cmd",\
                        type=str, action="store", dest="manual_cmd",\
                        default=config["manual_cmd"],\
                        help="Manual command. One of: [fw_version, raise_pen, lower_pen, "\
                        + "walk_x, walk_y, walk_mmx, walk_mmy, walk_home, enable_xy, "\
                        + "disable_xy, res_read, res_adj_in, res_adj_mm, bootload, "\
                        + "strip_data, read_name, list_names, write_name]. Default: fw_version")

    options.add_argument("--dist", "--walk_dist",\
                        type=float, action="store", dest="dist",\
                        default=config["dist"],\
                        help="Distance for manual walk or changing resume position. "\
                            + "(The argument name walk_dist is deprecated.)")

    options.add_argument("--layer",\
                        type=int, action="store", dest="layer",\
                        default=config["default_layer"],\
                        help="Layer(s) selected for layers mode (1-1000). Default: 1")

    options.add_argument("--copies",\
                        type=int, action="store", dest="copies",\
                        default=config["copies"],\
                        help="Copies to plot, or 0 for continuous plotting. Default: 1")

    return options
