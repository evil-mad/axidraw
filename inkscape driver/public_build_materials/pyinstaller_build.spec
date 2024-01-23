# -*- mode: python ; coding: utf-8 -*-
import os
import platform
import sys
from copy import deepcopy

block_cipher = None

binaries = []
target_arch = None
if platform.system() == "Darwin": # mac
    target_arch = "universal2"

elif platform.system() == "Windows":
    binaries = [
        ('../assets/DLLs/arm/*', './arm'),
        ('../assets/DLLs/x64/*', './x64'),
        ('../assets/DLLs/x86', './x86')
    ]


analysis_params = {
    'pathex': ['/Users/username/programming/clean'], # this path doesn't seem to matter
    'binaries': binaries,
    'datas': [],
    'hiddenimports': [
               # packages
               'requests',
               'lxml',
               'numbers',
               'packaging',
               'pyclipper',
               'serial',
               'serial.tools',
               'serial.tools.list_ports',
               'tqdm',
               'mpmath', # plotink
               # random extra modules that are necessary
               # to include here for some reason
               'distutils.version', # axidrawinternal
               'cmath', # ink_extensions
    ],
    'hookspath': [],
    'runtime_hooks': [],
    'excludes': [],
    'win_no_prefer_redirects': False,
    'win_private_assemblies': False,
    'cipher': block_cipher,
    'noarchive': False
}
control_analysis = Analysis(['./axidraw_control.py'], **deepcopy(analysis_params))
naming_analysis = Analysis(['./axidraw_naming.py'], **deepcopy(analysis_params))
merge_params = [(control_analysis, 'axidraw_control', os.path.join('dir_axidraw_control', 'axidraw_control')),
                (naming_analysis, 'axidraw_naming', os.path.join('dir_axidraw_naming', 'axidraw_naming'))
               ]
'''
MERGE(*merge_params)
'''
exes = []
for a, script_name, _ in merge_params:
    pyz = PYZ(a.pure, a.zipped_data,
              cipher=block_cipher)
    exes.append(EXE(pyz,
              a.scripts,
              [],
              exclude_binaries=True,
              name=script_name,
              debug=False,
              bootloader_ignore_signals=False,
              strip=False,
              upx=False,
              console=False,
              target_arch=target_arch))


coll = COLLECT(*exes,
              control_analysis.binaries,
              control_analysis.zipfiles,
              control_analysis.datas,
              naming_analysis.binaries,
              naming_analysis.zipfiles,
              naming_analysis.datas,
              strip=False,
              upx=False,
              upx_exclude=[],
              name='build_deps')
