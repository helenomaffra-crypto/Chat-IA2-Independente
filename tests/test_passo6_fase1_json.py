"""
Testes para Fase 1 do Passo 6: Verificar que JSON estruturado está sendo retornado.

⚠️ IMPORTANTE: Na Fase 1, a string formatada ainda é usada (comportamento esperado).
Este teste verifica que o JSON também está sendo retornado corretamente.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.agents.processo_agent import ProcessoAgent
from datetime import datetime


def test_obter_dashboard_hoje_retorna_json():
    """Testa que _obter_dashboard_hoje retorna dados_json estruturado."""
    agent = ProcessoAgent()
    
    # Chamar método com argumentos mínimos
    resultado = agent._obter_dashboard_hoje(
        arguments={},
        context={'session_id': 'test_session'}
    )
    
    # Verificar que sucesso é True
    assert resultado.get('sucesso') == True, "Método deve retornar sucesso=True"
    
    # Verificar que resposta (string formatada) existe
    assert 'resposta' in resultado, "Deve retornar 'resposta' (string formatada)"
    assert isinstance(resultado['resposta'], str), "Resposta deve ser string"
    assert len(resultado['resposta']) > 0, "Resposta não deve estar vazia"
    
    # ✅ PASSO 6 - FASE 1: Verificar que dados_json existe
    assert 'dados_json' in resultado, "✅ FASE 1: Deve retornar 'dados_json' estruturado"
    dados_json = resultado['dados_json']
    
    # Verificar estrutura do JSON
    assert isinstance(dados_json, dict), "dados_json deve ser dict"
    assert 'tipo_relatorio' in dados_json, "JSON deve ter 'tipo_relatorio'"
    assert dados_json['tipo_relatorio'] == 'o_que_tem_hoje', "Tipo deve ser 'o_que_tem_hoje'"
    assert 'data' in dados_json, "JSON deve ter 'data'"
    assert 'secoes' in dados_json, "JSON deve ter 'secoes'"
    assert 'resumo' in dados_json, "JSON deve ter 'resumo'"
    
    # Verificar seções
    secoes = dados_json['secoes']
    assert 'processos_chegando' in secoes, "Seções devem ter 'processos_chegando'"
    assert 'processos_prontos' in secoes, "Seções devem ter 'processos_prontos'"
    assert 'pendencias' in secoes, "Seções devem ter 'pendencias'"
    
    # Verificar resumo
    resumo = dados_json['resumo']
    assert 'total_chegando' in resumo, "Resumo deve ter 'total_chegando'"
    assert isinstance(resumo['total_chegando'], int), "total_chegando deve ser int"
    
    print("✅ TESTE PASSOU: _obter_dashboard_hoje retorna dados_json estruturado corretamente")
    print(f"   - Tipo: {dados_json['tipo_relatorio']}")
    print(f"   - Data: {dados_json['data']}")
    print(f"   - Total chegando: {resumo['total_chegando']}")
    print(f"   - Resposta (string) existe: {len(resultado['resposta'])} caracteres")
    
    return True


def test_fechar_dia_retorna_json():
    """Testa que _fechar_dia retorna dados_json estruturado."""
    agent = ProcessoAgent()
    
    # Chamar método com argumentos mínimos
    resultado = agent._fechar_dia(
        arguments={},
        context={'session_id': 'test_session'}
    )
    
    # Verificar que sucesso é True (ou pode ser False se não houver dados)
    # Mas pelo menos deve retornar estrutura correta
    
    # Verificar que resposta (string formatada) existe
    assert 'resposta' in resultado, "Deve retornar 'resposta' (string formatada)"
    assert isinstance(resultado['resposta'], str), "Resposta deve ser string"
    
    # ✅ PASSO 6 - FASE 1: Verificar que dados_json existe
    assert 'dados_json' in resultado, "✅ FASE 1: Deve retornar 'dados_json' estruturado"
    dados_json = resultado['dados_json']
    
    # Verificar estrutura do JSON
    assert isinstance(dados_json, dict), "dados_json deve ser dict"
    assert 'tipo_relatorio' in dados_json, "JSON deve ter 'tipo_relatorio'"
    assert dados_json['tipo_relatorio'] == 'fechamento_dia', "Tipo deve ser 'fechamento_dia'"
    assert 'data' in dados_json, "JSON deve ter 'data'"
    assert 'secoes' in dados_json, "JSON deve ter 'secoes'"
    assert 'resumo' in dados_json, "JSON deve ter 'resumo'"
    
    # Verificar seções
    secoes = dados_json['secoes']
    assert 'processos_chegaram' in secoes, "Seções devem ter 'processos_chegaram'"
    assert 'processos_desembaracados' in secoes, "Seções devem ter 'processos_desembaracados'"
    
    # Verificar resumo
    resumo = dados_json['resumo']
    assert 'total_movimentacoes' in resumo, "Resumo deve ter 'total_movimentacoes'"
    
    print("✅ TESTE PASSOU: _fechar_dia retorna dados_json estruturado corretamente")
    print(f"   - Tipo: {dados_json['tipo_relatorio']}")
    print(f"   - Data: {dados_json['data']}")
    print(f"   - Total movimentações: {resumo['total_movimentacoes']}")
    print(f"   - Resposta (string) existe: {len(resultado['resposta'])} caracteres")
    
    return True


def test_tipo_explicito_no_json():
    """Testa que tipo_relatorio está explícito no JSON (não precisa regex)."""
    agent = ProcessoAgent()
    
    # Testar dashboard
    resultado_dashboard = agent._obter_dashboard_hoje(
        arguments={},
        context={'session_id': 'test'}
    )
    
    tipo_dashboard = resultado_dashboard['dados_json']['tipo_relatorio']
    assert tipo_dashboard == 'o_que_tem_hoje', f"Tipo deve ser 'o_que_tem_hoje', recebido: {tipo_dashboard}"
    
    # Testar fechamento
    resultado_fechamento = agent._fechar_dia(
        arguments={},
        context={'session_id': 'test'}
    )
    
    tipo_fechamento = resultado_fechamento['dados_json']['tipo_relatorio']
    assert tipo_fechamento == 'fechamento_dia', f"Tipo deve ser 'fechamento_dia', recebido: {tipo_fechamento}"
    
    # Verificar que tipos são diferentes
    assert tipo_dashboard != tipo_fechamento, "Tipos devem ser diferentes"
    
    print("✅ TESTE PASSOU: Tipo explícito no JSON (sem necessidade de regex)")
    print(f"   - Dashboard: {tipo_dashboard}")
    print(f"   - Fechamento: {tipo_fechamento}")
    
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("TESTES - PASSO 6 FASE 1: JSON Estruturado")
    print("=" * 60)
    print()
    
    try:
        print("1. Testando _obter_dashboard_hoje retorna JSON...")
        test_obter_dashboard_hoje_retorna_json()
        print()
        
        print("2. Testando _fechar_dia retorna JSON...")
        test_fechar_dia_retorna_json()
        print()
        
        print("3. Testando tipo explícito no JSON...")
        test_tipo_explicito_no_json()
        print()
        
        print("=" * 60)
        print("✅ TODOS OS TESTES PASSARAM!")
        print("=" * 60)
        print()
        print("📝 NOTA: Na Fase 1, a string formatada ainda é usada (comportamento esperado).")
        print("   O JSON está disponível para uso nas próximas fases (Fase 2, 3, 4).")
        
    except AssertionError as e:
        print(f"❌ TESTE FALHOU: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
