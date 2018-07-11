# axidraw_naming.py
# Part of the AxiDraw driver for Inkscape
# https://github.com/evil-mad/AxiDraw
#
# See versionString below for detailed version number.
#
# Copyright 2018 Windell H. Oskay, Evil Mad Scientist Laboratories
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Requires Pyserial 2.7.0 or newer. Pyserial 3.0 recommended.


import inkex
import axidraw	# https://github.com/evil-mad/axidraw

class AxiDrawNamingClass( inkex.Effect ):

	def __init__( self ):
		inkex.Effect.__init__( self )

		self.OptionParser.add_option( "--mode",	action="store", type="string", dest="mode", default="plot", help="Mode (or GUI tab) selected" )
		self.OptionParser.add_option( "--nickname", action="store", type="string", dest="nickname", default="AxiDraw 1", help="The nickname to assign" )

	def effect( self ):
		'''Main entry point: check to see which mode/tab is selected, and act accordingly.'''

		self.versionString = "AxiDraw Naming - Version 2.0.0 dated 2018-07-10"
		
		# Input sanitization:
		self.options.mode = self.options.mode.strip("\"")
		self.options.nickname = self.options.nickname.strip("\"")

		if (self.options.mode == "about"):
			return

		ad = axidraw.AxiDrawClass()
						
		ad.getoptions([])

		ad.called_externally = True

		# Pass the document off for plotting
		ad.document = self.document 
		
		ad.options.mode = "manual"
		if (self.options.mode == "read-name"):
			ad.options.manual_type = "read-name"
		if (self.options.mode == "write-name"):
			ad.options.manual_type = "write-name" + self.options.nickname
# 			ad.options.setup_type = self.options.nickname

		ad.effect()	


if __name__ == '__main__':
	e = AxiDrawNamingClass()
	e.affect()
