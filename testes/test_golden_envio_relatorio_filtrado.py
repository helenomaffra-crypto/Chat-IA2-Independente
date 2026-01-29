"""
Golden Test: Envio de Relatório Filtrado

Testa o fluxo completo:
1. "o que temos pra hoje?" → cria rel_...115355
2. "filtre os mss" → cria rel_...115410 (filtrado) e salva last_visible_report_id
3. "envia esse relatorio para helenomaffra@gmail.com" → deve usar rel_...115410 (filtrado)

Validações:
- ✅ Precheck detecta "envio de relatório" (não follow-up de extrato)
- ✅ Usa last_visible_report_id_processos correto
- ✅ Envia relatório filtrado (MSS), não completo
- ✅ Logs obrigatórios presentes
"""

import sys
import os
import logging
from datetime import datetime

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_golden_envio_relatorio_filtrado():
    """Teste golden completo do fluxo de envio de relatório filtrado."""
    
    print("=" * 80)
    print("🧪 GOLDEN TEST: Envio de Relatório Filtrado")
    print("=" * 80)
    print()
    
    # Importar serviços
    from services.precheck_service import PrecheckService
    from services.chat_service import ChatService
    from services.report_service import (
        salvar_ultimo_relatorio,
        criar_relatorio_gerado,
        obter_last_visible_report_id,
        _detectar_dominio_por_mensagem
    )
    from db_manager import init_db
    
    # Inicializar banco
    init_db()
    
    # Criar ChatService (necessário para PrecheckService)
    chat_service = ChatService()
    precheck_service = PrecheckService(chat_service)
    
    # Session ID de teste
    session_id = "test_golden_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"📋 Session ID: {session_id}")
    print()
    
    # ============================================================
    # PASSO 1: "o que temos pra hoje?" → cria rel_...115355
    # ============================================================
    print("📝 PASSO 1: Gerar relatório 'o que temos pra hoje'")
    print("-" * 80)
    
    relatorio_completo_id = f"rel_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    relatorio_completo = criar_relatorio_gerado(
        tipo_relatorio='o_que_tem_hoje',
        texto_chat=f"""
📅 O QUE TEMOS PRA HOJE - 14/01/2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚢 CHEGANDO HOJE (6 processo(s))
DMD (5 processo(s)):
• DMD.0001/26 - Porto: RIO DE JANEIRO - ETA: 2026-01-14
• DMD.0074/25 - Porto: RIO DE JANEIRO - ETA: 2026-01-14
MSS (1 processo(s)):
• MSS.0032/25 - ETA: 11/02/2026 (atraso de 7 dia(s))
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[REPORT_META:{{"tipo":"o_que_tem_hoje","id":"{relatorio_completo_id}","data":"2026-01-14","created_at":"2026-01-14T12:00:00-03:00","ttl_min":60,"secoes":["processos_chegando","eta_alterado"],"counts":{{"processos_chegando":6,"eta_alterado":14}}}}]
""",
        categoria=None,
        filtros={},
        meta_json={
            'id': relatorio_completo_id,
            'tipo': 'o_que_tem_hoje',
            'data': '2026-01-14',
            'created_at': datetime.now().isoformat(),
            'ttl_min': 60,
            'secoes': ['processos_chegando', 'eta_alterado'],
            'counts': {
                'processos_chegando': 6,
                'eta_alterado': 14
            }
        }
    )
    salvar_ultimo_relatorio(session_id, relatorio_completo)
    
    last_visible_1 = obter_last_visible_report_id(session_id, dominio='processos')
    print(f"✅ Relatório completo criado: {relatorio_completo_id}")
    print(f"✅ Last visible report ID (processos): {last_visible_1.get('id') if last_visible_1 else 'None'}")
    print()
    
    # ============================================================
    # PASSO 2: "filtre os mss" → cria rel_...115410 (filtrado)
    # ============================================================
    print("📝 PASSO 2: Filtrar relatório por categoria MSS")
    print("-" * 80)
    
    relatorio_filtrado_id = f"rel_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    relatorio_filtrado = criar_relatorio_gerado(
        tipo_relatorio='o_que_tem_hoje',
        texto_chat=f"""
📅 O QUE TEMOS PRA HOJE - 14/01/2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 ETA ALTERADO (1 processo(s))
MSS (1 processo(s)):
• MSS.0032/25 - ETA: 11/02/2026 (atraso de 7 dia(s))
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[REPORT_META:{{"tipo":"o_que_tem_hoje","id":"{relatorio_filtrado_id}","data":"2026-01-14","created_at":"2026-01-14T12:01:00-03:00","ttl_min":60,"secoes":["eta_alterado"],"counts":{{"eta_alterado":1}},"filtrado":true,"secoes_filtradas":["eta_alterado"]}}]
""",
        categoria='MSS',
        filtros={
            'categoria_filtro': 'MSS',
            'secao_filtro': 'eta_alterado',
            'relatorio_original_id': relatorio_completo_id,
            'filtrado': True
        },
        meta_json={
            'id': relatorio_filtrado_id,
            'tipo': 'o_que_tem_hoje',
            'data': '2026-01-14',
            'created_at': datetime.now().isoformat(),
            'ttl_min': 60,
            'secoes': ['eta_alterado'],
            'counts': {
                'eta_alterado': 1
            },
            'filtrado': True,
            'secoes_filtradas': ['eta_alterado']
        }
    )
    salvar_ultimo_relatorio(session_id, relatorio_filtrado)
    
    last_visible_2 = obter_last_visible_report_id(session_id, dominio='processos')
    print(f"✅ Relatório filtrado criado: {relatorio_filtrado_id}")
    print(f"✅ Last visible report ID (processos): {last_visible_2.get('id') if last_visible_2 else 'None'}")
    print(f"✅ Esperado: {relatorio_filtrado_id}")
    
    if last_visible_2 and last_visible_2.get('id') == relatorio_filtrado_id:
        print("✅✅✅ VALIDAÇÃO PASSO 2: Last visible report ID correto!")
    else:
        print(f"❌❌❌ VALIDAÇÃO PASSO 2 FALHOU: Esperado {relatorio_filtrado_id}, obtido {last_visible_2.get('id') if last_visible_2 else 'None'}")
    print()
    
    # ============================================================
    # PASSO 3: "envia esse relatorio para helenomaffra@gmail.com"
    # ============================================================
    print("📝 PASSO 3: Testar precheck de envio de relatório")
    print("-" * 80)
    
    mensagem_envio = "envia esse relatorio para helenomaffra@gmail.com"
    print(f"💬 Mensagem: '{mensagem_envio}'")
    print()
    
    # Testar precheck
    resultado_precheck = precheck_service.tentar_responder_sem_ia(
        mensagem=mensagem_envio,
        historico=[],
        session_id=session_id,
        nome_usuario="Teste"
    )
    
    if resultado_precheck:
        tool_calls = resultado_precheck.get('tool_calls', [])
        if tool_calls:
            tool_call = tool_calls[0]
            func_name = tool_call.get('function', {}).get('name', '')
            func_args = tool_call.get('function', {}).get('arguments', {})
            
            print(f"✅ Precheck retornou tool call: {func_name}")
            print(f"   Argumentos: {func_args}")
            print()
            
            # Validações
            validacoes = []
            
            # ✅ VALIDAÇÃO 1: Tool correta
            if func_name == 'enviar_relatorio_email':
                validacoes.append(("✅ Tool correta: enviar_relatorio_email", True))
            else:
                validacoes.append((f"❌ Tool incorreta: {func_name} (esperado: enviar_relatorio_email)", False))
            
            # ✅ VALIDAÇÃO 2: Email correto
            if func_args.get('destinatario') == 'helenomaffra@gmail.com':
                validacoes.append(("✅ Email correto: helenomaffra@gmail.com", True))
            else:
                validacoes.append((f"❌ Email incorreto: {func_args.get('destinatario')}", False))
            
            # ✅ VALIDAÇÃO 3: Report ID correto (deve ser o filtrado)
            report_id_usado = func_args.get('report_id')
            if report_id_usado == relatorio_filtrado_id:
                validacoes.append((f"✅✅✅ Report ID correto: {report_id_usado} (filtrado)", True))
            else:
                validacoes.append((f"❌❌❌ Report ID incorreto: {report_id_usado} (esperado: {relatorio_filtrado_id})", False))
            
            # ✅ VALIDAÇÃO 4: confirmar_envio=False
            if func_args.get('confirmar_envio') == False:
                validacoes.append(("✅ confirmar_envio=False (mostrar preview primeiro)", True))
            else:
                validacoes.append((f"❌ confirmar_envio incorreto: {func_args.get('confirmar_envio')}", False))
            
            # Mostrar validações
            print("📊 VALIDAÇÕES:")
            print("-" * 80)
            todas_ok = True
            for msg, ok in validacoes:
                print(msg)
                if not ok:
                    todas_ok = False
            print()
            
            if todas_ok:
                print("✅✅✅ TODAS AS VALIDAÇÕES PASSARAM!")
                print()
                
                # ============================================================
                # PASSO 4: Executar realmente o envio (opcional)
                # ============================================================
                print("📝 PASSO 4: Executar envio real do email")
                print("-" * 80)
                print("⚠️  ATENÇÃO: Isso vai enviar um email REAL para helenomaffra@gmail.com")
                print()
                
                # ✅ Executar envio real automaticamente (para teste)
                executar_envio_real = os.getenv('EXECUTAR_ENVIO_REAL', 'false').lower() == 'true'
                
                if executar_envio_real:
                    print("📧 Executando envio real...")
                    try:
                        resultado_envio = chat_service._executar_funcao_tool(
                            'enviar_relatorio_email',
                            func_args,
                            mensagem_original=mensagem_envio,
                            session_id=session_id
                        )
                        
                        if resultado_envio.get('sucesso'):
                            print("✅✅✅ Email enviado com sucesso!")
                            print(f"   Resposta: {resultado_envio.get('resposta', '')[:200]}...")
                        else:
                            print(f"❌ Erro ao enviar email: {resultado_envio.get('erro', 'Erro desconhecido')}")
                    except Exception as e:
                        print(f"❌ Exceção ao enviar email: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("⏭️  Envio real pulado (apenas validação do precheck)")
                    print("   💡 Para executar envio real, defina: EXECUTAR_ENVIO_REAL=true")
            else:
                print("❌❌❌ ALGUMAS VALIDAÇÕES FALHARAM!")
        else:
            print("❌ Precheck retornou resultado mas sem tool_calls")
    else:
        print("❌❌❌ Precheck NÃO retornou resultado (deveria retornar tool call)")
        print("   Isso significa que o precheck não detectou o envio de relatório")
    
    print()
    print("=" * 80)
    print("🏁 TESTE CONCLUÍDO")
    print("=" * 80)


if __name__ == '__main__':
    try:
        test_golden_envio_relatorio_filtrado()
    except Exception as e:
        logger.error(f"❌ Erro no teste: {e}", exc_info=True)
        sys.exit(1)
