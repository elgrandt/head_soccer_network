# -*- mode: python -*-

block_cipher = None


a = Analysis(['../pyinstaller.py'],
             pathex=['/home/newtonis/Dropbox/Proyectos2015/HeadSoccer/head_soccer_05/pyinstaller-develop/bin'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             cipher=block_cipher)
pyz = PYZ(a.pure,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='pyinstaller',
          debug=False,
          strip=None,
          upx=True,
          console=True )
