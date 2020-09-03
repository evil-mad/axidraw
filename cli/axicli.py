'''
axicli.py   - Command line interface (CLI) for AxiDraw.

For quick help:
    python axicli.py --help

Full user guide:  
    https://axidraw.com/doc/cli_api/


This script is a stand-alone version of AxiDraw Control, accepting 
various options and providing a facility for setting default values.

'''

from axicli.axidraw_cli import axidraw_CLI

if __name__ == '__main__':
    axidraw_CLI()
