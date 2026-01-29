"""
Script para identificar e preencher o nome e CNPJ de contrapartida em lançamentos existentes.
Útil para auditoria e compliance IN 1986/2020.
"""
import sys
import os
import logging

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sql_server_adapter import get_sql_adapter
from services.consulta_cpf_cnpj_service import ConsultaCpfCnpjService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def identificar_e_corrigir_contrapartidas():
    adapter = get_sql_adapter()
    if not adapter:
        print("❌ Não foi possível conectar ao SQL Server")
        return

    consulta_svc = ConsultaCpfCnpjService()
    
    print("🔍 Buscando lançamentos de CRÉDITO sem identificação de cliente...")
    
    # Buscar lançamentos de crédito onde o nome ou cnpj está vazio
    query = """
    SELECT id_movimentacao, sinal_movimentacao, valor_movimentacao, 
           descricao_movimentacao, cpf_cnpj_contrapartida, nome_contrapartida,
           json_dados_originais
    FROM dbo.MOVIMENTACAO_BANCARIA
    WHERE sinal_movimentacao = 'C'
      AND (cpf_cnpj_contrapartida IS NULL OR nome_contrapartida IS NULL)
    """
    
    res = adapter.execute_query(query)
    if not res.get('success'):
        print(f"❌ Erro ao buscar lançamentos: {res.get('error')}")
        return

    lancamentos = res.get('data', [])
    print(f"📊 Encontrados {len(lancamentos)} lançamentos para processar.")

    corrigidos = 0
    for lanc in lancamentos:
        id_mov = lanc.get('id_movimentacao')
        cnpj = lanc.get('cpf_cnpj_contrapartida')
        nome = lanc.get('nome_contrapartida')
        json_raw = lanc.get('json_dados_originais')
        
        # Se não tem CNPJ no banco, tentar extrair do JSON original
        if not cnpj and json_raw:
            try:
                import json
                dados = json.loads(json_raw)
                # Tentar campos do BB e Santander
                cnpj = dados.get('numeroCpfCnpjContrapartida') or dados.get('counterpartDocument') or dados.get('document')
                if cnpj == 0 or cnpj == '0':
                    cnpj = None
            except:
                pass

        if cnpj:
            cnpj_limpo = ''.join(filter(str.isdigit, str(cnpj)))
            if cnpj_limpo and len(cnpj_limpo) >= 11:
                print(f"⚙️ Processando ID {id_mov} - CNPJ: {cnpj_limpo}...")
                
                # Buscar nome se estiver faltando
                if not nome:
                    try:
                        res_consulta = consulta_svc.consultar(cnpj_limpo)
                        if res_consulta and res_consulta.get('nome'):
                            nome = res_consulta.get('nome')
                            print(f"   ✅ Nome encontrado: {nome}")
                    except Exception as e:
                        print(f"   ⚠️ Erro ao consultar CNPJ {cnpj_limpo}: {e}")

                # ✅ NOVO: Se ainda não tem nome, tentar extrair da descrição (ex: "PIX RECEBIDO - NOME")
                if not nome and lanc.get('descricao_movimentacao'):
                    desc = lanc.get('descricao_movimentacao')
                    # Se a descrição tem o CNPJ, o que vem antes ou depois pode ser o nome
                    partes = desc.split('-')
                    if len(partes) > 1:
                        for p in partes:
                            p_clean = p.strip()
                            if p_clean and not any(char.isdigit() for char in p_clean) and len(p_clean) > 3:
                                nome = p_clean
                                print(f"   ℹ️ Nome inferido da descrição: {nome}")
                                break

                # Atualizar no banco
                nome_esc = nome.replace("'", "''") if nome else None
                query_update = f"""
                UPDATE dbo.MOVIMENTACAO_BANCARIA
                SET cpf_cnpj_contrapartida = '{cnpj_limpo}',
                    nome_contrapartida = {'NULL' if not nome else f"'{nome_esc}'"}
                WHERE id_movimentacao = {id_mov}
                """
                adapter.execute_query(query_update)
                corrigidos += 1

    print(f"\n✅ Concluído! {corrigidos} lançamentos atualizados.")

if __name__ == "__main__":
    identificar_e_corrigir_contrapartidas()
