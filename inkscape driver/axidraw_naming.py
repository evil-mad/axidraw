# axidraw_naming.py
# Part of the AxiDraw driver for Inkscape
# https://github.com/evil-mad/AxiDraw
#
# See version_string below for detailed version number.

'''
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

from axidrawinternal import axidraw    # https://github.com/evil-mad/axidraw

from axidrawinternal.plot_utils_import import from_dependency_import # plotink
inkex = from_dependency_import('ink_extensions.inkex')

class AxiDrawNamingClass( inkex.Effect ): # pylint: disable=too-few-public-methods
    ''' Main class for AxiDraw Naming function '''

    def __init__( self ):
        inkex.Effect.__init__( self )

        self.version_string = "2.2.0" # Dated 2023-01-01

        self.arg_parser.add_argument( "--mode", action="store", type=str,
                dest="mode", default="plot", help="Mode (or GUI tab) selected" )
        self.arg_parser.add_argument( "--nickname", action="store", type=str,
                dest="nickname", default="", help="The nickname to assign" )

    def effect( self ):
        '''Main entry point: check to see which mode/tab is selected, and act accordingly.'''

        # Input sanitization:
        self.options.mode = self.options.mode.strip("\"")
        self.options.nickname = self.options.nickname.strip("\"")
        self.options.nickname = self.options.nickname.strip()

        if self.options.mode == "about":
            return

        ad_ref = axidraw.AxiDraw()

        ad_ref.called_externally = True

        # Pass the document off for plotting
        ad_ref.document = self.document

        ad_ref.options.mode = "manual"
        if self.options.mode == "list_names":
            ad_ref.options.manual_cmd = "list_names"
        if self.options.mode == "write_name":
            ad_ref.options.manual_cmd = "write_name" + self.options.nickname

        ad_ref.effect()

if __name__ == '__main__':
    e = AxiDrawNamingClass()
    e.affect()
