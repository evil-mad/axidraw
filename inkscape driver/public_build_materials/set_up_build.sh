#! /bin/bash
# The easiest/best way to run this is by running it from buildink. Refer there for documentation.

# This script sets up the directory structure needed to build the final product.

set -e # exit on error

# CONSTANTS
HERSHEY_TEXT_DIR=hershey-text/hershey-text

# DEFAULTS
build_dir=axidraw_for_inkscape_build
ink_version=1
python_executable=python
quiet_flag="-q"
windows=false
apple=false

source ./utils.sh

# COMMAND LINE PARAMS
while [ "$1" != "" ]; do
      case $1 in
           -p | --python )      shift
                                python_executable=$1
                                shift
                                ;;
           --builddir )         shift
                                build_dir=$1
                                shift
                                ;;
           --windows )          shift
                                windows=true
                                ;;
           --apple )            shift
                                apple=true
                                ;;
           --verbose )          shift
                                quiet_flag=""
      esac
done

dependency_dir=$build_dir/axidraw_deps
# this is where pip installs the dependencies
if $windows; then
  install_location="$build_dir/venv/Lib/site-packages"
else # mac, unix
  install_location="$build_dir/venv/lib/python*/site-packages"
fi

# list of files to remove from final build
removed="$dependency_dir/axidrawinternal/*.inx"

python_version=`$python_executable --version 2>&1`
echo "Setting up build for inkscape $ink_version and $python_version in $build_dir"

# BEGIN
rm -r -f $build_dir
mkdir $build_dir

# VIRTUAL ENVIRONMENT
echo "Setting up virtual environment"
$python_executable -m venv $build_dir/venv
source $build_dir/venv/*/activate

echo "Installing other program dependencies in virtual environment"
pip $quiet_flag install -r ./requirements.txt

if $apple; then
  # make sure to use universal2 binaries
  for builtlib in "pyclipper" "lxml"; do
    builtlib_ver=$(pip freeze | grep $builtlib)
    pip uninstall $quiet_flag -y $builtlib
    pip install $builtlib_ver --platform universal2 --abi none --target $install_location --no-deps
  done
  # make sure to use pure python version of charset-normalizer
  # (using universal2 binary might work too)
  cn_ver=$(pip freeze | grep charset-normalizer)
  pip uninstall $quiet_flag -y charset-normalizer
  pip $quiet_flag cache remove charset-normalizer # Remove cached version, just in case
  pip $quiet_flag install $cn_ver --no-binary :all:
fi

# POPULATE DEPENDENCY DIR
echo "Copying python-only dependencies into $dependency_dir"
mkdir $dependency_dir
touch $dependency_dir/__init__.py

# inhouse_packages and other_packages are lists of pure-python packages that can be copied
# into the axidraw_deps directory and used that way. In an ideal world, only inhouse_packages
# would be placed in this directory (helpful for development purposes). Unless and until all
# scripts are built using pyinstaller, however, putting non-inhouse pure-python packages
# in axidraw_deps works fine. (If a script depends on a non-pure-python package, that script
# then must be build using pyinstaller.)
inhouse_packages="ink_extensions plotink"
other_packages="urllib3 idna requests certifi charset_normalizer packaging serial mpmath"
for file in $inhouse_packages $other_packages; do
  cp -r $install_location/$file* $dependency_dir
done

# COPY FILES TO BASE DIRECTORY

echo "Copying files from other repos that aren't set up as python dependencies (hershey-text, wcb-ink, eggbot) to base directory"
get_files_from_repo https://github.com/evil-mad/wcb-ink.git wcb-ink master extensions $build_dir
get_files_from_repo https://github.com/evil-mad/EggBot.git EggBot master inkscape_driver $build_dir
get_files_from_repo https://github.com/evil-mad/axidraw.git axidraw master "" $build_dir

# axidraw/*.inx and config must be in the top layer of the extensions directory
cp axidraw/inkscape\ driver/*.inx $build_dir
cp axidraw/inkscape\ driver/axidraw_conf.py $build_dir
# whereas the python modules should go in the dependency dir
mkdir $dependency_dir/axidrawinternal
cp -r axidraw/inkscape\ driver/* $dependency_dir/axidrawinternal
rm $dependency_dir/axidrawinternal/*.inx


# plot_utils_import must be in the top layer of the extensions directory so the extensions have access
cp $install_location/plotink/plot_utils_import.py $build_dir

# GET WRAPPERS
cp -r wrappers/* $build_dir

# REMOVE FILES FROM BUILD
# a few of the scripts are not to be included. Delete them.
for file in $removed; do
 rm -f $file
done
rm -r -f $build_dir/tests

echo "Done setting up"
