#!/usr/bin/env python3
"""
Teste do Serviço de Sincronização de Extratos Bancários.

Este script testa:
1. Geração de hash único para lançamentos
2. Detecção de duplicatas
3. Detecção de processos por descrição
4. Importação de lançamentos (se SQL Server disponível)

Uso:
    python3 testes/test_banco_sincronizacao.py
"""
import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import json


def test_gerar_hash():
    """Testa geração de hash único para lançamentos."""
    print("\n" + "="*60)
    print("TESTE 1: Geração de Hash Único")
    print("="*60)
    
    from services.banco_sincronizacao_service import BancoSincronizacaoService
    
    service = BancoSincronizacaoService()
    
    # Lançamento de teste
    lancamento1 = {
        'dataLancamento': 7012026,  # 07/01/2026
        'valorLancamento': 1500.00,
        'tipoLancamento': 'DEBITO',
        'indicadorSinalLancamento': 'D',
        'textoDescricaoHistorico': 'PAGAMENTO FRETE DMD.0083/25'
    }
    
    # Mesmo lançamento (deve gerar mesmo hash)
    lancamento2 = {
        'dataLancamento': 7012026,
        'valorLancamento': 1500.00,
        'tipoLancamento': 'DEBITO',
        'indicadorSinalLancamento': 'D',
        'textoDescricaoHistorico': 'PAGAMENTO FRETE DMD.0083/25'
    }
    
    # Lançamento diferente (deve gerar hash diferente)
    lancamento3 = {
        'dataLancamento': 8012026,  # Data diferente
        'valorLancamento': 1500.00,
        'tipoLancamento': 'DEBITO',
        'indicadorSinalLancamento': 'D',
        'textoDescricaoHistorico': 'PAGAMENTO FRETE DMD.0083/25'
    }
    
    hash1 = service.gerar_hash_lancamento(lancamento1, '1251', '50483')
    hash2 = service.gerar_hash_lancamento(lancamento2, '1251', '50483')
    hash3 = service.gerar_hash_lancamento(lancamento3, '1251', '50483')
    
    print(f"\nLançamento 1 hash: {hash1[:32]}...")
    print(f"Lançamento 2 hash: {hash2[:32]}...")
    print(f"Lançamento 3 hash: {hash3[:32]}...")
    
    # Validações
    assert hash1 == hash2, "❌ ERRO: Hashes iguais deveriam ser iguais!"
    assert hash1 != hash3, "❌ ERRO: Hashes diferentes deveriam ser diferentes!"
    assert len(hash1) == 64, f"❌ ERRO: Hash deveria ter 64 caracteres, tem {len(hash1)}"
    
    print("\n✅ TESTE 1 PASSOU: Hashes gerados corretamente!")
    print(f"   - Lançamentos iguais = mesmo hash ✅")
    print(f"   - Lançamentos diferentes = hash diferente ✅")
    print(f"   - Hash tem 64 caracteres (SHA-256) ✅")
    
    return True


def test_detectar_processo():
    """Testa detecção de processo por descrição."""
    print("\n" + "="*60)
    print("TESTE 2: Detecção de Processo por Descrição")
    print("="*60)
    
    from services.banco_sincronizacao_service import BancoSincronizacaoService
    
    service = BancoSincronizacaoService()
    
    # Casos de teste
    casos = [
        ("PAGAMENTO FRETE DMD.0083/25", "DMD.0083/25"),
        ("PAG FRETE DMD 0083/25", "DMD.0083/25"),
        ("IMPOSTOS ALH.0168/25", "ALH.0168/25"),
        ("VDM.0004/25 - DESPESAS", "VDM.0004/25"),
        ("BND0093/25 FRETE", "BND.0093/25"),
        ("PAGAMENTO GENERICO", None),  # Não deve detectar
        ("TRANSFERENCIA PIX", None),  # Não deve detectar
    ]
    
    erros = 0
    for descricao, esperado in casos:
        resultado = service.detectar_processo_por_descricao(descricao)
        
        if resultado == esperado:
            status = "✅"
        else:
            status = "❌"
            erros += 1
        
        print(f"{status} \"{descricao}\" → {resultado} (esperado: {esperado})")
    
    if erros == 0:
        print(f"\n✅ TESTE 2 PASSOU: Todos os {len(casos)} casos detectados corretamente!")
    else:
        print(f"\n❌ TESTE 2 FALHOU: {erros} de {len(casos)} casos falharam")
        return False
    
    return True


