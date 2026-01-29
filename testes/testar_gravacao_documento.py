#!/usr/bin/env python3
"""
Teste direto de gravação de documento no SQL Server
"""
import sys
import os
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

# ✅ FORÇAR CARREGAMENTO DO .env ANTES DE IMPORTAR ADAPTER
env_path = Path(root_dir) / '.env'
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

print("=" * 80)
print("🔍 TESTE DE GRAVAÇÃO DE DOCUMENTO NO SQL SERVER")
print("=" * 80)

# Dados de teste do CE 172505417636125
numero_ce = "172505417636125"
processo_ref = "BGR.0070/25"

# Dados simulados do CE (formato que vem da API)
ce_dados = {
    "numero": numero_ce,
    "situacaoCarga": "VINCULADA_A_DOCUMENTO_DE_DESPACHO",
    "dataSituacaoCarga": "2026-01-07T00:00:00",
    "numeroBL": "SZOWS2511061",
    "nomeNavio": "CMA CGM BUZIOS",
    "portoOrigem": "CNNGB",
    "portoDestino": "BRIOA",
    "ulDestinoFinal": "0927700",
    "paisProcedencia": "CN",
    "cnpjCpfConsignatario": "22849492000208",
    "dataEmissao": "2025-11-28T00:00:00"
}

print(f"\n1️⃣ Testando gravação do CE {numero_ce}...")
print(f"   Processo: {processo_ref}")

try:
    from services.documento_historico_service import DocumentoHistoricoService
    
    historico_service = DocumentoHistoricoService()
    
    print("\n2️⃣ Chamando detectar_e_gravar_mudancas...")
    mudancas = historico_service.detectar_e_gravar_mudancas(
        numero_documento=numero_ce,
        tipo_documento='CE',
        dados_novos=ce_dados,
        fonte_dados='TESTE',
        api_endpoint='/teste',
        processo_referencia=processo_ref
    )
    
    print(f"\n✅ Mudanças detectadas: {len(mudancas)}")
    for mudanca in mudancas:
        print(f"   - {mudanca.get('campo_alterado', 'N/A')}: {mudanca.get('valor_anterior', 'N/A')} → {mudanca.get('valor_novo', 'N/A')}")
    
    print("\n3️⃣ Verificando se documento foi gravado no SQL Server...")
    from utils.sql_server_adapter import get_sql_adapter
    
    sql_adapter = get_sql_adapter()
    database = os.getenv('SQL_DATABASE', 'mAIke_assistente')
    
    query = f"""
        SELECT 
            numero_documento,
            tipo_documento,
            processo_referencia,
            situacao_documento,
            fonte_dados,
            criado_em
        FROM dbo.DOCUMENTO_ADUANEIRO
        WHERE numero_documento = '{numero_ce}' AND tipo_documento = 'CE'
    """
    
    result = sql_adapter.execute_query(query, database=database)
    
    if result and result.get('success'):
        data = result.get('data', [])
        if data:
            print(f"\n✅✅✅ DOCUMENTO GRAVADO COM SUCESSO!")
            doc = data[0]
            print(f"   Número: {doc.get('numero_documento')}")
            print(f"   Tipo: {doc.get('tipo_documento')}")
            print(f"   Processo: {doc.get('processo_referencia')}")
            print(f"   Situação: {doc.get('situacao_documento')}")
            print(f"   Fonte: {doc.get('fonte_dados')}")
            print(f"   Criado em: {doc.get('criado_em')}")
        else:
            print(f"\n❌ Documento NÃO foi gravado")
            print(f"   Query executada com sucesso, mas nenhum registro encontrado")
            print(f"\n💡 Verificando erros...")
            if result.get('error'):
                print(f"   Erro: {result.get('error')}")
    else:
        print(f"\n❌ Erro ao verificar documento")
        print(f"   Erro: {result.get('error', 'Erro desconhecido') if result else 'Sem resposta'}")
    
    print("\n4️⃣ Verificando histórico...")
    query_historico = f"""
        SELECT TOP 5
            numero_documento,
            tipo_documento,
            tipo_evento,
            campo_alterado,
            valor_anterior,
            valor_novo,
            criado_em
        FROM dbo.HISTORICO_DOCUMENTO_ADUANEIRO
        WHERE numero_documento = '{numero_ce}' AND tipo_documento = 'CE'
        ORDER BY criado_em DESC
    """
    
    result_historico = sql_adapter.execute_query(query_historico, database=database)
    
    if result_historico and result_historico.get('success'):
        data_historico = result_historico.get('data', [])
        if data_historico:
            print(f"\n✅ Histórico encontrado: {len(data_historico)} registro(s)")
            for hist in data_historico[:3]:  # Mostrar até 3
                print(f"   - {hist.get('tipo_evento', 'N/A')}: {hist.get('campo_alterado', 'N/A')}")
        else:
            print(f"\n⚠️ Nenhum histórico encontrado (pode ser normal se não houve mudanças)")
    else:
        print(f"\n⚠️ Erro ao verificar histórico: {result_historico.get('error', 'Erro desconhecido') if result_historico else 'Sem resposta'}")
    
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("✅ Teste concluído")
print("=" * 80)


