#!/usr/bin/env python3
"""
Script para verificar TODAS as tabelas do banco mAIke_assistente
Compara com o planejamento e mostra o que existe e o que falta
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sql_server_adapter import get_sql_adapter

# Lista de tabelas esperadas (baseado no script SQL criar_banco_maike_completo.sql)
# Total: 30 tabelas no script SQL
TABELAS_ESPERADAS = {
    'dbo': [
        # FASE 1: TABELAS CRÍTICAS - COMPLIANCE E RASTREAMENTO (9 tabelas)
        'FORNECEDOR_CLIENTE',
        'MOVIMENTACAO_BANCARIA',
        'PROCESSO_IMPORTACAO',
        'MOVIMENTACAO_BANCARIA_PROCESSO',
        'RASTREAMENTO_RECURSO',
        'DESPESA_PROCESSO',
        'CONCILIACAO_BANCARIA',
        'COMPROVANTE_RECURSO',
        'VALIDACAO_ORIGEM_RECURSO',
        # FASE 2: TABELAS DE ESTRUTURA BASE (4 tabelas)
        'DOCUMENTO_ADUANEIRO',
        'TIMELINE_PROCESSO',
        'SHIPSGO_TRACKING',
        'HISTORICO_DOCUMENTO_ADUANEIRO',
        # FASE 3: TABELAS DE INTEGRAÇÃO E VALIDAÇÃO (4 tabelas)
        'CONSULTA_BILHETADA',
        'CONSULTA_BILHETADA_PENDENTE',
        'VALIDACAO_DADOS_OFICIAIS',
        'VERIFICACAO_AUTOMATICA',
        # Tabelas de Despesas (criadas separadamente)
        'LANCAMENTO_TIPO_DESPESA',
        'TIPO_DESPESA',
        # Tabelas ainda não implementadas no script SQL
        'IMPOSTO_IMPORTACAO',  # ⚠️ Ainda não implementado (ver docs/ESTRATEGIA_POPULACAO_BANCO_MAIKE.md)
        'VALOR_MERCADORIA',    # ⚠️ Ainda não implementado (ver docs/ESTRATEGIA_POPULACAO_BANCO_MAIKE.md)
    ],
    'comunicacao': [
        # FASE 4: TABELAS DE COMUNICAÇÃO (3 tabelas)
        'EMAIL_ENVIADO',
        'EMAIL_AGENDADO',
        'WHATSAPP_MENSAGEM',
    ],
    'ia': [
        # FASE 5: TABELAS DE IA E APRENDIZADO (4 tabelas)
        'CONVERSA_CHAT',
        'REGRA_APRENDIDA',
        'CONTEXTO_SESSAO',
        'CONSULTA_SALVA',
    ],
    'legislacao': [
        # FASE 6: TABELAS DE LEGISLAÇÃO (3 tabelas)
        'LEGISLACAO_IMPORTADA',
        'LEGISLACAO_VETORIZACAO',
        'LEGISLACAO_CHUNK',
    ],
    'auditoria': [
        # FASE 7: TABELAS DE AUDITORIA (3 tabelas)
        'LOG_SINCRONIZACAO',
        'LOG_CONSULTA_API',
        'LOG_ERRO',
    ],
}

def verificar_todas_tabelas():
    """Verifica todas as tabelas do banco mAIke_assistente"""
    
    print("=" * 80)
    print("🔍 VERIFICAÇÃO COMPLETA - BANCO mAIke_assistente")
    print("=" * 80)
    
    sql_adapter = get_sql_adapter()
    
    # Verificar se banco existe
    print("\n1️⃣ Verificando se banco mAIke_assistente existe...")
    check_db_query = """
        SELECT name FROM sys.databases WHERE name = 'mAIke_assistente'
    """
    
    result = sql_adapter.execute_query(check_db_query, database='master')
    if result.get('success') and result.get('data'):
        if result['data']:
            print("✅ Banco mAIke_assistente existe")
        else:
            print("❌ Banco mAIke_assistente NÃO existe")
            print("💡 Execute o script SQL para criar o banco")
            return
    else:
        print(f"⚠️ Erro ao verificar banco: {result.get('error', 'Erro desconhecido')}")
        print("💡 Pode estar fora da rede ou banco não existe")
        return
    
    # Buscar todas as tabelas existentes
    print("\n2️⃣ Buscando todas as tabelas existentes...")
    query_tabelas = """
        SELECT 
            TABLE_SCHEMA,
            TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    
    result = sql_adapter.execute_query(query_tabelas, database='mAIke_assistente')
    
    tabelas_existentes = {}
    if result.get('success') and result.get('data'):
        for row in result['data']:
            schema = row.get('TABLE_SCHEMA', 'dbo')
            tabela = row.get('TABLE_NAME', '')
            if schema not in tabelas_existentes:
                tabelas_existentes[schema] = []
            tabelas_existentes[schema].append(tabela)
        
        print(f"✅ Encontradas {sum(len(t) for t in tabelas_existentes.values())} tabela(s)")
    else:
        print(f"❌ Erro ao buscar tabelas: {result.get('error', 'Erro desconhecido')}")
        return
    
    # Comparar com esperado
    print("\n3️⃣ Comparando com planejamento...")
    print("\n" + "=" * 80)
    print("📊 RESUMO POR SCHEMA")
    print("=" * 80)
    
    total_existentes = 0
    total_faltantes = 0
    total_nao_planejadas = 0
    
    for schema, tabelas_esperadas in TABELAS_ESPERADAS.items():
        print(f"\n📁 Schema: {schema}")
        print("-" * 80)
        
        tabelas_schema = tabelas_existentes.get(schema, [])
        
        # Tabelas existentes
        print(f"\n✅ Tabelas EXISTENTES ({len([t for t in tabelas_esperadas if t in tabelas_schema])}):")
        for tabela in tabelas_esperadas:
            if tabela in tabelas_schema:
                marcador = "✅" if tabela not in ['IMPOSTO_IMPORTACAO', 'VALOR_MERCADORIA'] else "⚠️"
                print(f"   {marcador} {tabela}")
                total_existentes += 1
        
        # Tabelas faltantes
        print(f"\n❌ Tabelas FALTANTES ({len([t for t in tabelas_esperadas if t not in tabelas_schema])}):")
        for tabela in tabelas_esperadas:
            if tabela not in tabelas_schema:
                marcador = "⚠️" if tabela in ['IMPOSTO_IMPORTACAO', 'VALOR_MERCADORIA'] else "❌"
                print(f"   {marcador} {tabela}")
                total_faltantes += 1
        
        # Tabelas não planejadas (existem mas não estão no planejamento)
        tabelas_nao_planejadas = [t for t in tabelas_schema if t not in tabelas_esperadas]
        if tabelas_nao_planejadas:
            print(f"\n⚠️ Tabelas NÃO PLANEJADAS ({len(tabelas_nao_planejadas)}):")
            for tabela in tabelas_nao_planejadas:
                print(f"   ⚠️ {tabela}")
                total_nao_planejadas += 1
    
    # Resumo geral
    print("\n" + "=" * 80)
    print("📊 RESUMO GERAL")
    print("=" * 80)
    print(f"✅ Tabelas existentes: {total_existentes}")
    print(f"❌ Tabelas faltantes: {total_faltantes}")
    print(f"⚠️ Tabelas não planejadas: {total_nao_planejadas}")
    
    # Tabelas críticas
    print("\n" + "=" * 80)
    print("🎯 TABELAS CRÍTICAS")
    print("=" * 80)
    
    tabelas_criticas = [
        ('PROCESSO_IMPORTACAO', 'dbo'),
        ('DOCUMENTO_ADUANEIRO', 'dbo'),
        ('HISTORICO_DOCUMENTO_ADUANEIRO', 'dbo'),
        ('LANCAMENTO_TIPO_DESPESA', 'dbo'),
        ('MOVIMENTACAO_BANCARIA', 'dbo'),
    ]
    
    for tabela, schema in tabelas_criticas:
        existe = tabela in tabelas_existentes.get(schema, [])
        status = "✅" if existe else "❌"
        print(f"{status} {schema}.{tabela}")
    
    # Tabelas ainda não implementadas
    print("\n" + "=" * 80)
    print("⚠️ TABELAS AINDA NÃO IMPLEMENTADAS (planejadas mas não criadas)")
    print("=" * 80)
    
    tabelas_nao_implementadas = [
        ('IMPOSTO_IMPORTACAO', 'dbo'),
        ('VALOR_MERCADORIA', 'dbo'),
    ]
    
    for tabela, schema in tabelas_nao_implementadas:
        existe = tabela in tabelas_existentes.get(schema, [])
        status = "✅" if existe else "⚠️"
        print(f"{status} {schema}.{tabela} - {'Criada!' if existe else 'Ainda não implementada (ver docs/ESTRATEGIA_POPULACAO_BANCO_MAIKE.md)'}")
    
    print("\n" + "=" * 80)
    print("✅ Verificação concluída")
    print("=" * 80)
    
    # Recomendações
    if total_faltantes > 0:
        print("\n💡 RECOMENDAÇÕES:")
        print("   1. Execute o script SQL: scripts/criar_banco_maike_completo.sql")
        print("   2. Verifique se todas as tabelas críticas foram criadas")
        print("   3. Execute este script novamente para validar")

if __name__ == '__main__':
    verificar_todas_tabelas()

