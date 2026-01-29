#!/usr/bin/env python3
"""
Script de teste para verificar se a funcionalidade de sugestões de vinculação bancária está funcionando.

Uso:
    python3 scripts/testar_sugestoes_vinculacao.py
"""

import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import get_db_connection, init_db
from services.banco_auto_vinculacao_service import BancoAutoVinculacaoService

def testar_tabela():
    """Testa se a tabela existe e tem a estrutura correta."""
    print("🔍 Testando estrutura da tabela...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se a tabela existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='sugestoes_vinculacao_bancaria'
        """)
        row = cursor.fetchone()
        
        if not row:
            print("❌ Tabela 'sugestoes_vinculacao_bancaria' não encontrada!")
            print("   Tentando criar...")
            init_db()
            print("   ✅ init_db() executado. Verifique novamente.")
            conn.close()
            return False
        
        print("✅ Tabela 'sugestoes_vinculacao_bancaria' existe")
        
        # Verificar estrutura
        cursor.execute("PRAGMA table_info(sugestoes_vinculacao_bancaria)")
        colunas = cursor.fetchall()
        
        colunas_esperadas = [
            'id', 'processo_referencia', 'tipo_documento', 'numero_documento',
            'data_desembaraco', 'total_impostos', 'id_movimentacao_sugerida',
            'score_confianca', 'status', 'criado_em', 'aplicado_em', 'observacoes'
        ]
        
        colunas_encontradas = [col[1] for col in colunas]
        
        print(f"   Colunas encontradas: {len(colunas_encontradas)}")
        for col in colunas_esperadas:
            if col in colunas_encontradas:
                print(f"   ✅ {col}")
            else:
                print(f"   ❌ {col} - FALTANDO!")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar tabela: {e}")
        import traceback
        traceback.print_exc()
        return False


def testar_servico():
    """Testa se o serviço pode ser importado e inicializado."""
    print("\n🔍 Testando serviço BancoAutoVinculacaoService...")
    
    try:
        service = BancoAutoVinculacaoService()
        print("✅ Serviço inicializado com sucesso")
        
        # Testar listagem
        resultado = service.listar_sugestoes_pendentes(limite=10)
        
        if resultado.get('sucesso'):
            print(f"✅ Listagem funcionando: {resultado.get('total', 0)} sugestão(ões) encontrada(s)")
            return True
        else:
            print(f"❌ Erro ao listar: {resultado.get('erro', 'Erro desconhecido')}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar serviço: {e}")
        import traceback
        traceback.print_exc()
        return False


def testar_criar_sugestao_teste():
    """Cria uma sugestão de teste."""
    print("\n🔍 Criando sugestão de teste...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se já existe sugestão de teste
        cursor.execute("""
            SELECT id FROM sugestoes_vinculacao_bancaria
            WHERE processo_referencia = 'TEST.0001/26'
        """)
        
        if cursor.fetchone():
            print("ℹ️ Sugestão de teste já existe (pulando criação)")
            conn.close()
            return True
        
        # Criar sugestão de teste
        # ✅ NOTA: id_movimentacao_sugerida pode ser NULL ou um ID fictício
        # A validação real será feita na aplicação quando a sugestão for aplicada
        cursor.execute("""
            INSERT INTO sugestoes_vinculacao_bancaria (
                processo_referencia,
                tipo_documento,
                numero_documento,
                data_desembaraco,
                total_impostos,
                id_movimentacao_sugerida,
                score_confianca,
                status,
                observacoes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pendente', ?)
        """, (
            'TEST.0001/26',
            'DI',
            '123456789',
            '2026-01-23',
            13337.88,
            777,  # ID fictício (será validado na aplicação quando aplicar)
            95,
            'Sugestão criada automaticamente pelo script de teste'
        ))
        
        sugestao_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ Sugestão de teste criada (ID: {sugestao_id})")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar sugestão de teste: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executa todos os testes."""
    print("=" * 60)
    print("🧪 TESTE DE SUGESTÕES DE VINCULAÇÃO BANCÁRIA")
    print("=" * 60)
    
    resultados = []
    
    # Teste 1: Tabela
    resultados.append(("Tabela", testar_tabela()))
    
    # Teste 2: Serviço
    resultados.append(("Serviço", testar_servico()))
    
    # Teste 3: Criar sugestão de teste
    resultados.append(("Criar Sugestão Teste", testar_criar_sugestao_teste()))
    
    # Resumo
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{status} - {nome}")
    
    todos_passaram = all(r[1] for r in resultados)
    
    if todos_passaram:
        print("\n✅ TODOS OS TESTES PASSARAM!")
        print("\n💡 Próximos passos:")
        print("   1. Acesse o chat: http://localhost:5001")
        print("   2. Digite: 'maike quero conciliar banco'")
        print("   3. Clique na aba '💡 Sugestões'")
        print("   4. Você deve ver a sugestão de teste criada")
    else:
        print("\n❌ ALGUNS TESTES FALHARAM")
        print("   Verifique os erros acima e corrija antes de continuar")
    
    return 0 if todos_passaram else 1


if __name__ == '__main__':
    sys.exit(main())
