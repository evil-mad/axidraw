# Bail out if python is less than 3.7
import sys
MIN_VERSION = (3, 7)
if sys.version_info < MIN_VERSION:
    sys.exit("AxiDraw software must be run with python 3.7 or greater.")
