"""
Based on https://github.com/pypa/sampleproject

"""

# Always prefer setuptools over distutils
import glob
from io import open
from os import path
import re
import setuptools
import subprocess
import sys

here = path.abspath(path.dirname(__file__))

print("WARNING: It looks like you might be attempting to install this in a non-pip way. This is discouraged. Use `pip install .` (or `pip install -r requirements.txt` if you are a developer with access to the relevant private repositories).")

extras_require = {
    'dev': [ 'axidrawinternal'], # see installation instructions
    'test': [
        'coverage', # coverage run -m unittest discover && coverage html
        'mock',
        'pyfakefs>=4.2.1',
    ],
}

extras_require['dev'].extend(extras_require['test']) # if you're developing, you're testing

# Get the long description from the README file
with open(path.join(here, 'README.txt'), encoding='utf-8') as f:
    long_description = f.read()

def replacement_setup(*args, **kwargs):
    try:
        depdir = "prebuilt_dependencies"
        if path.isdir(depdir): #installing on a non-privileged machine
            pkg_pattern = re.compile('(?P<pkg>[a-zA-Z]*)-[0-9]')
            for wheel_file in glob.glob(path.join(depdir, "*")):
                pkg_name = pkg_pattern.search(wheel_file).group('pkg')
                try:
                    subprocess.check_call(
                        [sys.executable, '-m', 'pip', 'uninstall', '--yes', pkg_name])
                except subprocess.CalledProcessError: # Will be raised if there is no version to uninstall
                    pass
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', wheel_file])
    except (AttributeError, subprocess.CalledProcessError) as err:
        raise RuntimeError("Could not install one or more prebuilt dependencies.") from err

    original_setup(*args, **kwargs)

original_setup = setuptools.setup
setuptools.setup = replacement_setup

replacement_setup(
    name='pyaxidraw',
    version='2.7.5',
    python_requires='>=3.6.0',
    long_description=long_description,
    long_description_content_type='text/plain',
    url='https://axidraw.com/doc/cli_api/',
    author='Evil Mad Scientist Laboratories',
    author_email='contact@evilmadscientist.com',
    packages=setuptools.find_packages(exclude=['contrib', 'docs', 'test']),
    install_requires=[
        # this only includes publicly available dependencies
        'ink_extensions>=1.1.0',
        'lxml',
        'plotink>=1.2.4',
        'requests', # just for the certificates for now
    ],
    extras_require=extras_require,
    entry_points={
        'console_scripts': [
            'axicli = axicli.__main__:axidraw_CLI',
            'htacli = axicli.__main__:hta_CLI',
        ]
    },
)
