#!/usr/bin/env python3
"""
Script de teste combinado para validar todas as migrações de serviços.

Testa:
- ConsultaService (verificar_atualizacao_ce, consultar_ce_maritimo, consultar_processo_consolidado)
- ProcessoListService (listar_processos_por_categoria, listar_processos_por_eta, etc.)

Uso:
    python test_servicos_migrados.py
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def executar_testes_consulta_service():
    """Executa testes do ConsultaService"""
    print("\n" + "="*70)
    print("📦 TESTANDO CONSULTASERVICE")
    print("="*70)
    
    try:
        from test_consulta_service import (
            test_verificar_atualizacao_ce,
            test_consultar_ce_maritimo,
            test_consultar_processo_consolidado,
            test_integracao_chat_service as test_integracao_consulta
        )
        
        test_verificar_atualizacao_ce()
        test_consultar_ce_maritimo()
        test_consultar_processo_consolidado()
        test_integracao_consulta()
        
        print("\n✅ Todos os testes do ConsultaService passaram!")
        return True
        
    except Exception as e:
        print(f"\n❌ Erro nos testes do ConsultaService: {e}")
        import traceback
        traceback.print_exc()
        return False


def executar_testes_processo_list_service():
    """Executa testes do ProcessoListService"""
    print("\n" + "="*70)
    print("📋 TESTANDO PROCESSOLISTSERVICE")
    print("="*70)
    
    try:
        from test_processo_list_service import (
            test_listar_processos_por_categoria,
            test_listar_processos_por_eta,
            test_listar_processos_por_situacao,
            test_listar_processos_com_pendencias,
            test_listar_todos_processos_por_situacao,
            test_integracao_chat_service as test_integracao_lista
        )
        
        test_listar_processos_por_categoria()
        test_listar_processos_por_eta()
        test_listar_processos_por_situacao()
        test_listar_processos_com_pendencias()
        test_listar_todos_processos_por_situacao()
        test_integracao_lista()
        
        print("\n✅ Todos os testes do ProcessoListService passaram!")
        return True
        
    except Exception as e:
        print(f"\n❌ Erro nos testes do ProcessoListService: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executa todos os testes"""
    print("\n" + "="*70)
    print("🧪 TESTES COMPLETOS DOS SERVIÇOS MIGRADOS")
    print("="*70)
    print("\n⚠️  IMPORTANTE: Altere os valores nos arquivos de teste individuais")
    print("   (test_consulta_service.py e test_processo_list_service.py)")
    print("   para valores que você sabe que existem no seu sistema.\n")
    
    resultados = []
    
    # Testar ConsultaService
    resultados.append(("ConsultaService", executar_testes_consulta_service()))
    
    # Testar ProcessoListService
    resultados.append(("ProcessoListService", executar_testes_processo_list_service()))
    
    # Resumo final
    print("\n" + "="*70)
    print("📊 RESUMO DOS TESTES")
    print("="*70)
    
    todos_passaram = True
    for nome, passou in resultados:
        status = "✅ PASSOU" if passou else "❌ FALHOU"
        print(f"   {nome}: {status}")
        if not passou:
            todos_passaram = False
    
    print("="*70)
    
    if todos_passaram:
        print("\n✅ TODOS OS TESTES PASSARAM!")
        print("\n🎉 Migrações validadas com sucesso!")
        print("   - ConsultaService: ✅")
        print("   - ProcessoListService: ✅")
        return 0
    else:
        print("\n❌ ALGUNS TESTES FALHARAM!")
        print("   Verifique os erros acima.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
