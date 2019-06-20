from importlib import import_module
import sys
import os

# this handles importing in two major cases

DEPENDENCY_DIR_NAME = 'axidraw_deps'
DEPENDENCY_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), DEPENDENCY_DIR_NAME)

def from_dependency_import(module_name):
    ''' module_name ex: "ink_extensions", "ink_extensions.inkex" '''
    module = None

    if os.path.isdir(DEPENDENCY_DIR):
        # running as an inkscape extension in inkscape
        sys.path.append(DEPENDENCY_DIR)
        try:
            module = import_module("{}.{}".format(DEPENDENCY_DIR_NAME, module_name))
        finally:
            if DEPENDENCY_DIR in sys.path:
                sys.path.remove(DEPENDENCY_DIR)
    else:
        # running as a python module with traditionally installed packages
        # e.g. if you used pip or setup.py
        module = import_module(module_name)

    return module
