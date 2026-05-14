# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

# Дополнительные файлы для включения в exe
added_files = [
    ('config.json', '.'),                      # Конфигурация БД
    ('photo_analysis.db', '.'),                # SQLite база данных (если нужна)
]

# Скрытые импорты (библиотеки, которые PyInstaller может пропустить)
hidden_imports = [
    'sqlite3',
    'rawpy',
    'pyodbc',
    'PIL',
    'PIL._imaging',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL.ExifTags',
    'numpy',
    'numpy.core',
    'numpy.core._methods',
    'numpy.lib.format',
    'scipy',
    'scipy.ndimage',
    'scipy.signal',
    'scipy.fft',
    'cv2',
    'customtkinter',
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
]

# Исключаем ненужные модули для уменьшения размера
excludes = [
    'tkinter.test',
    'unittest',
    'pdb',
    'test',
    'distutils',
    'setuptools',
    'pydoc',
    'email',
    'http',
    'xml',
    'html',
    'curses',
    'dbm',
    'lib2to3',
]

# Анализируем все необходимые файлы
a = Analysis(
    ['gui_app.py', 'analyzer.py', 'database.py', 'dxomark_service.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PhotoQualityAnalyzerGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # ← Важно: False для GUI приложения (без консоли)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)