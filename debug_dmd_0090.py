
import logging
import os
from utils.sql_server_adapter import get_sql_adapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_dmd_0090():
    adapter = get_sql_adapter()
    if not adapter:
        print("❌ Não foi possível obter o adaptador SQL Server")
        return

    processo = "DMD.0090/25"
    print(f"\n🔍 Investigando processo: {processo}")

    # 1. Buscar dados básicos do processo
    query_proc = f"SELECT id_processo_importacao, id_importacao, numero_di, numero_duimp FROM make.dbo.PROCESSO_IMPORTACAO WHERE numero_processo = '{processo}'"
    res_proc = adapter.execute_query(query_proc, 'Make')
    if not res_proc.get('success') or not res_proc.get('data'):
        print(f"❌ Processo {processo} não encontrado")
        return
    
    proc_data = res_proc['data'][0]
    id_importacao = proc_data['id_importacao']
    print(f"✅ ID Importação: {id_importacao}")
    print(f"✅ Número DI: {proc_data['numero_di']}")

    # 2. Buscar histórico de DIs
    print("\n--- Histórico de DIs (Hi_Historico_Di) ---")
    query_hi = f"""
        SELECT diH.diId, diH.idImportacao, ddg.numeroDi, ddg.dataHoraSituacaoDi, diDesp.dataHoraDesembaraco, diRoot.dadosDiId
        FROM Serpro.dbo.Hi_Historico_Di diH
        INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot ON diH.diId = diRoot.dadosDiId
        INNER JOIN Serpro.dbo.Di_Dados_Gerais ddg ON diRoot.dadosGeraisId = ddg.dadosGeraisId
        LEFT JOIN Serpro.dbo.Di_Dados_Despacho diDesp ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
        WHERE diH.idImportacao = {id_importacao}
        ORDER BY ddg.dataHoraSituacaoDi DESC
    """
    res_hi = adapter.execute_query(query_hi, 'Serpro')
    if res_hi.get('success') and res_hi.get('data'):
        for row in res_hi['data']:
            print(f"DI: {row['numeroDi']} | Situacao: {row['dataHoraSituacaoDi']} | Desembaraco: {row['dataHoraDesembaraco']} | dadosDiId: {row['dadosDiId']}")
            
            # Buscar Frete para este dadosDiId
            query_frete = f"SELECT valorTotalDolares, totalReais FROM Serpro.dbo.Di_Frete WHERE freteId = '{row['dadosDiId']}'"
            res_frete = adapter.execute_query(query_frete, 'Serpro')
            if res_frete.get('success') and res_frete.get('data'):
                for f in res_frete['data']:
                    print(f"   -> FRETE DI: USD {f['valorTotalDolares']} | BRL {f['totalReais']}")
            else:
                print("   -> FRETE DI: Não encontrado")
    else:
        print("❌ Nenhuma DI encontrada no histórico")

    # 3. Buscar CE relacionado
    print("\n--- Conhecimento de Embarque (CE) ---")
    query_ce = f"""
        SELECT ceRoot.numero, ceRoot.valorFreteTotal, ceRoot.updatedAt
        FROM Serpro.dbo.Hi_Historico_Ce ceH
        INNER JOIN Serpro.dbo.Ce_Root_Conhecimento_Embarque ceRoot ON ceH.ceId = ceRoot.rootConsultaEmbarqueId
        WHERE ceH.idImportacao = {id_importacao}
        ORDER BY ceRoot.updatedAt DESC
    """
    res_ce = adapter.execute_query(query_ce, 'Serpro')
    if res_ce.get('success') and res_ce.get('data'):
        for row in res_ce['data']:
            print(f"CE: {row['numero']} | Frete Total: {row['valorFreteTotal']} | Atualizado em: {row['updatedAt']}")
    else:
        print("❌ Nenhum CE encontrado")

if __name__ == "__main__":
    debug_dmd_0090()
