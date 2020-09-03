import runpy
import sys

from optparse import OptionGroup

def core_options(parser, config):
    options = OptionGroup(parser, "Core Options")

    options.add_option("--speed_pendown",\
                       type="int", action="store", dest="speed_pendown", \
                       default=config["speed_pendown"], \
                       help="Maximum plotting speed, when pen is down (1-100)")

    options.add_option("--speed_penup",\
                       type="int", action="store", dest="speed_penup", \
                       default=config["speed_penup"], \
                       help="Maximum transit speed, when pen is up (1-100)")
    
    options.add_option("--accel",\
                       type="int", action="store", dest="accel", \
                       default=config["accel"], \
                       help="Acceleration rate factor (1-100)")
    
    options.add_option("--pen_pos_down",\
                       type="int", action="store", dest="pen_pos_down",\
                       default=config["pen_pos_down"],\
                       help="Height of pen when lowered (0-100)")
    
    options.add_option("--pen_pos_up",\
                       type="int", action="store", dest="pen_pos_up", \
                       default=config["pen_pos_up"], \
                       help="Height of pen when raised (0-100)")
    
    options.add_option("--pen_rate_lower",\
                       type="int", action="store", dest="pen_rate_lower",\
                       default=config["pen_rate_lower"], \
                       help="Rate of lowering pen (1-100)")
    
    options.add_option("--pen_rate_raise",\
                       type="int", action="store", dest="pen_rate_raise",\
                       default=config["pen_rate_raise"],\
                       help="Rate of raising pen (1-100)")
    
    options.add_option("--pen_delay_down",\
                       type="int", action="store", dest="pen_delay_down",\
                       default=config["pen_delay_down"],\
                       help="Optional delay after pen is lowered (ms)")
    
    options.add_option("--pen_delay_up",\
                       type="int", action="store", dest="pen_delay_up", \
                       default=config["pen_delay_up"],\
                       help="Optional delay after pen is raised (ms)")
    
    options.add_option("--no_rotate",\
                       type="inkbool", action="store", dest="no_rotate",\
                       default=False,\
                       help="Disable auto-rotate; preserve plot orientation")
    
    options.add_option("--const_speed",\
                       type="inkbool", action="store", dest="const_speed",\
                       default=config["const_speed"],\
                       help="Use constant velocity when pen is down")
    
    options.add_option("--report_time",\
                       type="inkbool", action="store", dest="report_time",\
                       default=config["report_time"],\
                       help="Report time elapsed")

    options.add_option("--page_delay",\
                       type="int", action="store", dest="page_delay",\
                       default=config["page_delay"],\
                       help="Optional delay between copies (s).")
    
    options.add_option("--preview",\
                       type="inkbool", action="store", dest="preview",\
                       default=config["preview"],\
                       help="Preview mode; simulate plotting only.")

    options.add_option("--rendering",\
                       type="int", action="store", dest="rendering",\
                       default=config["rendering"],\
                       help="Preview mode rendering option (0-3). 0: None. " \
                       + "1: Pen-down movement. 2: Pen-up movement. 3: All movement.")
    
    options.add_option("--model",\
                       type="int", action="store", dest="model",\
                       default=config["model"],\
                       help="AxiDraw Model (1-3). 1: AxiDraw V2 or V3. " \
                       + "2:AxiDraw V3/A3 or SE/A3. 3: AxiDraw V3 XLX.")

    options.add_option("--port",\
                       type="string", action="store", dest="port",\
                       default=config["port"],\
                       help="Serial port or named AxiDraw to use")

    options.add_option("--setup_type",\
                       type="string", action="store", dest="setup_type",\
                       default="align",\
                       help="Setup option selected (GUI Only)")
    
    options.add_option("--resume_type",\
                       type="string", action="store", dest="resume_type",\
                       default="plot",
                       help="The resume option selected (GUI Only)")
    
    options.add_option("--auto_rotate",\
                       type="inkbool", action="store", dest="auto_rotate",\
                       default=config["auto_rotate"], \
                       help="Boolean: Auto select portrait vs landscape")

    options.add_option("--reordering",\
                       type="int", action="store", dest="reordering",\
                       default=config["reordering"],\
                       help="Plot optimization option selected")

    options.add_option("--resolution",\
                       type="int", action="store", dest="resolution",\
                       default=config["resolution"],\
                       help="Resolution option selected")

    return options

def core_mode_options(parser, config):
    options = OptionGroup(parser, "Mode Options")    
    
    options.add_option("--mode",\
                       action="store", type="string", dest="mode",\
                       default="plot", \
                       help="Mode or GUI tab. One of: [plot, layers, align, toggle, manual"\
                       + ", sysinfo, version,  res_plot, res_home]. Default: plot.")

    options.add_option("--manual_cmd",\
                       type="string", action="store", dest="manual_cmd",\
                       default="fw_version",\
                       help="Manual command. One of: [fw_version, raise_pen, lower_pen, " \
                       + "walk_x, walk_y, enable_xy, disable_xy, bootload, strip_data, " \
                       + "read_name, list_names,  write_name]. Default: fw_version")
    
    options.add_option("--walk_dist",\
                       type="float", action="store", dest="walk_dist",\
                       default=1,\
                       help="Distance for manual walk (inches)")
    
    options.add_option("--layer",\
                       type="int", action="store", dest="layer",\
                       default=config["default_layer"],\
                       help="Layer(s) selected for layers mode (1-1000). Default: 1")
    
    options.add_option("--copies",\
                       type="int", action="store", dest="copies",\
                       default=config["copies"],\
                       help="Copies to plot, or 0 for continuous plotting. Default: 1")
    
    return options