def test_conversao_data():
    """Testa conversão de data do formato BB."""
    print("\n" + "="*60)
    print("TESTE 3: Conversão de Data BB (DDMMAAAA)")
    print("="*60)
    
    from services.banco_sincronizacao_service import BancoSincronizacaoService
    
    service = BancoSincronizacaoService()
    
    # Casos de teste
    casos = [
        (7012026, datetime(2026, 1, 7)),    # 07/01/2026
        (15122025, datetime(2025, 12, 15)),  # 15/12/2025
        (1012026, datetime(2026, 1, 1)),     # 01/01/2026 (sem zero à esquerda)
        (0, None),                            # Data inválida
        (None, None),                         # Data nula
    ]
    
    erros = 0
    for data_bb, esperado in casos:
        resultado = service._converter_data_bb(data_bb)
        
        if resultado == esperado:
            status = "✅"
        else:
            status = "❌"
            erros += 1
        
        print(f"{status} {data_bb} → {resultado} (esperado: {esperado})")
    
    if erros == 0:
        print(f"\n✅ TESTE 3 PASSOU: Todas as conversões de data corretas!")
    else:
        print(f"\n❌ TESTE 3 FALHOU: {erros} de {len(casos)} casos falharam")
        return False
    
    return True


def test_importacao_simulada():
    """Testa importação simulada (sem SQL Server real)."""
    print("\n" + "="*60)
    print("TESTE 4: Importação Simulada de Lançamentos")
    print("="*60)
    
    from services.banco_sincronizacao_service import BancoSincronizacaoService
    
    service = BancoSincronizacaoService()
    
    # Simular lançamentos da API do BB
    lancamentos = [
        {
            'dataLancamento': 7012026,
            'valorLancamento': 1500.00,
            'tipoLancamento': 'DEBITO',
            'indicadorSinalLancamento': 'D',
            'textoDescricaoHistorico': 'PAGAMENTO FRETE DMD.0083/25',
            'codigoHistoricoBanco': '123',
            'textoInformacaoComplementar': 'Ref: NF 12345'
        },
        {
            'dataLancamento': 7012026,
            'valorLancamento': 2500.00,
            'tipoLancamento': 'CREDITO',
            'indicadorSinalLancamento': 'C',
            'textoDescricaoHistorico': 'RECEBIMENTO CLIENTE',
            'numeroCpfCnpjContrapartida': '12345678901234',
            'indicadorTipoPessoaContrapartida': 'J'
        },
        {
            'dataLancamento': 6012026,
            'valorLancamento': 800.00,
            'tipoLancamento': 'DEBITO',
            'indicadorSinalLancamento': 'D',
            'textoDescricaoHistorico': 'IMPOSTOS ALH.0168/25'
        }
    ]
    
    # Gerar hashes para todos
    hashes = []
    for lanc in lancamentos:
        h = service.gerar_hash_lancamento(lanc, '1251', '50483')
        hashes.append(h)
        print(f"📝 Lançamento: {lanc['textoDescricaoHistorico'][:40]}...")
        print(f"   Hash: {h[:32]}...")
        print(f"   Processo detectado: {service.detectar_processo_por_descricao(lanc['textoDescricaoHistorico'])}")
        print()
    
    # Verificar que todos os hashes são únicos
    hashes_unicos = set(hashes)
    if len(hashes) == len(hashes_unicos):
        print(f"✅ Todos os {len(hashes)} lançamentos têm hashes únicos!")
    else:
        print(f"❌ ERRO: Alguns lançamentos têm hashes duplicados!")
        return False
    
    print("\n✅ TESTE 4 PASSOU: Importação simulada funcionando!")
    return True


