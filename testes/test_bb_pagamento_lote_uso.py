"""
Script de teste prático para API de Pagamentos em Lote do Banco do Brasil.

Este script demonstra como usar a API de pagamentos em lote:
1. Listar lotes existentes
2. Criar um novo lote de pagamentos
3. Consultar status de um lote

⚠️ ATENÇÃO: Este teste faz requisições REAIS à API do BB (sandbox).
"""
import sys
import os
import logging

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_listar_lotes():
    """Testa listagem de lotes."""
    logger.info("=" * 80)
    logger.info("📋 Teste 1: Listar Lotes de Pagamentos")
    logger.info("=" * 80)
    
    try:
        from services.banco_brasil_payments_service import BancoBrasilPaymentsService
        
        service = BancoBrasilPaymentsService()
        
        if not service.enabled:
            logger.error("❌ Serviço não está habilitado. Configure as credenciais no .env")
            return False
        
        logger.info("   Listando lotes...")
        resultado = service.listar_lotes()
        
        if resultado.get('sucesso'):
            logger.info("   ✅ Listagem realizada com sucesso")
            logger.info(f"   📋 Resposta:\n{resultado.get('resposta', '')}")
            return True
        else:
            logger.warning(f"   ⚠️ Erro: {resultado.get('erro', 'Desconhecido')}")
            logger.info(f"   📋 Resposta: {resultado.get('resposta', '')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao listar lotes: {e}", exc_info=True)
        return False

def test_criar_lote_exemplo():
    """Testa criação de um lote de exemplo (boleto)."""
    logger.info("=" * 80)
    logger.info("💰 Teste 2: Criar Lote de Pagamento (Exemplo)")
    logger.info("=" * 80)
    
    try:
        from services.banco_brasil_payments_service import BancoBrasilPaymentsService
        
        service = BancoBrasilPaymentsService()
        
        if not service.enabled:
            logger.error("❌ Serviço não está habilitado. Configure as credenciais no .env")
            return False
        
        # Obter agência e conta do .env ou usar valores de exemplo
        agencia = os.getenv("BB_TEST_AGENCIA", "1505")
        conta = os.getenv("BB_TEST_CONTA", "1348")
        
        logger.info(f"   Agência: {agencia}, Conta: {conta}")
        logger.info("   ⚠️ Este é um EXEMPLO - não será executado automaticamente")
        logger.info("   Para criar um lote real, descomente o código abaixo e ajuste os valores")
        
        # Exemplo de pagamento (comentado para não executar acidentalmente)
        exemplo_pagamentos = [
            {
                "tipo": "BOLETO",
                "codigo_barras": "34191093216412992293280145580009313510000090000",
                "valor": 900.00,
                "beneficiario": "PLUXEE BENEFICIOS BRASIL S.A",
                "vencimento": "2026-02-08"
            }
        ]
        
        logger.info("   📝 Exemplo de payload:")
        logger.info(f"      Agência: {agencia}")
        logger.info(f"      Conta: {conta}")
        logger.info(f"      Pagamentos: {len(exemplo_pagamentos)} boleto(s)")
        logger.info(f"      Valor total: R$ {sum(p.get('valor', 0) for p in exemplo_pagamentos):,.2f}")
        
        # Descomente para executar de verdade:
        # resultado = service.iniciar_pagamento_lote(
        #     agencia=agencia,
        #     conta=conta,
        #     pagamentos=exemplo_pagamentos,
        #     data_pagamento=None  # Usa data de hoje
        # )
        # 
        # if resultado.get('sucesso'):
        #     logger.info("   ✅ Lote criado com sucesso!")
        #     logger.info(f"   📋 Resposta:\n{resultado.get('resposta', '')}")
        #     return True
        # else:
        #     logger.error(f"   ❌ Erro: {resultado.get('erro', 'Desconhecido')}")
        #     return False
        
        logger.info("   💡 Para executar, descomente o código no script")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar lote: {e}", exc_info=True)
        return False

