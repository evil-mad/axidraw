"""
Based on https://github.com/pypa/sampleproject

"""

# Always prefer setuptools over distutils
import glob
import setuptools
import subprocess
import sys
from os import path
from io import open

here = path.abspath(path.dirname(__file__))

print("WARNING: It looks like you might be attempting to install this in a non-pip way. This is discouraged. Use `pip install .` (or `pip install -r requirements.txt` if you are a developer with access to the relevant private repositories).")

extras_require = {
    'dev': [ 'axidrawinternal'], # see installation instructions
    'test': [
        'coverage', # coverage run -m unittest discover && coverage html
        'mock',
        'pyfakefs',
    ]
}

extras_require['dev'].extend(extras_require['test']) # if you're developing, you're testing

# Get the long description from the README file
with open(path.join(here, 'README.txt'), encoding='utf-8') as f:
    long_description = f.read()

def replacement_setup(*args, **kwargs):
    depdir = "prebuilt_dependencies"
    if path.isdir(depdir): #installing on a non-privileged machine; todo consider adding a check for the pip -e flag
        for wheel in glob.glob("/".join([depdir, "*"])):
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', wheel])
    original_setup(*args, **kwargs)

original_setup = setuptools.setup
setuptools.setup = replacement_setup

replacement_setup(
    name='pyaxidraw',
    version='2.6.3',
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
        'pyserial>=2.7.0', # 3.0 recommended
        'requests', # just for the certificates for now
        'plotink>=1.0.0',
    ],
    extras_require=extras_require,
    entry_points={
        'console_scripts': [
            'axicli = axicli.__main__:axidraw_CLI',
        ]
    },
)
