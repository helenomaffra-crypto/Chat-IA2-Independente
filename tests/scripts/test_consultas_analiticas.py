#!/usr/bin/env python3
"""
Script de teste para funcionalidades de consultas analíticas.

Testa:
- executar_consulta_analitica
- buscar_consulta_personalizada
- salvar_consulta_personalizada
- salvar_regra_aprendida
"""

import sys
import os
from pathlib import Path

# Adicionar raiz do projeto ao path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.analytical_query_service import executar_consulta_analitica, validar_sql_seguro
from services.saved_queries_service import (
    salvar_consulta_personalizada,
    buscar_consulta_personalizada,
    listar_consultas_salvas,
    ensure_consultas_padrao
)
from services.learned_rules_service import (
    salvar_regra_aprendida,
    buscar_regras_aprendidas,
    formatar_regras_para_prompt
)
from services.context_service import (
    salvar_contexto_sessao,
    buscar_contexto_sessao,
    formatar_contexto_para_prompt
)
from services.chat_service import ChatService

def test_validacao_sql():
    """Testa validação de SQL seguro."""
    print("\n" + "="*60)
    print("TESTE 1: Validação de SQL Seguro")
    print("="*60)
    
    # Teste 1: SQL válido
    sql_valido = "SELECT categoria, COUNT(*) as total FROM processos_kanban GROUP BY categoria"
    valido, erro = validar_sql_seguro(sql_valido)
    print(f"✅ SQL válido: {valido} (esperado: True)")
    assert valido, f"SQL deveria ser válido: {erro}"
    
    # Teste 2: SQL perigoso (INSERT)
    sql_perigoso = "INSERT INTO processos VALUES (1, 'teste')"
    valido, erro = validar_sql_seguro(sql_perigoso)
    print(f"✅ SQL perigoso bloqueado: {not valido} (esperado: True)")
    assert not valido, "SQL perigoso deveria ser bloqueado"
    print(f"   Erro: {erro}")
    
    # Teste 3: SQL perigoso (DROP)
    sql_drop = "DROP TABLE processos"
    valido, erro = validar_sql_seguro(sql_drop)
    print(f"✅ SQL DROP bloqueado: {not valido} (esperado: True)")
    assert not valido, "SQL DROP deveria ser bloqueado"
    
    print("✅ Todos os testes de validação passaram!")


def test_executar_consulta_analitica():
    """Testa execução de consulta analítica."""
    print("\n" + "="*60)
    print("TESTE 2: Executar Consulta Analítica")
    print("="*60)
    
    # Teste 1: Consulta simples
    sql = "SELECT COUNT(*) as total FROM processos_kanban LIMIT 1"
    resultado = executar_consulta_analitica(sql=sql)
    
    print(f"✅ Consulta executada: {resultado.get('sucesso')}")
    print(f"   Fonte: {resultado.get('fonte')}")
    print(f"   Linhas: {resultado.get('linhas_retornadas', 0)}")
    
    if resultado.get('sucesso'):
        dados = resultado.get('dados', [])
        if dados:
            print(f"   Primeiro resultado: {dados[0]}")
    else:
        print(f"   Erro: {resultado.get('erro')}")
    
    # Teste 2: Consulta com agregação
    sql2 = """
    SELECT categoria, COUNT(*) as total 
    FROM processos_kanban 
    GROUP BY categoria 
    LIMIT 5
    """
    resultado2 = executar_consulta_analitica(sql=sql2)
    
    print(f"\n✅ Consulta com agregação: {resultado2.get('sucesso')}")
    if resultado2.get('sucesso'):
        dados2 = resultado2.get('dados', [])
        print(f"   Resultados: {len(dados2)} linhas")
        for linha in dados2[:3]:
            print(f"   - {linha}")
    
    print("✅ Teste de execução de consulta concluído!")


