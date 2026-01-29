#!/usr/bin/env python3
"""
Script para deletar o Decreto 6.759/2009 do banco de dados.
"""
import sys
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.legislacao_service import LegislacaoService
from db_manager import get_db_connection

def deletar_decreto_6759():
    """Deleta o Decreto 6.759/2009 do banco."""
    
    print("=" * 70)
    print("🗑️  DELETANDO DECRETO 6.759/2009")
    print("=" * 70)
    print()
    
    service = LegislacaoService()
    
    # Buscar o decreto
    ato = service.buscar_ato(
        tipo_ato='Decreto',
        numero='6759',
        ano=2009,
        sigla_orgao=None
    )
    
    if not ato:
        print("❌ Decreto 6.759/2009 não encontrado no banco.")
        print("   Pode já ter sido deletado ou nunca foi importado.")
        return
    
    legislacao_id = ato['id']
    print(f"📋 Decreto encontrado:")
    print(f"   ID: {legislacao_id}")
    print(f"   Tipo: {ato['tipo_ato']} {ato['numero']}/{ato['ano']}")
    if ato.get('sigla_orgao'):
        print(f"   Órgão: {ato['sigla_orgao']}")
    print(f"   Data importação: {ato.get('data_importacao', 'N/A')}")
    print()
    
    # Contar trechos
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM legislacao_trecho WHERE legislacao_id = ?', (legislacao_id,))
    num_trechos = cursor.fetchone()[0]
    print(f"📄 Trechos relacionados: {num_trechos}")
    print()
    
    # Deletar trechos primeiro (foreign key)
    print("🗑️  Deletando trechos...")
    cursor.execute('DELETE FROM legislacao_trecho WHERE legislacao_id = ?', (legislacao_id,))
    trechos_deletados = cursor.rowcount
    
    # Deletar legislação
    print("🗑️  Deletando registro principal...")
    cursor.execute('DELETE FROM legislacao WHERE id = ?', (legislacao_id,))
    legislacao_deletada = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print()
    print("=" * 70)
    if legislacao_deletada > 0:
        print("✅✅✅ DELETADO COM SUCESSO!")
        print("=" * 70)
        print(f"   📊 Registro principal: {legislacao_deletada} deletado")
        print(f"   📄 Trechos relacionados: {trechos_deletados} deletados")
        print()
        print("💡 Agora você pode importar novamente com:")
        print("   \"busque o Decreto 6759/2009\"")
    else:
        print("❌ Nenhum registro foi deletado.")
        print("=" * 70)

if __name__ == '__main__':
    try:
        deletar_decreto_6759()
    except Exception as e:
        print(f"\n❌ Erro ao deletar: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

