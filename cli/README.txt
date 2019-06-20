Stand-alone command line interface and python API
for the AxiDraw writing and drawing machine.

Supported on python 2.7, python 3.6, Mac, Windows, and Linux.


Copyright 2019 Evil Mad Scientist Laboratories

The AxiDraw writing and drawing machine is a product of Evil Mad Scientist
Laboratories. https://axidraw.com   https://shop.evilmadscientist.com


----------


Please see Installation.txt for requirements.


----------

This directory contains the following items:

axicli.py                         - One way to invoke the command line interface (CLI) program

axicli/                           - The CLI module directory

pyaxidraw/                        - The AxiDraw python module directory

Installation.txt                  - Installation documentation

python_example_plot.py            - Example files, showing use of this software
python_example_xy.py	            as a python module, to plot an SVG file,
python_example_toggle.py            execute XY motion commands, or toggle pen up/down

test/assets/AxiDraw_trivial.svg   - Sample SVG file that can be plotted
----------

COMMAND LINE INTERFACE: USAGE

For detailed documentation, please refer to:
    
    https://axidraw.com/doc/cli_api/


Quick start (CLI): 

(1) To plot an SVG document called "AxiDraw_trivial.svg" from the command line,
    use the AxiDraw CLI:

        axicli test/assets/AxiDraw_trivial.svg


(2) The CLI features an extensive set of control options. For quick help, use: 

        axicli --help

Some alternative commands (functionally identical):

        python axicli.py <input>
        python -m axicli <input>

----------
    
PYTHON API: USAGE

For detailed documentation, please refer to:
    
    https://axidraw.com/doc/py_api/
    
Quick Start:

(1) The file "python_example_plot.py" is an example python script, showing how
one can use a the axidraw python module in "plot" mode to open and plot an SVG
file. 

    To run the example, call:

        python python_example_plot.py

    This is a minimal demonstration script for opening and plotting an SVG file
    (in this case, "AxiDraw_trivial.svg") from within a python script. 


(2) The file "python_example_xy.py" is an example python script, showing how one
can use a the axidraw python module in "interactive" mode, to execute absolute
and relative XY motion control commands like move(x,y), lineto(x,y), penup()
and pendown(). 

    To run the example, call:

        python python_example_xy.py




----------
    

Licensing:

The AxiDraw CLI and top level example scripts are licensed under the MIT license. 
Some of the underlying libraries that are included with this distribution
are licensed as GPL. Please see the individual files and directories included with
this distribution for additional license information. 

API Documentation: Copyright 2019, Windell H. Oskay, Evil Mad Scientist Laboratories.