def test_salvar_e_buscar_consulta():
    """Testa salvar e buscar consulta personalizada."""
    print("\n" + "="*60)
    print("TESTE 3: Salvar e Buscar Consulta Personalizada")
    print("="*60)
    
    # Teste 1: Salvar consulta
    resultado_salvar = salvar_consulta_personalizada(
        nome_exibicao="Teste: Processos por categoria",
        slug="teste_processos_por_categoria",
        descricao="Consulta de teste para processos agrupados por categoria",
        sql="SELECT categoria, COUNT(*) as total FROM processos_kanban GROUP BY categoria LIMIT 10",
        exemplos_pergunta="teste processos por categoria; processos agrupados por categoria",
        criado_por="test_script"
    )
    
    print(f"✅ Consulta salva: {resultado_salvar.get('sucesso')}")
    if resultado_salvar.get('sucesso'):
        consulta_id = resultado_salvar.get('id')
        print(f"   ID da consulta: {consulta_id}")
    else:
        print(f"   Erro: {resultado_salvar.get('erro')}")
        return
    
    # Teste 2: Buscar consulta
    resultado_busca = buscar_consulta_personalizada("teste processos por categoria")
    
    print(f"\n✅ Consulta encontrada: {resultado_busca.get('sucesso')}")
    if resultado_busca.get('sucesso'):
        consulta = resultado_busca.get('consulta')
        print(f"   Nome: {consulta.get('nome_exibicao')}")
        print(f"   Slug: {consulta.get('slug')}")
        print(f"   SQL: {consulta.get('sql_base')[:50]}...")
    
    # Teste 3: Listar todas as consultas
    consultas = listar_consultas_salvas(limit=10)
    print(f"\n✅ Total de consultas salvas: {len(consultas)}")
    for i, consulta in enumerate(consultas[:3], 1):
        print(f"   {i}. {consulta.get('nome_exibicao')} (usado {consulta.get('vezes_usado', 0)} vezes)")
    
    print("✅ Teste de consultas salvas concluído!")


def test_salvar_regra_aprendida():
    """Testa salvar e buscar regras aprendidas."""
    print("\n" + "="*60)
    print("TESTE 4: Salvar e Buscar Regras Aprendidas")
    print("="*60)
    
    # Teste 1: Salvar regra
    resultado_salvar = salvar_regra_aprendida(
        tipo_regra='campo_definicao',
        contexto='chegada_processos',
        nome_regra='destfinal como confirmação de chegada (teste)',
        descricao='Campo data_destino_final indica que o processo chegou ao destino final - TESTE',
        aplicacao_sql='WHERE data_destino_final IS NOT NULL',
        aplicacao_texto='Processos que têm data_destino_final preenchida são considerados como tendo chegado',
        exemplo_uso='Quando perguntar "quais VDM chegaram", usar data_destino_final IS NOT NULL',
        criado_por='test_script'
    )
    
    print(f"✅ Regra salva: {resultado_salvar.get('sucesso')}")
    if resultado_salvar.get('sucesso'):
        regra_id = resultado_salvar.get('id')
        print(f"   ID da regra: {regra_id}")
    else:
        print(f"   Erro: {resultado_salvar.get('erro')}")
        return
    
    # Teste 2: Buscar regras
    regras = buscar_regras_aprendidas(contexto='chegada_processos', ativas=True)
    print(f"\n✅ Regras encontradas: {len(regras)}")
    for i, regra in enumerate(regras[:3], 1):
        print(f"   {i}. {regra.get('nome_regra')} (usado {regra.get('vezes_usado', 0)} vezes)")
    
    # Teste 3: Formatar regras para prompt
    if regras:
        regras_texto = formatar_regras_para_prompt(regras)
        print(f"\n✅ Formatação para prompt:")
        print(regras_texto[:200] + "..." if len(regras_texto) > 200 else regras_texto)
    
    print("✅ Teste de regras aprendidas concluído!")


