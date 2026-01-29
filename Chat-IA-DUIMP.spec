# -*- mode: python ; coding: utf-8 -*-
"""
Arquivo de especificação PyInstaller para Chat IA DUIMP.
Use: pyinstaller Chat-IA-DUIMP.spec
"""

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('nesh_chunks.json', '.'),  # ✅ NESH necessário para busca de notas explicativas
    ],
    hiddenimports=[
        'flask',
        'werkzeug',
        'sqlite3',
        'requests',
        'openai',
        'duckduckgo_search',
        'xhtml2pdf',
        'pyodbc',
        'services',
        'services.agents',
        'services.agents.processo_agent',
        'services.agents.ce_agent',
        'services.agents.di_agent',
        'services.agents.duimp_agent',
        'services.agents.cct_agent',
        'services.chat_service',
        'services.notificacao_service',
        'services.processo_kanban_service',
        'services.processo_repository',
        'services.models.processo_kanban_dto',
        'db_manager',
        'ai_service',
        'utils.sql_server_adapter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Chat-IA-DUIMP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Mudar para False se não quiser ver console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Adicionar caminho do ícone aqui se tiver
)

