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
    'dev': [ 'axidrawinternal>=3.0.0'], # see installation instructions
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
                pip_prefix = [sys.executable, '-m', 'pip']
                try:
                    subprocess.check_call(pip_prefix + ['uninstall', '--yes', pkg_name])
                except subprocess.CalledProcessError: # Will be raised if there is no version to uninstall
                    pass
                try:
                    subprocess.run(pip_prefix + ['install', wheel_file],
                                   capture_output=True, check=True)
                except subprocess.CalledProcessError as cpe:
                    # in certain cases, if the user has attempted to install AxiCli with the --user
                    # flag, there is an error due to not propagating this flag. In this case,
                    # try installing again with --user. See
                    # https://github.com/evil-mad/axidraw/issues/119 and
                    # https://gitlab.com/evil-mad/AxiCli/-/issues/84
                    if "--user" in str(cpe.stderr):
                        subprocess.run(pip_prefix + ['install', '--user', wheel_file], check=True)
                    else:
                        raise
    except (AttributeError, subprocess.CalledProcessError) as err:
        if sys.version_info < (3, 6):
            pass # pip has a standard message for this situation (see `python_requires` arg below)
        else: # python3
            raise RuntimeError("Could not install one or more prebuilt dependencies.", err.with_traceback(err.__traceback__))

    original_setup(*args, **kwargs)

original_setup = setuptools.setup
setuptools.setup = replacement_setup

replacement_setup(
    name='axicli',
    version='3.5.0',
    python_requires='>=3.7.0',
    long_description=long_description,
    long_description_content_type='text/plain',
    url='https://axidraw.com/doc/cli_api/',
    author='Evil Mad Scientist Laboratories',
    author_email='contact@evilmadscientist.com',
    packages=setuptools.find_packages(exclude=['contrib', 'docs', 'test']),
    install_requires=[
        # this only includes publicly available dependencies
        'ink_extensions>=1.1.0',
        'lxml>=4.9.1',
        'plotink>=1.6.1',
        'pyserial>=3.5',
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