def test_consultar_lote():
    """Testa consulta de um lote específico."""
    logger.info("=" * 80)
    logger.info("🔍 Teste 3: Consultar Lote Específico")
    logger.info("=" * 80)
    
    try:
        from services.banco_brasil_payments_service import BancoBrasilPaymentsService
        
        service = BancoBrasilPaymentsService()
        
        if not service.enabled:
            logger.error("❌ Serviço não está habilitado. Configure as credenciais no .env")
            return False
        
        # Primeiro, listar lotes para obter um ID
        logger.info("   Listando lotes para obter um ID de exemplo...")
        resultado_lista = service.listar_lotes()
        
        if resultado_lista.get('sucesso'):
            lotes = resultado_lista.get('dados', [])
            if lotes:
                id_lote = lotes[0].get('idLote') or lotes[0].get('id_lote') or lotes[0].get('id')
                if id_lote:
                    logger.info(f"   Consultando lote: {id_lote}")
                    resultado = service.consultar_lote(id_lote)
                    
                    if resultado.get('sucesso'):
                        logger.info("   ✅ Consulta realizada com sucesso")
                        logger.info(f"   📋 Resposta:\n{resultado.get('resposta', '')}")
                        return True
                    else:
                        logger.warning(f"   ⚠️ Erro: {resultado.get('erro', 'Desconhecido')}")
                        return False
                else:
                    logger.warning("   ⚠️ Nenhum ID de lote encontrado na lista")
                    return False
            else:
                logger.info("   ℹ️ Nenhum lote encontrado. Crie um lote primeiro.")
                return True  # Não é erro, apenas não há lotes
        else:
            logger.warning(f"   ⚠️ Erro ao listar lotes: {resultado_lista.get('erro', 'Desconhecido')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao consultar lote: {e}", exc_info=True)
        return False

def test_via_agent():
    """Testa uso via Agent (como seria usado pelo chat)."""
    logger.info("=" * 80)
    logger.info("🤖 Teste 4: Uso via Agent (Simulação do Chat)")
    logger.info("=" * 80)
    
    try:
        from services.agents.banco_brasil_agent import BancoBrasilAgent
        
        agent = BancoBrasilAgent()
        
        if not agent.payments_service or not agent.payments_service.enabled:
            logger.error("❌ Payments Service não está habilitado no Agent")
            return False
        
        logger.info("   ✅ Agent inicializado com Payments Service")
        
        # Testar listagem via agent
        logger.info("   Testando listagem via agent...")
        resultado = agent.execute(
            tool_name='listar_lotes_bb',
            arguments={},
            context={}
        )
        
        if resultado.get('sucesso'):
            logger.info("   ✅ Listagem via agent funcionou")
            logger.info(f"   📋 Resposta:\n{resultado.get('resposta', '')[:200]}...")
            return True
        else:
            logger.warning(f"   ⚠️ Erro: {resultado.get('erro', 'Desconhecido')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao testar agent: {e}", exc_info=True)
        return False

def main():
    """Executa todos os testes."""
    logger.info("=" * 80)
    logger.info("🚀 TESTE PRÁTICO - API DE PAGAMENTOS EM LOTE - BANCO DO BRASIL")
    logger.info("=" * 80)
    logger.info("")
    logger.info("⚠️ ATENÇÃO: Este teste faz requisições REAIS à API do BB (sandbox)")
    logger.info("")
    logger.info("📋 Pré-requisitos:")
    logger.info("   1. Configure no .env:")
    logger.info("      - BB_PAYMENTS_CLIENT_ID")
    logger.info("      - BB_PAYMENTS_CLIENT_SECRET")
    logger.info("      - BB_PAYMENTS_DEV_APP_KEY")
    logger.info("      - BB_PAYMENTS_BASIC_AUTH (opcional)")
    logger.info("   2. Verifique se as credenciais estão corretas")
    logger.info("   3. Certifique-se de estar em ambiente sandbox")
    logger.info("")
    
    tests = [
        ("Listar Lotes", test_listar_lotes),
        ("Criar Lote (Exemplo)", test_criar_lote_exemplo),
        ("Consultar Lote", test_consultar_lote),
        ("Uso via Agent", test_via_agent),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ Erro ao executar teste '{test_name}': {e}", exc_info=True)
            results.append((test_name, False))
        logger.info("")
    
    # Resumo
    logger.info("=" * 80)
    logger.info("📊 RESUMO DOS TESTES")
    logger.info("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        logger.info(f"   {test_name}: {status}")
    
    logger.info("")
    logger.info(f"Total: {passed}/{total} testes passaram")
    
    if passed == total:
        logger.info("")
        logger.info("🎉 TODOS OS TESTES PASSARAM!")
    else:
        logger.warning("")
        logger.warning("⚠️ ALGUNS TESTES FALHARAM")
        logger.warning("   Verifique:")
        logger.warning("   - Se as credenciais estão configuradas corretamente")
        logger.warning("   - Se o scope 'pagamento-lote' está autorizado")
        logger.warning("   - Se a URL da API está correta")
    
    logger.info("")
    logger.info("💡 Próximos passos:")
    logger.info("   1. Para criar um lote real, edite o script e descomente o código")
    logger.info("   2. Ajuste os valores (agência, conta, pagamentos)")
    logger.info("   3. Execute novamente")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
