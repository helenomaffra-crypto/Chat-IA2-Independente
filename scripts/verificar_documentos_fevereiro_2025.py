#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar documentos registrados em fevereiro/2025 no banco Make.

Verifica se há apenas os 3 documentos esperados:
- DI 2504026314 — Processo: MSS.0015/24 — Registro: 19/02/2025
- DI 2503481590 — Processo: MSS.0002/25 — Registro: 12/02/2025
- DI 2503408906 — Processo: ALH.0004/25 — Registro: 11/02/2025
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sql_server_adapter import get_sql_adapter

def formatar_data(data_str: str) -> str:
    """Formata data para exibição."""
    try:
        if isinstance(data_str, str):
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y']:
                try:
                    dt = datetime.strptime(data_str.split()[0], fmt)
                    return dt.strftime('%d/%m/%Y')
                except:
                    continue
        return str(data_str)
    except:
        return str(data_str)

def main():
    print("=" * 80)
    print("🔍 VERIFICANDO DOCUMENTOS REGISTRADOS EM FEVEREIRO/2025")
    print("=" * 80)
    print()
    
    adapter = get_sql_adapter()
    if not adapter:
        print("❌ Erro: Não foi possível conectar ao SQL Server")
        return 1
    
    # Verificar nos bancos antigos (Make/Serpro/duimp)
    print("📊 Buscando em: Serpro.dbo (DIs) e duimp.dbo (DUIMPs)")
    print()
    
    documentos = []
    
    # 1. Buscar DIs no Serpro.dbo
    query_dis = """
        SELECT 
            ddg.numeroDi as numero_documento,
            'DI' as tipo_documento,
            COALESCE(pi.numero_processo, 'ID:' + CAST(diH.idImportacao as VARCHAR(50))) as processo_referencia,
            ddg.situacaoDi as situacao_documento,
            diDesp.canalSelecaoParametrizada as canal_documento,
            CAST(diDesp.dataHoraRegistro AS DATE) as data_registro_date,
            diDesp.dataHoraRegistro as data_registro
        FROM Serpro.dbo.Hi_Historico_Di diH
        INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot ON diH.diId = diRoot.dadosDiId
        INNER JOIN Serpro.dbo.Di_Dados_Gerais ddg ON diRoot.dadosGeraisId = ddg.dadosGeraisId
        LEFT JOIN Serpro.dbo.Di_Dados_Despacho diDesp ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
        LEFT JOIN Make.dbo.PROCESSO_IMPORTACAO pi ON pi.id_importacao = diH.idImportacao
        WHERE diDesp.dataHoraRegistro IS NOT NULL
          AND YEAR(diDesp.dataHoraRegistro) = 2025
          AND MONTH(diDesp.dataHoraRegistro) = 2
        ORDER BY diDesp.dataHoraRegistro ASC
    """
    
    resultado_dis = adapter.execute_query(query_dis, database='Serpro')
    if resultado_dis.get('success') and resultado_dis.get('data'):
        documentos.extend(resultado_dis['data'])
        print(f"✅ DIs encontradas: {len(resultado_dis['data'])}")
    else:
        print(f"⚠️  Erro ao buscar DIs: {resultado_dis.get('error', 'Erro desconhecido')}")
    
    # 2. Buscar DUIMPs no duimp.dbo
    query_duimp = """
        SELECT 
            d.numero as numero_documento,
            'DUIMP' as tipo_documento,
            d.numero_processo as processo_referencia,
            d.ultima_situacao as situacao_documento,
            dar.canal_consolidado as canal_documento,
            CAST(d.data_registro AS DATE) as data_registro_date,
            d.data_registro as data_registro
        FROM duimp.dbo.duimp d
        LEFT JOIN duimp.dbo.duimp_resultado_analise_risco dar ON d.duimp_id = dar.duimp_id
        WHERE d.data_registro IS NOT NULL
          AND YEAR(d.data_registro) = 2025
          AND MONTH(d.data_registro) = 2
        ORDER BY d.data_registro ASC
    """
    
    resultado_duimp = adapter.execute_query(query_duimp, database='duimp')
    if resultado_duimp.get('success') and resultado_duimp.get('data'):
        documentos.extend(resultado_duimp['data'])
        print(f"✅ DUIMPs encontradas: {len(resultado_duimp['data'])}")
    else:
        print(f"⚠️  Erro ao buscar DUIMPs: {resultado_duimp.get('error', 'Erro desconhecido')}")
    
    print()
    
    print(f"📊 Total de documentos encontrados: {len(documentos)}")
    print()
    
    if not documentos:
        print("⚠️  Nenhum documento encontrado em fevereiro/2025 no banco Make")
        return 0
    
    # Documentos esperados
    esperados = {
        '2504026314': {'processo': 'MSS.0015/24', 'data': '19/02/2025'},
        '2503481590': {'processo': 'MSS.0002/25', 'data': '12/02/2025'},
        '2503408906': {'processo': 'ALH.0004/25', 'data': '11/02/2025'}
    }
    
    print("=" * 80)
    print("📋 DOCUMENTOS ENCONTRADOS:")
    print("=" * 80)
    print()
    
    encontrados = {}
    for doc in documentos:
        num_doc = str(doc.get('numero_documento', '')).strip()
        if not num_doc or num_doc == 'None':
            continue
        
        processo = doc.get('processo_referencia', 'N/A')
        if processo and processo != 'None':
            processo = str(processo).strip()
        else:
            processo = 'N/A'
        
        data_reg = formatar_data(str(doc.get('data_registro_date', '') or doc.get('data_registro', '')))
        situacao = doc.get('situacao_documento', 'N/A')
        canal = doc.get('canal_documento', '')
        
        encontrados[num_doc] = {
            'processo': processo,
            'data': data_reg,
            'situacao': situacao,
            'canal': canal
        }
        
        print(f"📄 {doc.get('tipo_documento', 'N/A')} {num_doc}")
        print(f"   Processo: {processo}")
        print(f"   Data Registro: {data_reg}")
        print(f"   Situação: {situacao}")
        if canal and canal != 'None':
            print(f"   Canal: {canal}")
        print()
    
    # Comparar com esperados
    print("=" * 80)
    print("✅ VERIFICAÇÃO:")
    print("=" * 80)
    print()
    
    todos_encontrados = True
    extras = []
    
    for num_doc, info in esperados.items():
        if num_doc in encontrados:
            encontrado = encontrados[num_doc]
            if encontrado['processo'] == info['processo']:
                print(f"✅ {num_doc} ({info['processo']}) - ENCONTRADO")
            else:
                print(f"⚠️  {num_doc} - Processo diferente! Esperado: {info['processo']}, Encontrado: {encontrado['processo']}")
                todos_encontrados = False
        else:
            print(f"❌ {num_doc} ({info['processo']}) - NÃO ENCONTRADO")
            todos_encontrados = False
    
    # Verificar se há documentos extras
    for num_doc, info in encontrados.items():
        if num_doc not in esperados:
            extras.append((num_doc, info))
    
    if extras:
        print()
        print(f"⚠️  {len(extras)} documento(s) EXTRA encontrado(s) (não estava na lista esperada):")
        for num_doc, info in extras:
            print(f"   - {num_doc} — Processo: {info['processo']} — Data: {info['data']}")
        todos_encontrados = False
    
    print()
    print("=" * 80)
    if todos_encontrados and len(documentos) == 3:
        print("✅ RESULTADO: Exatamente os 3 documentos esperados foram encontrados!")
    elif todos_encontrados:
        print(f"✅ RESULTADO: Todos os documentos esperados foram encontrados, mas há {len(documentos)} total (esperado 3)")
    else:
        print(f"⚠️  RESULTADO: Há diferenças! Total encontrado: {len(documentos)}")
    print("=" * 80)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
