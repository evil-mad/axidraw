Instructions for building the AxiDraw plugin for Inkscape from this public bundle.

Tested on python 3.11, Mac, Windows, and Linux.

Copyright 2024 Evil Mad Scientist Laboratories

The AxiDraw writing and drawing machine is a product of Evil Mad Scientist
Laboratories. https://axidraw.com   https://shop.evilmadscientist.com

----------

1.) Install python.

These instructions were tested on python3.11. python3.8 and above are probably acceptable.

Macs and linux boxes usually have python pre-installed.

If you are on Windows, you'll probably not already have this on your computer. 
Go to: https://www.python.org/download/

2.) Enter the `public_build_materials` directory:

    cd public_build_materials

3.) Run the build:

    bash ./buildink.sh

This will create a directory called `axidraw_for_inkscape_build`

3.) Copy the contents of `axidraw_for_inkscape_build` into Inkscape's `extensions` directory.
To find your installation's `extensions` directory, open Inkscape. Under the "Edit" menu,
click on "Preferences". Click "System". Find the directory path in the  "User extensions" field.

For example:

    cp -r axidraw_for_inkscape_build/* ~/.config/inkscape/extensions

4.) Open Inkscape. (If Inkscape is already open, close it first, then reopen.)

The extensions can now be found under the "Extensions" menu.
See axidraw.com for more instructions and help.

----------

Licensing:

The AxiDraw CLI and top level example scripts are licensed under the MIT license. 
Some of the underlying libraries that are included with this distribution
are licensed as GPL. Please see the individual files and directories included with
this distribution for additional license information. 
