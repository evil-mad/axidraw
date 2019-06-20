"""
Based on https://github.com/pypa/sampleproject

"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from os import path
from io import open

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.txt'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pyaxidraw',
    version='2.5.3',
    long_description=long_description,
    long_description_content_type='text/plain',
    url='https://axidraw.com/doc/cli_api/',
    author='Evil Mad Scientist Laboratories',
    author_email='contact@evilmadscientist.com',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=[
        'ink_extensions',
        'lxml',
        'pyserial>=2.7.0' # 3.0 recommended
    ],
    extras_require={
        'dev': [],
        'test': [
            'mock'
        ],
    },
    entry_points={
        'console_scripts': [
            'axicli = axicli.__main__:main'
        ]
    }
)
