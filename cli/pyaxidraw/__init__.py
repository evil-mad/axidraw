import os
import sys

# make sources in "pyaxidraw" directories importable from anywhere (e.g., `import inkex`).
# this method of handling dependencies can cause subtle bugs,
# however due to requirements (files in pyaxidraw must be runnable as inkscape extension/script,
# pyaxidraw must work as a regular module in python 3) this is the best solution
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__))))
