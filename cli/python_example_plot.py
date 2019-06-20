#!/usr/bin/env python
# -*- encoding: utf-8 -#-

'''
python_example_plot.py

Demonstrate use of axidraw module in "plot" mode, to plot an SVG file.

Run this demo by calling: python python_example_plot.py


This is a minimal example to show how one can import the AxiDraw module
and use it to plot an SVG file with the AxiDraw.

(There is also a separate "interactive" mode, which can be used for moving
the AxiDraw to various points upon command, rather than plotting an SVG file.)


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



Copyright 2019 Windell H. Oskay, Evil Mad Scientist Laboratories

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




from pyaxidraw import axidraw

ad = axidraw.AxiDraw()             # Create class instance
ad.plot_setup("test/assets/AxiDraw_trivial.svg")    # Parse the input file

'''
The following is a list of options that may be set
ad.options.mode 
ad.options.speed_pendown
ad.options.speed_penup
ad.options.accel
ad.options.pen_pos_down
ad.options.pen_pos_up
ad.options.pen_rate_lower
ad.options.pen_rate_raise
ad.options.pen_delay_down
ad.options.pen_delay_up
ad.options.auto_rotate
ad.options.const_speed
ad.options.report_time
ad.options.manual_cmd
ad.options.walk_dist
ad.options.layer
ad.options.copies
ad.options.page_delay
ad.options.preview
ad.options.rendering
ad.options.reordering
ad.options.model
ad.options.port
ad.options.port_config

See documentation for a description of these items and their allowed values.

'''

ad.options.speed_pendown = 50 # Set maximum  pen-down speed to 50%

ad.plot_run()   # plot the document
