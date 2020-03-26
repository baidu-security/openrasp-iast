# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(['main.py'],
             pathex=['.'],
             binaries=[],
             datas=[("./config.default.yaml", "."),
                    ("./VERSION", "."),
                    ("./plugin", "./plugin")
                    ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

# multifile
# exe = EXE(pyz,
#           a.scripts,
#           [],
#           exclude_binaries=True,
#           name='openrasp-iast',
#           debug=False,
#           bootloader_ignore_signals=False,
#           strip=False,
#           upx=True,
#           console=True )

# coll = COLLECT(exe,
#                a.binaries,
#                a.zipfiles,
#                a.datas,
#                strip=False,
#                upx=True,
#                upx_exclude=[],
#                name='openrasp-iast')

# single file
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='openrasp-iast',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )