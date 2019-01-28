# -*- mode: python -*-

block_cipher = None


a = Analysis(['VMIcrtlGUI_v12.py'],
             pathex=['/home/thomasb/Documents/wetlab-software/lib_thomasb/DAQ/VMI_PEPICO'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='VMIcrtlGUI_v12',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='VMIcrtlGUI_v12')
