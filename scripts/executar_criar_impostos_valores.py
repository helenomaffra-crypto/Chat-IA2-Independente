#!/usr/bin/env python3
"""
Script para criar tabelas IMPOSTO_IMPORTACAO e VALOR_MERCADORIA no SQL Server
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from utils.sql_server_adapter import get_sql_adapter

def criar_tabelas_impostos_valores():
    """Cria as tabelas IMPOSTO_IMPORTACAO e VALOR_MERCADORIA"""
    print("=" * 80)
    print("🔨 CRIAÇÃO DE TABELAS - IMPOSTOS E VALORES")
    print("=" * 80)
    
    adapter = get_sql_adapter()
    if not adapter:
        print("❌ SQL Server adapter não disponível")
        return False
    
    # Ler script SQL
    script_path = os.path.join(os.path.dirname(__file__), 'criar_tabelas_impostos_valores.sql')
    
    if not os.path.exists(script_path):
        print(f"❌ Script SQL não encontrado: {script_path}")
        return False
    
    with open(script_path, 'r', encoding='utf-8') as f:
        script_sql = f.read()
    
    print(f"\n📄 Script SQL carregado: {script_path}")
    print(f"📊 Tamanho: {len(script_sql)} caracteres\n")
    
    # Dividir script em comandos (separados por GO)
    comandos = [cmd.strip() for cmd in script_sql.split('GO') if cmd.strip()]
    
    print(f"🔍 Encontrados {len(comandos)} comando(s) SQL\n")
    
    sucesso = 0
    erros = 0
    
    for i, comando in enumerate(comandos, 1):
        # Pular comandos USE (não funcionam via adapter)
        if comando.upper().startswith('USE'):
            print(f"⏭️  [{i}/{len(comandos)}] Pulando comando USE...")
            continue
        
        # Pular comandos PRINT (não funcionam via adapter)
        if comando.upper().startswith('PRINT'):
            print(f"ℹ️  [{i}/{len(comandos)}] {comando[:100]}...")
            continue
        
        print(f"🔨 [{i}/{len(comandos)}] Executando comando SQL...")
        
        try:
            result = adapter.execute_query(comando, database=adapter.database)
            
            if result and result.get('success'):
                sucesso += 1
                print(f"   ✅ Sucesso")
            else:
                erros += 1
                error_msg = result.get('error', 'Erro desconhecido') if result else 'Sem resposta'
                print(f"   ❌ Erro: {error_msg}")
                
        except Exception as e:
            erros += 1
            print(f"   ❌ Exceção: {str(e)}")
    
    print("\n" + "=" * 80)
    print("📊 RESUMO:")
    print(f"   ✅ Sucessos: {sucesso}")
    print(f"   ❌ Erros: {erros}")
    print("=" * 80)
    
    # Verificar se tabelas foram criadas
    print("\n🔍 Verificando tabelas criadas...\n")
    
    tabelas = ['IMPOSTO_IMPORTACAO', 'VALOR_MERCADORIA']
    
    for tabela in tabelas:
        query_check = f"""
            SELECT COUNT(*) as total
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = '{tabela}'
        """
        
        result = adapter.execute_query(query_check, database=adapter.database)
        
        if result and result.get('success'):
            data = result.get('data', [])
            if data and data[0].get('total', 0) > 0:
                print(f"✅ Tabela {tabela} existe")
                
                # Contar registros
                query_count = f"SELECT COUNT(*) as total FROM {tabela}"
                result_count = adapter.execute_query(query_count, database=adapter.database)
                if result_count and result_count.get('success'):
                    count_data = result_count.get('data', [])
                    if count_data:
                        total = count_data[0].get('total', 0)
                        print(f"   📊 Registros: {total}")
            else:
                print(f"❌ Tabela {tabela} NÃO existe")
        else:
            print(f"⚠️  Erro ao verificar tabela {tabela}")
    
    print("\n" + "=" * 80)
    
    if erros == 0:
        print("✅✅✅ SUCESSO! Todas as tabelas foram criadas!")
        print("=" * 80)
        return True
    else:
        print("⚠️  Alguns erros ocorreram. Verifique os logs acima.")
        print("=" * 80)
        return False

if __name__ == '__main__':
    criar_tabelas_impostos_valores()


