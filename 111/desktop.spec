# PyInstaller 打包规范（桌面应用）
#
# 用法：
#   pip install pyinstaller pywebview
#   cd frontend && npm run build && cd ..
#   pyinstaller desktop.spec
#
# 产出：dist/SmartDataAnalysis/SmartDataAnalysis.exe（双击即起）

# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    ['desktop_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 把前端 dist 资源整体打包
        ('frontend_dist', 'frontend_dist'),
    ],
    hiddenimports=[
        'webview.platforms.winforms',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy', 'tkinter',
        # 让打包更小：去除非用到的大库
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SmartDataAnalysis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # 双击启动无黑色窗口
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SmartDataAnalysis',
)
