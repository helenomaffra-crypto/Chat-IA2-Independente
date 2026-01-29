#!/usr/bin/env python3
"""
Script para testar notificação com TTS.

Este script cria uma notificação de teste e verifica se:
1. O texto foi formatado corretamente para TTS
2. O áudio foi gerado
3. A notificação foi salva no banco com audio_url

Uso:
    python testar_notificacao_tts.py
"""
import os
import sys
from pathlib import Path

# Carregar .env
def load_env_from_file(filepath: str = '.env') -> None:
    if not os.path.exists(filepath):
        return
    try:
        with open(filepath, 'r', encoding='utf-8') as env_file:
            for line in env_file:
                s = line.strip()
                if not s or s.startswith('#') or '=' not in s:
                    continue
                k, v = s.split('=', 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass

load_env_from_file()
sys.path.insert(0, str(Path(__file__).parent))

from services.notificacao_service import NotificacaoService
from utils.tts_text_formatter import formatar_texto_notificacao_para_tts
from db_manager import get_db_connection
from utils.json_helpers import safe_json_loads

def main():
    print("="*60)
    print("🧪 TESTE DE NOTIFICAÇÃO COM TTS")
    print("="*60)
    print()
    
    # Criar notificação de teste
    processo = "VDM.0004/25"
    titulo = "Teste de notificação TTS"
    mensagem = f"{processo} chegou ao destino. Status CE: DESCARREGADA."
    
    print(f"📝 Criando notificação de teste:")
    print(f"   Processo: {processo}")
    print(f"   Título: {titulo}")
    print(f"   Mensagem: {mensagem}")
    print()
    
    # Verificar formatação TTS
    texto_tts = formatar_texto_notificacao_para_tts(
        titulo=titulo,
        mensagem=mensagem,
        processo_referencia=processo
    )
    print(f"🎤 Texto formatado para TTS:")
    print(f"   '{texto_tts}'")
    print()
    
    # Criar notificação
    notif_service = NotificacaoService()
    
    notificacao = {
        'processo_referencia': processo,
        'tipo_notificacao': 'chegada',
        'titulo': titulo,
        'mensagem': mensagem,
        'dados_extras': {}
    }
    
    print("⏳ Salvando notificação (vai gerar TTS automaticamente)...")
    sucesso = notif_service._salvar_notificacao(notificacao)
    
    if not sucesso:
        print("❌ Falha ao salvar notificação")
        return
    
    print("✅ Notificação salva!")
    print()
    
    # Verificar se foi salva com audio_url
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, processo_referencia, titulo, mensagem, dados_extras, criado_em
        FROM notificacoes_processos
        WHERE processo_referencia = ? AND tipo_notificacao = ?
        ORDER BY criado_em DESC
        LIMIT 1
    ''', (processo, 'chegada'))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        dados_extras = safe_json_loads(row[4], default={})
        audio_url = dados_extras.get('audio_url')
        texto_tts_salvo = dados_extras.get('texto_tts', '')
        
        print("📊 Resultado:")
        print(f"   ID da notificação: {row[0]}")
        print(f"   Áudio gerado: {'✅ SIM' if audio_url else '❌ NÃO'}")
        
        if audio_url:
            print(f"   URL do áudio: {audio_url}")
            print(f"   💡 Para ouvir: http://localhost:5001{audio_url}")
        
        if texto_tts_salvo:
            print(f"   Texto TTS salvo: '{texto_tts_salvo[:80]}...'")
        
        print()
        
        if audio_url:
            print("✅ TESTE PASSOU! Notificação criada com TTS funcionando.")
            print()
            print("📋 Próximos passos:")
            print("   1. Acesse: http://localhost:5001/chat-ia")
            print("   2. A notificação deve aparecer automaticamente (polling a cada 30s)")
            print("   3. O áudio deve tocar automaticamente")
            print("   4. Ou teste via API:")
            print(f"      curl -X POST http://localhost:5001/api/teste/notificacao-tts \\")
            print(f"        -H 'Content-Type: application/json' \\")
            print(f"        -d '{{\"processo_referencia\": \"{processo}\"}}'")
        else:
            print("⚠️ TESTE PARCIAL: Notificação criada, mas áudio não foi gerado.")
            print("   Verifique se TTS está habilitado no .env")
    else:
        print("❌ Notificação não encontrada no banco")
    
    print()
    print("="*60)

if __name__ == "__main__":
    main()


