#!/usr/bin/env python3
"""
Script para corrigir a tabela sugestoes_vinculacao_bancaria removendo a foreign key.

A foreign key não pode existir porque MOVIMENTACAO_BANCARIA está no SQL Server,
não no SQLite.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import get_db_connection

def corrigir_tabela():
    """Recria a tabela sem foreign key."""
    print("🔧 Corrigindo tabela sugestoes_vinculacao_bancaria...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Fazer backup dos dados existentes
        cursor.execute("SELECT * FROM sugestoes_vinculacao_bancaria")
        dados = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description] if cursor.description else []
        
        print(f"   📦 Backup: {len(dados)} registro(s) encontrado(s)")
        
        # 2. Dropar índices
        print("   🗑️ Removendo índices...")
        try:
            cursor.execute("DROP INDEX IF EXISTS idx_sugestoes_processo")
            cursor.execute("DROP INDEX IF EXISTS idx_sugestoes_status")
            cursor.execute("DROP INDEX IF EXISTS idx_sugestoes_movimentacao")
        except:
            pass
        
        # 3. Dropar tabela
        print("   🗑️ Removendo tabela antiga...")
        cursor.execute("DROP TABLE IF EXISTS sugestoes_vinculacao_bancaria")
        
        # 4. Recriar tabela sem foreign key
        print("   ✅ Recriando tabela sem foreign key...")
        from services.sugestoes_vinculacao_schema import criar_tabela_sugestoes_vinculacao
        criar_tabela_sugestoes_vinculacao(cursor)
        
        # 5. Restaurar dados (se houver)
        if dados and colunas:
            print(f"   📥 Restaurando {len(dados)} registro(s)...")
            for row in dados:
                row_dict = dict(zip(colunas, row))
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
                        criado_em,
                        aplicado_em,
                        observacoes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row_dict.get('processo_referencia'),
                    row_dict.get('tipo_documento'),
                    row_dict.get('numero_documento'),
                    row_dict.get('data_desembaraco'),
                    row_dict.get('total_impostos'),
                    row_dict.get('id_movimentacao_sugerida'),
                    row_dict.get('score_confianca'),
                    row_dict.get('status'),
                    row_dict.get('criado_em'),
                    row_dict.get('aplicado_em'),
                    row_dict.get('observacoes')
                ))
        
        conn.commit()
        conn.close()
        
        print("✅ Tabela corrigida com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao corrigir tabela: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if corrigir_tabela():
        print("\n✅ Correção concluída! Agora você pode executar o script de teste novamente.")
        sys.exit(0)
    else:
        print("\n❌ Correção falhou!")
        sys.exit(1)
