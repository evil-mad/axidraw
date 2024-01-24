#! /bin/bash

# Automates the building of the AxiDraw pkg for Inkscape users.
# See the README for instructions.

set -e # exit on error

# defaults
build_dir=axidraw_for_inkscape_build
python_executable=python3
verbose=false
apple=false
windows=false

# assign command line params
while [ "$1" != "" ]; do
      case $1 in
           -p | --python )      shift
                                python_executable=$1
                                shift
                                ;; 
           --apple )            shift
                                apple=true
                                ;;
           --windows )          shift
                                windows=true
                                ;;
           --verbose )          shift
                                verbose=true
      esac
done

./set_up_build.sh --builddir $build_dir --python $python_executable $($windows && echo '--windows') $($verbose && echo '--verbose') $($apple && echo '--apple')

echo "DONE SETTING UP, ON TO THE BUILD"

./build_and_package.sh --builddir $build_dir --output $build_dir.zip $($apple && echo '--apple') $($windows && echo '--windows') $($verbose && echo '--verbose')

