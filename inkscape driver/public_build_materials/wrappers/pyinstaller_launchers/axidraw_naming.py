'''
Automatically generated launcher to launch axidraw_naming.
This launcher is used for scripts that are built via pyinstaller (e.g. axidraw_control.py, axidraw_naming.py).
'''
import subprocess
import sys

command = ['./build_deps/axidraw_naming'] + sys.argv[1:]
proc = subprocess.run(command, capture_output=True, text=True)

# print error messages, if there are any
if proc.stderr != "":
    sys.stderr.write(proc.stderr)

# inkscape parses stdout for the result of an extension
sys.stdout.write(proc.stdout)