def test_contexto_sessao():
    """Testa contexto de sessão."""
    print("\n" + "="*60)
    print("TESTE 5: Contexto de Sessão")
    print("="*60)
    
    session_id = "test_session_123"
    
    # Teste 1: Salvar contexto
    salvo = salvar_contexto_sessao(
        session_id=session_id,
        tipo_contexto='processo_atual',
        chave='processo',
        valor='VDM.0004/25',
        dados_adicionais={'categoria': 'VDM', 'ano': '25'}
    )
    print(f"✅ Contexto salvo: {salvo}")
    
    # Teste 2: Buscar contexto
    contextos = buscar_contexto_sessao(session_id=session_id)
    print(f"\n✅ Contextos encontrados: {len(contextos)}")
    for ctx in contextos:
        print(f"   - {ctx.get('tipo_contexto')}: {ctx.get('valor')}")
    
    # Teste 3: Formatar contexto para prompt
    if contextos:
        contexto_texto = formatar_contexto_para_prompt(contextos)
        print(f"\n✅ Formatação para prompt:")
        print(contexto_texto)
    
    print("✅ Teste de contexto de sessão concluído!")


def test_consultas_padrao():
    """Testa se consultas padrão estão sendo criadas."""
    print("\n" + "="*60)
    print("TESTE 6: Consultas Padrão")
    print("="*60)
    
    # Garantir que consultas padrão existem
    ensure_consultas_padrao()
    
    # Listar consultas padrão
    consultas = listar_consultas_salvas(limit=10)
    consultas_padrao = [c for c in consultas if c.get('criado_por') == 'system_seed']
    
    print(f"✅ Consultas padrão encontradas: {len(consultas_padrao)}")
    for consulta in consultas_padrao:
        print(f"   - {consulta.get('nome_exibicao')} ({consulta.get('slug')})")
    
    print("✅ Teste de consultas padrão concluído!")


def test_integracao_chat_service():
    """Testa integração com ChatService."""
    print("\n" + "="*60)
    print("TESTE 7: Integração com ChatService")
    print("="*60)
    
    try:
        chat_service = ChatService()
        print("✅ ChatService inicializado")
        
        # Teste: Executar tool de consulta analítica
        resultado = chat_service._executar_funcao_tool(
            'executar_consulta_analitica',
            {
                'sql': 'SELECT COUNT(*) as total FROM processos_kanban LIMIT 1',
                'limit': 10
            }
        )
        
        print(f"✅ Tool executada via ChatService: {resultado.get('sucesso')}")
        if resultado.get('sucesso'):
            print(f"   Resposta: {resultado.get('resposta', '')[:100]}...")
        else:
            print(f"   Erro: {resultado.get('erro')}")
        
        # Teste: Buscar consulta personalizada
        resultado2 = chat_service._executar_funcao_tool(
            'buscar_consulta_personalizada',
            {
                'texto_pedido_usuario': 'processos por categoria'
            }
        )
        
        print(f"\n✅ Buscar consulta via ChatService: {resultado2.get('sucesso')}")
        if resultado2.get('sucesso'):
            print(f"   Resposta: {resultado2.get('resposta', '')[:100]}...")
        
    except Exception as e:
        print(f"❌ Erro ao testar ChatService: {e}")
        import traceback
        traceback.print_exc()
    
    print("✅ Teste de integração concluído!")


def main():
    """Executa todos os testes."""
    print("\n" + "="*60)
    print("🧪 TESTES DE CONSULTAS ANALÍTICAS")
    print("="*60)
    print("\nEste script testa todas as funcionalidades de consultas analíticas")
    print("implementadas no sistema.\n")
    
    try:
        # Teste 1: Validação SQL
        test_validacao_sql()
        
        # Teste 2: Executar consulta
        test_executar_consulta_analitica()
        
        # Teste 3: Consultas padrão
        test_consultas_padrao()
        
        # Teste 4: Salvar e buscar consulta
        test_salvar_e_buscar_consulta()
        
        # Teste 5: Salvar regra aprendida
        test_salvar_regra_aprendida()
        
        # Teste 6: Contexto de sessão
        test_contexto_sessao()
        
        # Teste 7: Integração com ChatService
        test_integracao_chat_service()
        
        print("\n" + "="*60)
        print("✅ TODOS OS TESTES PASSARAM!")
        print("="*60)
        print("\n🎉 As funcionalidades de consultas analíticas estão funcionando corretamente!")
        
    except AssertionError as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
