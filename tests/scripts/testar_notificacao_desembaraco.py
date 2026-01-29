#!/usr/bin/env python3
"""
Script para simular mudança de status DUIMP e testar notificações de desembaraço.
"""
import sys
import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# ✅ CORREÇÃO: Adicionar diretório raiz ao path (subir 2 níveis: tests/scripts/ -> raiz)
# ✅ CORREÇÃO: Garantir que funciona mesmo quando executado com caminho absoluto
try:
    # Tentar usar __file__ primeiro (funciona na maioria dos casos)
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.parent.resolve()
except (NameError, AttributeError):
    # Fallback: usar o diretório de trabalho atual e subir até encontrar a raiz do projeto
    current_dir = Path(os.getcwd())
    project_root = current_dir
    # Procurar por indicadores de que estamos na raiz (app.py, services/, etc.)
    while project_root != project_root.parent:
        if (project_root / 'app.py').exists() and (project_root / 'services').exists():
            break
        project_root = project_root.parent
    # Se não encontrou, usar diretório atual
    if not (project_root / 'app.py').exists():
        project_root = current_dir

sys.path.insert(0, str(project_root))

from services.models.processo_kanban_dto import ProcessoKanbanDTO
from services.notificacao_service import NotificacaoService

def simular_mudanca_desembaraco(processo_referencia: str = 'VDM.0004/25'):
    """
    Simula uma mudança de status DUIMP para desembaraçada e testa as notificações.
    """
    print(f"🧪 Simulando mudança de desembaraço para {processo_referencia}\n")
    
    # ✅ CORREÇÃO: Conectar ao banco na raiz do projeto
    db_path = project_root / 'chat_ia.db'
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Buscar processo atual
    cursor.execute('''
        SELECT dados_completos_json, numero_duimp, modal, pendencia_icms, pendencia_frete
        FROM processos_kanban
        WHERE processo_referencia = ?
    ''', (processo_referencia,))
    
    row = cursor.fetchone()
    if not row:
        print(f"❌ Processo {processo_referencia} não encontrado no banco")
        print(f"\n💡 Processos disponíveis no banco (primeiros 10):")
        cursor.execute('SELECT processo_referencia FROM processos_kanban LIMIT 10')
        processos = cursor.fetchall()
        if processos:
            for proc in processos:
                print(f"   - {proc[0]}")
            print(f"\n💡 Use um dos processos acima como argumento:")
            print(f"   python3 {Path(__file__).name} <processo_referencia>")
        else:
            print("   ⚠️ Nenhum processo encontrado no banco")
        conn.close()
        return
    
    # Carregar dados atuais
    dados_atual = json.loads(row['dados_completos_json']) if row['dados_completos_json'] else {}
    
    notif_service = NotificacaoService()
    
    print(f"📋 Status atual da DUIMP:")
    dto_atual = ProcessoKanbanDTO.from_kanban_json(dados_atual)
    status_atual = notif_service._extrair_status_duimp(dto_atual.dados_completos)
    print(f"   {status_atual}\n")
    
    # Criar versão anterior (simulando que estava registrada)
    # Fazer deep copy para garantir que modificações não afetem o original
    import copy
    dados_anterior = copy.deepcopy(dados_atual)
    
    # Garantir que tem estrutura duimp
    if 'duimp' not in dados_anterior:
        dados_anterior['duimp'] = []
    
    if isinstance(dados_anterior['duimp'], list):
        if len(dados_anterior['duimp']) > 0:
            # Modificar status existente
            dados_anterior['duimp'][0] = copy.deepcopy(dados_anterior['duimp'][0])
            dados_anterior['duimp'][0]['situacao_duimp'] = 'REGISTRADA_AGUARDANDO_CANAL'
            dados_anterior['duimp'][0]['situacao_duimp_agr'] = 'REGISTRADA_AGUARDANDO_CANAL'
            dados_anterior['duimp'][0]['ultima_situacao'] = 'REGISTRADA_AGUARDANDO_CANAL'
        else:
            # Criar estrutura básica
            dados_anterior['duimp'] = [{
                'numero': row['numero_duimp'] or '25BR00002369283',
                'situacao_duimp': 'REGISTRADA_AGUARDANDO_CANAL',
                'situacao_duimp_agr': 'REGISTRADA_AGUARDANDO_CANAL',
                'ultima_situacao': 'REGISTRADA_AGUARDANDO_CANAL'
            }]
    
    dto_anterior = ProcessoKanbanDTO.from_kanban_json(dados_anterior)
    
    # Criar versão nova (desembaraçada) - fazer deep copy também
    dados_novo = copy.deepcopy(dados_atual)
    
    # Garantir que tem estrutura duimp
    if 'duimp' not in dados_novo:
        dados_novo['duimp'] = []
    
    if isinstance(dados_novo['duimp'], list):
        if len(dados_novo['duimp']) > 0:
            # Modificar status existente
            dados_novo['duimp'][0] = copy.deepcopy(dados_novo['duimp'][0])
            dados_novo['duimp'][0]['situacao_duimp'] = 'DESEMBARACADA_AGUARDANDO_PENDENCIA'
            dados_novo['duimp'][0]['situacao_duimp_agr'] = 'DESEMBARACADA_AGUARDANDO_PENDENCIA'
            dados_novo['duimp'][0]['ultima_situacao'] = 'DESEMBARACADA_AGUARDANDO_PENDENCIA'
        else:
            # Criar estrutura básica
            dados_novo['duimp'] = [{
                'numero': row['numero_duimp'] or '25BR00002369283',
                'situacao_duimp': 'DESEMBARACADA_AGUARDANDO_PENDENCIA',
                'situacao_duimp_agr': 'DESEMBARACADA_AGUARDANDO_PENDENCIA',
                'ultima_situacao': 'DESEMBARACADA_AGUARDANDO_PENDENCIA'
            }]
    
    dto_novo = ProcessoKanbanDTO.from_kanban_json(dados_novo)
    
    # Ajustar pendências para teste
    dto_novo.pendencia_icms = row['pendencia_icms'] or 'Pendente'
    dto_novo.pendencia_frete = row['pendencia_frete']
    dto_novo.modal = row['modal'] or 'Marítimo'
    
    # Garantir que dados_completos está atualizado
    dto_anterior.dados_completos = dados_anterior
    dto_novo.dados_completos = dados_novo
    
    print(f"📋 Status anterior (simulado):")
    status_anterior = notif_service._extrair_status_duimp(dto_anterior.dados_completos)
    print(f"   {status_anterior}\n")
    
    print(f"📋 Status novo:")
    status_novo = notif_service._extrair_status_duimp(dto_novo.dados_completos)
    print(f"   {status_novo}\n")
    
    # Verificar detecção
    print("🔍 Verificando detecção de mudanças:\n")
    status_mudou = notif_service._status_duimp_mudou(dto_anterior, dto_novo)
    desembaracou = notif_service._duimp_desembaracou(dto_anterior, dto_novo)
    
    print(f"   Status mudou: {status_mudou}")
    print(f"   Desembaraçou: {desembaracou}\n")
    
    if not status_mudou:
        print("⚠️ Status não foi detectado como mudado. Verificando...")
        return
    
    # Simular criação de notificações
    print("🔔 Criando notificações...\n")
    notificacoes = notif_service.detectar_mudancas_e_notificar(dto_anterior, dto_novo)
    
    if notificacoes:
        print(f"✅ {len(notificacoes)} notificação(ões) criada(s):\n")
        for i, notif in enumerate(notificacoes, 1):
            print(f"   {i}. {notif.get('tipo_notificacao')}: {notif.get('titulo')}")
            
            # Mostrar mensagem formatada para TTS
            if notif.get('dados_extras'):
                try:
                    dados_extras = json.loads(notif.get('dados_extras', '{}'))
                    texto_tts = dados_extras.get('texto_tts', '')
                    if texto_tts:
                        print(f"      📝 Texto TTS formatado:")
                        # Mostrar texto completo ou primeiras linhas
                        linhas_tts = texto_tts.split('\n')
                        for linha in linhas_tts[:10]:  # Primeiras 10 linhas
                            if linha.strip():
                                print(f"         {linha}")
                        if len(linhas_tts) > 10:
                            print(f"         ... ({len(linhas_tts) - 10} linhas a mais)")
                except Exception as e:
                    print(f"      ⚠️ Erro ao ler texto TTS: {e}")
            
            print()
        
        # Verificar se há notificação de pagamentos
        notif_pagamentos = [n for n in notificacoes if n.get('tipo_notificacao') == 'pagamentos_necessarios']
        if notif_pagamentos:
            print("💰 Notificação de pagamentos encontrada:")
            notif = notif_pagamentos[0]
            print(f"   Título: {notif.get('titulo')}")
            print(f"   Mensagem completa:")
            mensagem = notif.get('mensagem', '')
            # Mostrar mensagem em partes
            linhas = mensagem.split('\n')
            for linha in linhas[:20]:  # Primeiras 20 linhas
                if linha.strip():
                    print(f"      {linha}")
            if len(linhas) > 20:
                print(f"      ... ({len(linhas) - 20} linhas a mais)")
    else:
        print("❌ Nenhuma notificação foi criada")
    
    conn.close()
    print("\n✅ Teste concluído!")

if __name__ == '__main__':
    processo = sys.argv[1] if len(sys.argv) > 1 else 'VDM.0004/25'
    simular_mudanca_desembaraco(processo)


