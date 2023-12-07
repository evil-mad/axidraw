"""
Based on https://github.com/pypa/sampleproject

"""

# Always prefer setuptools over distutils
import pathlib
import re
import setuptools

# install_requires is dynamically created (below) and therefore cannot easily be
# specified in pyproject.toml, so it is specified here.

install_requires=[
        'ink_extensions>=1.3.2',
        'lxml>=4.9.3',
        'plotink>=1.8.0',
        'pyserial>=3.5',
        'requests',
    ]


here = pathlib.Path.absolute(pathlib.Path(__file__).parent)
depdir = here.joinpath("prebuilt_dependencies")
if depdir.is_dir(): #installing on a non-privileged machine
    pkg_pattern = re.compile('(?P<pkg>[a-zA-Z]*)-[0-9]')
    for wheel_path in depdir.glob("*.whl"):
        wheel_file = wheel_path.name
        pkg_name = pkg_pattern.search(wheel_file).group('pkg')
        install_requires.append(f"{pkg_name} @ {wheel_path.as_uri()}")

setuptools.setup(
    packages=setuptools.find_packages(exclude=['contrib', 'docs', 'test']),
    install_requires=install_requires,
)
