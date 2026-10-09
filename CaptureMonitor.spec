# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for CaptureMonitor (Windows onefile build)
#
# Build command (see build.bat):
#   pyinstaller --clean --noconfirm CaptureMonitor.spec
#
# Entry point: run.py -> capture_monitor.app.main()

datas = [('DEMO.png', '.'), ('assets/icon.png', 'assets')]
binaries = []
hiddenimports = ['cv2']

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CaptureMonitor',
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
    icon=['assets/icon.ico'],
)
