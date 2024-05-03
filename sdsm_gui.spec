# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['sdsm_gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

excludes=(
    'opengl32sw.dll',
    'Qt6Network.dll',
    'Qt6OpenGL.dll',
    'Qt6Pdf.dll',
    'Qt6Qml.dll',
    'Qt6QmlModels.dll',
    'Qt6Quick.dll',
    'Qt6VirtualKeyboard.dll'
    'QtNetwork.pyd',
)
a.datas = [x for x in a.datas if not x[0].startswith('PySide6\\translations')]
a.binaries = [x for x in a.binaries if not x[0].endswith(excludes)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='StardewSaveManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
