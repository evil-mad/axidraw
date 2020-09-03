# axidraw_naming.py
# Part of the AxiDraw driver for Inkscape
# https://github.com/evil-mad/AxiDraw
#
# See versionString below for detailed version number.

'''
Copyright 2020 Windell H. Oskay, Evil Mad Scientist Laboratories


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

# Requires Pyserial 2.7.0 or newer. Pyserial 3.0 recommended.

from lxml import etree

from axidrawinternal import axidraw	# https://github.com/evil-mad/axidraw

from axidrawinternal.plot_utils_import import from_dependency_import # plotink
inkex = from_dependency_import('ink_extensions.inkex')

class AxiDrawNamingClass( inkex.Effect ):

	def __init__( self ):
		inkex.Effect.__init__( self )

		self.OptionParser.add_option( "--mode",	action="store", type="string", dest="mode", default="plot", help="Mode (or GUI tab) selected" )
		self.OptionParser.add_option( "--nickname", action="store", type="string", dest="nickname", default="AxiDraw 1", help="The nickname to assign" )

	def effect( self ):
		'''Main entry point: check to see which mode/tab is selected, and act accordingly.'''

		self.versionString = "AxiDraw Naming - Version 2.1.0 dated 2019-05-15"
		
		# Input sanitization:
		self.options.mode = self.options.mode.strip("\"")
		self.options.nickname = self.options.nickname.strip("\"")

		if (self.options.mode == "about"):
			return

		ad = axidraw.AxiDraw()
						
		ad.getoptions([])

		ad.called_externally = True

		# Pass the document off for plotting
		ad.document = self.document 
		
		ad.options.mode = "manual"
		
		if (self.options.mode == "list_names"):
			ad.options.manual_cmd = "list_names"
		if (self.options.mode == "write_name"):
			ad.options.manual_cmd = "write_name" + self.options.nickname

		ad.effect()	


if __name__ == '__main__':
	e = AxiDrawNamingClass()
	e.affect()
