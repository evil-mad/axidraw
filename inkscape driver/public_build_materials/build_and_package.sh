#! /bin/bash
# Actually build the release. This step must be done on the enviroment (i.e. mac, linux, arm) it's being built for. --builddir must be the dir created as a result of running buildink_setup. See buildink for usage.

set -e # exit on error

source ./utils.sh

# DEFAULTS
output_file=axidraw_for_inkscape_release.zip
quiet_flag="-q"
build_dir=axidraw_for_inkscape_build
apple=false
windows=false

# COMMAND LINE PARAMS
while [ "$1" != "" ]; do
      case $1 in
           -o | --output )      shift
                                output_file=$1
                                shift
                                ;;
           --builddir )         shift
                                build_dir=$1
                                shift
                                ;;
           --apple )            shift
                                apple=true
                                ;;
           --windows )          shift
                                windows=true
                                ;;
           --verbose )          shift
                                quiet_flag=""
      esac
done

source $build_dir/venv/*/activate

# BUILD THE EXECUTABLE
echo "Building the executable"
cp ./pyinstaller_build.spec $build_dir
pyinstaller $build_dir/pyinstaller_build.spec --noconfirm --distpath $build_dir --log-level WARN --clean

cp $build_dir/pyinstaller_launchers/axidraw_control.py $build_dir/axidraw_control.py
cp $build_dir/pyinstaller_launchers/axidraw_naming.py $build_dir/axidraw_naming.py
rm -r $build_dir/pyinstaller_launchers

find . -type f -name *.pyc -delete # remove superfluous pyc files
rm $build_dir/*_build.spec
rm -r -f $build_dir/__pycache__

ls $build_dir/hershey_axidraw.inx # ensure it exists

chmod a+x $build_dir

deactivate # not in the virtualenv anymore
rm -r -f $build_dir/venv

echo "Built into $build_dir"
