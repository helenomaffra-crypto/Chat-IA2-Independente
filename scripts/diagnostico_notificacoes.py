#!/usr/bin/env python3
"""
Script de diagnóstico para verificar o sistema de notificações.
Verifica se o scheduler está rodando, se há notificações no banco, etc.
"""
import sys
import os
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

def verificar_scheduler():
    """Verifica se o scheduler está rodando"""
    print("\n" + "="*60)
    print("1. VERIFICANDO SCHEDULER")
    print("="*60)
    try:
        from services.scheduled_notifications_service import ScheduledNotificationsService
        service = ScheduledNotificationsService()
        if service.scheduler.running:
            print("✅ Scheduler está RODANDO")
            jobs = service.scheduler.get_jobs()
            print(f"   Jobs agendados: {len(jobs)}")
            for job in jobs:
                print(f"   - {job.id}: {job.name} (próxima execução: {job.next_run_time})")
        else:
            print("❌ Scheduler NÃO está rodando")
            print("   ⚠️ Isso explica por que não há notificações!")
            return False
        return True
    except Exception as e:
        print(f"❌ Erro ao verificar scheduler: {e}")
        import traceback
        traceback.print_exc()
        return False

def verificar_notificacoes_banco():
    """Verifica notificações no banco"""
    print("\n" + "="*60)
    print("2. VERIFICANDO NOTIFICAÇÕES NO BANCO")
    print("="*60)
    try:
        from db_manager import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total de notificações
        cursor.execute("SELECT COUNT(*) FROM notificacoes_processos")
        total = cursor.fetchone()[0]
        print(f"   Total de notificações: {total}")
        
        # Notificações não lidas
        cursor.execute("SELECT COUNT(*) FROM notificacoes_processos WHERE lida = 0")
        nao_lidas = cursor.fetchone()[0]
        print(f"   Não lidas: {nao_lidas}")
        
        # Últimas 5 notificações
        cursor.execute("""
            SELECT processo_referencia, tipo_notificacao, titulo, criado_em, lida
            FROM notificacoes_processos
            ORDER BY criado_em DESC
            LIMIT 5
        """)
        ultimas = cursor.fetchall()
        if ultimas:
            print(f"\n   Últimas 5 notificações:")
            for notif in ultimas:
                status = "✅ Lida" if notif[4] else "🔔 Não lida"
                print(f"   - {notif[3]} | {notif[1]} | {notif[2]} | {status}")
        else:
            print("   ⚠️ Nenhuma notificação encontrada no banco")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erro ao verificar banco: {e}")
        import traceback
        traceback.print_exc()
        return False

def verificar_tts():
    """Verifica se TTS está habilitado"""
    print("\n" + "="*60)
    print("3. VERIFICANDO TTS")
    print("="*60)
    try:
        from services.tts_service import TTSService
        tts = TTSService()
        print(f"   TTS habilitado: {tts.enabled}")
        print(f"   API key presente: {bool(tts.api_key)}")
        print(f"   Voz: {tts.voice}")
        print(f"   Model: {tts.model}")
        print(f"   Cache habilitado: {tts.cache_enabled}")
        
        if not tts.enabled:
            print("   ⚠️ TTS está DESABILITADO - notificações não terão áudio")
            tts_enabled_env = os.getenv('OPENAI_TTS_ENABLED', 'não definido')
            print(f"   OPENAI_TTS_ENABLED={tts_enabled_env}")
        
        return tts.enabled
    except Exception as e:
        print(f"❌ Erro ao verificar TTS: {e}")
        import traceback
        traceback.print_exc()
        return False

def verificar_sincronizacao_kanban():
    """Verifica última sincronização do Kanban"""
    print("\n" + "="*60)
    print("4. VERIFICANDO SINCRONIZAÇÃO KANBAN")
    print("="*60)
    try:
        from services.sync_status_repository import SyncStatusRepository
        repo = SyncStatusRepository()
        ultima = repo.obter_ultima_sincronizacao("kanban")
        if ultima:
            print(f"   Última sincronização: {ultima.get('last_success_at')}")
            print(f"   Status: {ultima.get('last_status')}")
            print(f"   Último erro: {ultima.get('last_error') or 'Nenhum'}")
        else:
            print("   ⚠️ Nenhuma sincronização registrada")
        
        return True
    except Exception as e:
        print(f"❌ Erro ao verificar sincronização: {e}")
        import traceback
        traceback.print_exc()
        return False

def verificar_processos_kanban():
    """Verifica processos no Kanban"""
    print("\n" + "="*60)
    print("5. VERIFICANDO PROCESSOS NO KANBAN")
    print("="*60)
    try:
        from db_manager import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM processos_kanban")
        total = cursor.fetchone()[0]
        print(f"   Total de processos: {total}")
        
        # Processos atualizados recentemente
        from datetime import datetime, timedelta
        uma_hora_atras = (datetime.now() - timedelta(hours=1)).isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM processos_kanban 
            WHERE atualizado_em >= ?
        """, (uma_hora_atras,))
        recentes = cursor.fetchone()[0]
        print(f"   Atualizados na última hora: {recentes}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erro ao verificar processos: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🔍 DIAGNÓSTICO DO SISTEMA DE NOTIFICAÇÕES")
    print("="*60)
    
    resultados = {
        'scheduler': verificar_scheduler(),
        'notificacoes': verificar_notificacoes_banco(),
        'tts': verificar_tts(),
        'kanban': verificar_sincronizacao_kanban(),
        'processos': verificar_processos_kanban(),
    }
    
    print("\n" + "="*60)
    print("RESUMO")
    print("="*60)
    for item, ok in resultados.items():
        status = "✅" if ok else "❌"
        print(f"{status} {item}")
    
    if not resultados['scheduler']:
        print("\n⚠️ PROBLEMA CRÍTICO: Scheduler não está rodando!")
        print("   Solução: Reiniciar a aplicação ou verificar logs de inicialização")
    
    if resultados['notificacoes'] and resultados['processos']:
        print("\n💡 DICA: Se não há notificações mas há processos, pode ser que:")
        print("   - Não houve mudanças nos processos (sem mudança = sem notificação)")
        print("   - Processos são antigos/inativos (não geram notificações)")
        print("   - Scheduler não está rodando (notificações agendadas não executam)")

if __name__ == "__main__":
    main()
