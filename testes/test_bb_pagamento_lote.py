"""
Script de teste para API de Pagamentos em Lote do Banco do Brasil.

Testa:
1. Importação dos módulos
2. Inicialização dos serviços
3. Configuração da API
4. Estrutura básica (sem fazer requisições reais)
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

def test_imports():
    """Testa se todos os imports funcionam."""
    logger.info("=" * 80)
    logger.info("🔍 Teste 1: Importação de módulos")
    logger.info("=" * 80)
    
    try:
        from utils.banco_brasil_payments_api import BancoBrasilPaymentsAPI, BancoBrasilPaymentsConfig
        logger.info("✅ utils.banco_brasil_payments_api importado com sucesso")
    except ImportError as e:
        logger.error(f"❌ Erro ao importar banco_brasil_payments_api: {e}")
        return False
    
    try:
        from services.banco_brasil_payments_service import BancoBrasilPaymentsService
        logger.info("✅ services.banco_brasil_payments_service importado com sucesso")
    except ImportError as e:
        logger.error(f"❌ Erro ao importar banco_brasil_payments_service: {e}")
        return False
    
    try:
        from services.agents.banco_brasil_agent import BancoBrasilAgent
        logger.info("✅ services.agents.banco_brasil_agent importado com sucesso")
    except ImportError as e:
        logger.error(f"❌ Erro ao importar banco_brasil_agent: {e}")
        return False
    
    return True

def test_config():
    """Testa a configuração da API."""
    logger.info("=" * 80)
    logger.info("🔍 Teste 2: Configuração da API")
    logger.info("=" * 80)
    
    try:
        from utils.banco_brasil_payments_api import BancoBrasilPaymentsConfig
        
        config = BancoBrasilPaymentsConfig()
        
        logger.info(f"   Client ID: {'✅ Configurado' if config.client_id else '❌ Não configurado'}")
        logger.info(f"   Client Secret: {'✅ Configurado' if config.client_secret else '❌ Não configurado'}")
        logger.info(f"   GW Dev App Key: {'✅ Configurado' if config.gw_dev_app_key else '❌ Não configurado'}")
        logger.info(f"   Ambiente: {config.environment}")
        logger.info(f"   Base URL: {config.base_url}")
        logger.info(f"   Token URL: {config.token_url}")
        
        if not config.client_id or not config.client_secret or not config.gw_dev_app_key:
            logger.warning("⚠️ Credenciais não configuradas no .env")
            logger.warning("   Configure: BB_CLIENT_ID, BB_CLIENT_SECRET, BB_DEV_APP_KEY")
            logger.info("   (Isso é esperado se o .env não estiver acessível ou não configurado)")
            # Não falhar o teste - apenas avisar
            return True  # Estrutura está correta, apenas falta configurar credenciais
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao testar configuração: {e}", exc_info=True)
        return False

def test_service_initialization():
    """Testa a inicialização do serviço."""
    logger.info("=" * 80)
    logger.info("🔍 Teste 3: Inicialização do Serviço")
    logger.info("=" * 80)
    
    try:
        from services.banco_brasil_payments_service import BancoBrasilPaymentsService
        
        service = BancoBrasilPaymentsService()
        
        logger.info(f"   Serviço habilitado: {'✅ Sim' if service.enabled else '❌ Não'}")
        logger.info(f"   API disponível: {'✅ Sim' if service.api else '❌ Não'}")
        
        if not service.enabled:
            logger.warning("⚠️ Serviço não está habilitado. Verifique as credenciais.")
            logger.info("   (Isso é esperado se as credenciais não estiverem configuradas)")
            # Não falhar o teste - estrutura está correta
            return True  # Estrutura está correta, apenas falta configurar credenciais
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar serviço: {e}", exc_info=True)
        return False

def test_agent_initialization():
    """Testa a inicialização do agent."""
    logger.info("=" * 80)
    logger.info("🔍 Teste 4: Inicialização do Agent")
    logger.info("=" * 80)
    
    try:
        from services.agents.banco_brasil_agent import BancoBrasilAgent
        
        agent = BancoBrasilAgent()
        
        logger.info(f"   Agent criado: ✅ Sim")
        logger.info(f"   Payments Service disponível: {'✅ Sim' if agent.payments_service else '❌ Não'}")
        logger.info(f"   Payments Service habilitado: {'✅ Sim' if agent.payments_service and agent.payments_service.enabled else '❌ Não'}")
        
        # Testar se os handlers estão registrados
        handlers = {
            'iniciar_pagamento_lote_bb': agent._iniciar_pagamento_lote,
            'consultar_lote_bb': agent._consultar_lote,
            'listar_lotes_bb': agent._listar_lotes,
        }
        
        for tool_name, handler in handlers.items():
            if handler:
                logger.info(f"   Handler '{tool_name}': ✅ Registrado")
            else:
                logger.error(f"   Handler '{tool_name}': ❌ Não registrado")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar agent: {e}", exc_info=True)
        return False

def test_tool_definitions():
    """Testa se as tools estão definidas."""
    logger.info("=" * 80)
    logger.info("🔍 Teste 5: Definições de Tools")
    logger.info("=" * 80)
    
    try:
        from services.tool_definitions import get_available_tools
        
        tools = get_available_tools()
        
        tool_names = [tool['function']['name'] for tool in tools if tool.get('type') == 'function']
        
        expected_tools = [
            'iniciar_pagamento_lote_bb',
            'consultar_lote_bb',
            'listar_lotes_bb'
        ]
        
        for tool_name in expected_tools:
            if tool_name in tool_names:
                logger.info(f"   Tool '{tool_name}': ✅ Definida")
            else:
                logger.error(f"   Tool '{tool_name}': ❌ Não encontrada")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao testar tool definitions: {e}", exc_info=True)
        return False

def test_tool_router():
    """Testa se o tool router está mapeando corretamente."""
    logger.info("=" * 80)
    logger.info("🔍 Teste 6: Tool Router")
    logger.info("=" * 80)
    
    try:
        from services.tool_router import ToolRouter
        
        router = ToolRouter()
        
        expected_mappings = {
            'iniciar_pagamento_lote_bb': 'banco_brasil',
            'consultar_lote_bb': 'banco_brasil',
            'listar_lotes_bb': 'banco_brasil'
        }
        
        for tool_name, expected_agent in expected_mappings.items():
            agent_name = router.tool_to_agent.get(tool_name)
            if agent_name == expected_agent:
                logger.info(f"   Tool '{tool_name}' → Agent '{agent_name}': ✅ Mapeado corretamente")
            else:
                logger.error(f"   Tool '{tool_name}' → Agent '{agent_name}' (esperado: '{expected_agent}'): ❌ Mapeamento incorreto")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao testar tool router: {e}", exc_info=True)
        return False

def main():
    """Executa todos os testes."""
    logger.info("=" * 80)
    logger.info("🚀 TESTE DE PAGAMENTO EM LOTE - BANCO DO BRASIL")
    logger.info("=" * 80)
    logger.info("")
    
    tests = [
        ("Importação de módulos", test_imports),
        ("Configuração da API", test_config),
        ("Inicialização do Serviço", test_service_initialization),
        ("Inicialização do Agent", test_agent_initialization),
        ("Definições de Tools", test_tool_definitions),
        ("Tool Router", test_tool_router),
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
        logger.info("")
        logger.info("💡 Próximos passos:")
        logger.info("   1. Configure as credenciais no .env (OBRIGATÓRIO - credenciais separadas):")
        logger.info("      - BB_PAYMENTS_CLIENT_ID, BB_PAYMENTS_CLIENT_SECRET, BB_PAYMENTS_DEV_APP_KEY")
        logger.info("      - BB_PAYMENTS_BASIC_AUTH (opcional - do arquivo 'basic=')")
        logger.info("   2. NOTA: Cada API (Extrato e Pagamento) tem credenciais SEPARADAS - não há fallback")
        logger.info("   3. registrationAccessToken NÃO é necessário (usado apenas no registro inicial)")
        logger.info("   4. Teste com requisições reais no sandbox")
        logger.info("   5. Verifique a documentação oficial: https://apoio.developers.bb.com.br/sandbox/spec/61bc753bd9b75d00121497a1")
        return 0
    else:
        logger.error("")
        logger.error("⚠️ ALGUNS TESTES FALHARAM")
        logger.error("   Verifique os erros acima e corrija antes de usar em produção")
        return 1

if __name__ == "__main__":
    sys.exit(main())