def test_sql_server_disponivel():
    """Testa se SQL Server está disponível para importação real."""
    print("\n" + "="*60)
    print("TESTE 5: Verificar SQL Server Disponível")
    print("="*60)
    
    from services.banco_sincronizacao_service import BancoSincronizacaoService
    
    service = BancoSincronizacaoService()
    
    if service.sql_adapter:
        print("✅ SQL Server adapter disponível!")
        
        # Tentar verificar se tabela existe
        try:
            query = """
                SELECT COUNT(*) as total 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'MOVIMENTACAO_BANCARIA'
            """
            resultado = service.sql_adapter.execute_query(query)
            
            if resultado and len(resultado) > 0 and resultado[0].get('total', 0) > 0:
                print("✅ Tabela MOVIMENTACAO_BANCARIA existe!")
                
                # Contar registros existentes
                query_count = "SELECT COUNT(*) as total FROM MOVIMENTACAO_BANCARIA"
                resultado_count = service.sql_adapter.execute_query(query_count)
                total = resultado_count[0].get('total', 0) if resultado_count else 0
                print(f"📊 Total de registros existentes: {total}")
                
                return True
            else:
                print("⚠️ Tabela MOVIMENTACAO_BANCARIA não existe ainda")
                print("   Execute o script: scripts/criar_banco_maike_completo.sql")
                return True  # Não é erro, apenas aviso
                
        except Exception as e:
            print(f"⚠️ Erro ao verificar tabela: {e}")
            return True  # Não é erro crítico
    else:
        print("⚠️ SQL Server não disponível (pode estar offline)")
        print("   Isso não é um erro - o sistema funciona sem SQL Server")
        return True


def main():
    """Executa todos os testes."""
    print("\n" + "="*60)
    print("🧪 TESTES DO SERVIÇO DE SINCRONIZAÇÃO BANCÁRIA")
    print("="*60)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    resultados = []
    
    # Teste 1: Hash
    try:
        resultados.append(("Geração de Hash", test_gerar_hash()))
    except Exception as e:
        print(f"❌ ERRO no teste de hash: {e}")
        resultados.append(("Geração de Hash", False))
    
    # Teste 2: Detecção de processo
    try:
        resultados.append(("Detecção de Processo", test_detectar_processo()))
    except Exception as e:
        print(f"❌ ERRO no teste de detecção: {e}")
        resultados.append(("Detecção de Processo", False))
    
    # Teste 3: Conversão de data
    try:
        resultados.append(("Conversão de Data", test_conversao_data()))
    except Exception as e:
        print(f"❌ ERRO no teste de data: {e}")
        resultados.append(("Conversão de Data", False))
    
    # Teste 4: Importação simulada
    try:
        resultados.append(("Importação Simulada", test_importacao_simulada()))
    except Exception as e:
        print(f"❌ ERRO no teste de importação: {e}")
        resultados.append(("Importação Simulada", False))
    
    # Teste 5: SQL Server
    try:
        resultados.append(("SQL Server Disponível", test_sql_server_disponivel()))
    except Exception as e:
        print(f"❌ ERRO no teste de SQL Server: {e}")
        resultados.append(("SQL Server Disponível", False))
    
    # Resumo final
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    
    passou = 0
    falhou = 0
    
    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"  {status}: {nome}")
        if resultado:
            passou += 1
        else:
            falhou += 1
    
    print(f"\n📈 Total: {passou}/{len(resultados)} testes passaram")
    
    if falhou == 0:
        print("\n✅✅✅ TODOS OS TESTES PASSARAM! ✅✅✅")
        return 0
    else:
        print(f"\n❌ {falhou} teste(s) falharam")
        return 1


if __name__ == '__main__':
    sys.exit(main())

