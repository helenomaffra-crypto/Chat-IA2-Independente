"""
Script para corrigir datas dos lançamentos do Santander que foram salvos com data incorreta (07/01/2026 em vez de 08/01/2026).

Este script:
1. Identifica lançamentos do Santander com data 07/01/2026
2. Verifica se há lançamentos correspondentes com os mesmos valores e descrições do dia 08/01/2026
3. Atualiza a data para 08/01/2026 se os valores corresponderem
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Carregar .env
from dotenv import load_dotenv
load_dotenv(root_dir / '.env')

from utils.sql_server_adapter import get_sql_adapter

def corrigir_datas_santander():
    """Corrige datas dos lançamentos do Santander salvos incorretamente."""
    adapter = get_sql_adapter()
    if not adapter:
        print("❌ SQL Server não disponível")
        return
    
    database = 'mAIke_assistente'
    
    # Lista de lançamentos do dia 08/01/2026 do chat (valores conhecidos)
    lancamentos_dia_08 = [
        {'descricao': 'PIX ENVIADO - 4pl Apoio Administrativo', 'valor': 7880.48, 'sinal': 'D'},
        {'descricao': 'PIX ENVIADO - MASSY DO BRASIL COMERCIO', 'valor': 272902.70, 'sinal': 'D'},
        {'descricao': 'PIX ENVIADO - RIO BRASIL TERMINAL', 'valor': 17465.73, 'sinal': 'D'},
        {'descricao': 'PIX RECEBIDO - 02378779000109', 'valor': 498.00, 'sinal': 'C'},
        {'descricao': 'PIX RECEBIDO - 55046509000167', 'valor': 81166.63, 'sinal': 'C'},
        {'descricao': 'PIX RECEBIDO - 55046509000167', 'valor': 58471.06, 'sinal': 'C'},
        {'descricao': 'PIX RECEBIDO - 55046509000167', 'valor': 69009.44, 'sinal': 'C'},
        {'descricao': 'PIX RECEBIDO - 55046509000167', 'valor': 64255.57, 'sinal': 'C'},
        {'descricao': 'PIX ENVIADO - 4pl Apoio Administrativo', 'valor': 7885.55, 'sinal': 'D'},
        {'descricao': 'PIX ENVIADO - 4pl Apoio Administrativo', 'valor': 786.22, 'sinal': 'D'},
        {'descricao': 'PIX ENVIADO - BARDAM MEDIA', 'valor': 5989.90, 'sinal': 'D'},
        {'descricao': 'TRANSF VALOR P/ CONTA DIF TITULAR - 08895016700', 'valor': 2000.00, 'sinal': 'D'},
        {'descricao': 'PAGAMENTO DE BOLETO OUTROS BANCOS - JM TRANSPORTES E LOGISTIC', 'valor': 2800.00, 'sinal': 'D'},
        {'descricao': 'PAGAMENTO DE BOLETO - MSC MEDITERRANEAN SHIPPIN', 'valor': 8202.79, 'sinal': 'D'},
        {'descricao': 'PIX ENVIADO - FUTURO FERTIL', 'valor': 573.00, 'sinal': 'D'},
    ]
    
    print("🔍 Buscando lançamentos do Santander com data 07/01/2026 que correspondem ao dia 08/01/2026...")
    
    total_corrigidos = 0
    
    for lancamento_ref in lancamentos_dia_08:
        descricao_ref = lancamento_ref['descricao']
        valor_ref = lancamento_ref['valor']
        sinal_ref = lancamento_ref['sinal']
        
        # Buscar lançamentos do dia 07/01/2026 com mesmo valor e descrição similar
        # ✅ CORREÇÃO: Usar LIKE com escape correto para SQL Server
        descricao_like = descricao_ref.split(" - ")[0].replace("'", "''")
        descricao_exata = descricao_ref.replace("'", "''")
        
        query = f"""
            SELECT 
                id_movimentacao,
                descricao_movimentacao,
                valor_movimentacao,
                sinal_movimentacao,
                data_movimentacao
            FROM dbo.MOVIMENTACAO_BANCARIA
            WHERE banco_origem = 'SANTANDER'
              AND CAST(data_movimentacao AS DATE) = '2026-01-07'
              AND ABS(valor_movimentacao - {valor_ref}) < 0.01
              AND sinal_movimentacao = '{sinal_ref}'
              AND (
                  descricao_movimentacao LIKE '%{descricao_like}%'
                  OR descricao_movimentacao = '{descricao_exata}'
              )
            ORDER BY id_movimentacao DESC
        """
        
        resultado = adapter.execute_query(query, database=database)
        
        if resultado.get('success') and resultado.get('data'):
            rows = resultado['data']
            for row in rows:
                if isinstance(row, dict):
                    id_mov = row.get('id_movimentacao')
                    descricao_atual = row.get('descricao_movimentacao', '')
                else:
                    id_mov = row[0] if len(row) > 0 else None
                    descricao_atual = row[1] if len(row) > 1 else ''
                
                if id_mov:
                    # Verificar se a descrição corresponde (pode ter pequenas diferenças)
                    descricao_match = False
                    if descricao_ref in descricao_atual or descricao_atual in descricao_ref:
                        descricao_match = True
                    elif descricao_ref.split(' - ')[0] in descricao_atual:
                        descricao_match = True
                    
                    if descricao_match:
                        # Atualizar data para 08/01/2026
                        query_update = f"""
                            UPDATE dbo.MOVIMENTACAO_BANCARIA
                            SET data_movimentacao = '2026-01-08 00:00:00',
                                data_lancamento = '2026-01-08 00:00:00'
                            WHERE id_movimentacao = {id_mov}
                        """
                        
                        resultado_update = adapter.execute_query(query_update, database=database)
                        
                        if resultado_update.get('success'):
                            print(f"✅ Corrigido: ID {id_mov} - {descricao_atual[:50]}... (R$ {valor_ref:,.2f})")
                            total_corrigidos += 1
                        else:
                            error_msg = resultado_update.get('error', 'Erro desconhecido')
                            print(f"❌ Erro ao corrigir ID {id_mov}: {error_msg}")
    
    print(f"\n✅ Total de lançamentos corrigidos: {total_corrigidos}")
    
    if total_corrigidos > 0:
        print("\n💡 Agora os lançamentos do dia 08/01/2026 devem aparecer corretamente na tela de conciliação!")

if __name__ == '__main__':
    corrigir_datas_santander()

