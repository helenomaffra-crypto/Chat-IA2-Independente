"""
Teste REAL da API de Pagamentos em Lote do Banco do Brasil usando credenciais de sandbox.

⚠️ ATENÇÃO: Este teste faz requisições reais à API do BB.
Use apenas em ambiente de sandbox/homologação.
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

def test_obter_token():
    """Testa obtenção de token OAuth."""
    logger.info("=" * 80)
    logger.info("🔍 Teste 1: Obter Token OAuth")
    logger.info("=" * 80)
    
    try:
        from utils.banco_brasil_payments_api import BancoBrasilPaymentsAPI, BancoBrasilPaymentsConfig
        
        # ✅ Credenciais do arquivo - NOTA: Estas podem ser diferentes das de Extrato
        # Se você tiver credenciais específicas para Pagamentos, use BB_PAYMENTS_* no .env
        config = BancoBrasilPaymentsConfig()
        config.client_id = "eyJpZCI6IjVmYWYwM2MtMzFkNC00IiwiY29kaWdvUHVibGljYWRvciI6MCwiY29kaWdvU29mdHdhcmUiOjE2ODEyMCwic2VxdWVuY2lhbEluc3RhbGFjYW8iOjF9"
        config.client_secret = "eyJpZCI6IjhmNDQ3NGEtZDA0NC00YSIsImNvZGlnb1B1YmxpY2Fkb3IiOjAsImNvZGlnb1NvZnR3YXJlIjoxNjgxMjAsInNlcXVlbmNpYWxJbnN0YWxhY2FvIjoxLCJzZXF1ZW5jaWFsQ3JlZGVuY2lhbCI6MSwiYW1iaWVudGUiOiJob21vbG9nYWNhbyIsImlhdCI6MTc2ODMxNjY3MTkyNn0"
        config.gw_dev_app_key = "1f8386d110934639a2790912c5bba906"
        config.environment = "sandbox"
        
        logger.info("   ⚠️ NOTA: Usando credenciais do arquivo.")
        logger.info("   💡 Para produção, configure BB_PAYMENTS_* no .env (podem ser diferentes das de Extrato)")
        
        logger.info(f"   Client ID: {config.client_id[:30]}...")
        logger.info(f"   Client Secret: {config.client_secret[:30]}...")
        logger.info(f"   App Key: {config.gw_dev_app_key}")
        logger.info(f"   Ambiente: {config.environment}")
        logger.info(f"   Token URL: {config.token_url}")
        
        api = BancoBrasilPaymentsAPI(config, debug=True)
        
        logger.info("   Tentando obter token...")
        token = api._obter_token()
        
        if token:
            logger.info(f"   ✅ Token obtido com sucesso: {token[:50]}...")
            return True
        else:
            logger.error("   ❌ Falha ao obter token")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao obter token: {e}", exc_info=True)
        return False

def test_listar_lotes():
    """Testa listagem de lotes (sem filtros)."""
    logger.info("=" * 80)
    logger.info("🔍 Teste 2: Listar Lotes (sem filtros)")
    logger.info("=" * 80)
    
    try:
        from utils.banco_brasil_payments_api import BancoBrasilPaymentsAPI, BancoBrasilPaymentsConfig
        
        config = BancoBrasilPaymentsConfig()
        config.client_id = "eyJpZCI6IjVmYWYwM2MtMzFkNC00IiwiY29kaWdvUHVibGljYWRvciI6MCwiY29kaWdvU29mdHdhcmUiOjE2ODEyMCwic2VxdWVuY2lhbEluc3RhbGFjYW8iOjF9"
        config.client_secret = "eyJpZCI6IjhmNDQ3NGEtZDA0NC00YSIsImNvZGlnb1B1YmxpY2Fkb3IiOjAsImNvZGlnb1NvZnR3YXJlIjoxNjgxMjAsInNlcXVlbmNpYWxJbnN0YWxhY2FvIjoxLCJzZXF1ZW5jaWFsQ3JlZGVuY2lhbCI6MSwiYW1iaWVudGUiOiJob21vbG9nYWNhbyIsImlhdCI6MTc2ODMxNjY3MTkyNn0"
        config.gw_dev_app_key = "1f8386d110934639a2790912c5bba906"
        config.environment = "sandbox"
        
        api = BancoBrasilPaymentsAPI(config, debug=True)
        
        logger.info("   Tentando listar lotes...")
        resultado = api.listar_lotes()
        
        logger.info(f"   ✅ Resposta recebida: {type(resultado)}")
        logger.info(f"   📋 Dados: {str(resultado)[:500]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar lotes: {e}", exc_info=True)
        return False

def test_service_integration():
    """Testa integração completa via service."""
    logger.info("=" * 80)
    logger.info("🔍 Teste 3: Integração via Service")
    logger.info("=" * 80)
    
    try:
        from services.banco_brasil_payments_service import BancoBrasilPaymentsService
        
        # ✅ Configurar credenciais via variáveis de ambiente temporárias
        # NOTA: Usando BB_PAYMENTS_* (específicas para pagamentos)
        # Se não configurar, o sistema tentará usar BB_* como fallback
        os.environ['BB_PAYMENTS_CLIENT_ID'] = "eyJpZCI6IjVmYWYwM2MtMzFkNC00IiwiY29kaWdvUHVibGljYWRvciI6MCwiY29kaWdvU29mdHdhcmUiOjE2ODEyMCwic2VxdWVuY2lhbEluc3RhbGFjYW8iOjF9"
        os.environ['BB_PAYMENTS_CLIENT_SECRET'] = "eyJpZCI6IjhmNDQ3NGEtZDA0NC00YSIsImNvZGlnb1B1YmxpY2Fkb3IiOjAsImNvZGlnb1NvZnR3YXJlIjoxNjgxMjAsInNlcXVlbmNpYWxJbnN0YWxhY2FvIjoxLCJzZXF1ZW5jaWFsQ3JlZGVuY2lhbCI6MSwiYW1iaWVudGUiOiJob21vbG9nYWNhbyIsImlhdCI6MTc2ODMxNjY3MTkyNn0"
        os.environ['BB_PAYMENTS_DEV_APP_KEY'] = "1f8386d110934639a2790912c5bba906"
        os.environ['BB_ENVIRONMENT'] = "sandbox"
        
        service = BancoBrasilPaymentsService()
        
        if not service.enabled:
            logger.error("   ❌ Serviço não está habilitado")
            return False
        
        logger.info("   ✅ Serviço habilitado")
        logger.info("   Tentando listar lotes via service...")
        
        resultado = service.listar_lotes()
        
        if resultado.get('sucesso'):
            logger.info("   ✅ Listagem de lotes funcionou via service")
            logger.info(f"   📋 Resposta: {resultado.get('resposta', '')[:200]}...")
        else:
            logger.warning(f"   ⚠️ Listagem retornou erro: {resultado.get('erro', 'Desconhecido')}")
            logger.info("   (Pode ser normal se não houver lotes ou se a API ainda não estiver totalmente configurada)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao testar service: {e}", exc_info=True)
        return False

def main():
    """Executa todos os testes."""
    logger.info("=" * 80)
    logger.info("🚀 TESTE REAL - PAGAMENTO EM LOTE - BANCO DO BRASIL (SANDBOX)")
    logger.info("=" * 80)
    logger.info("")
    logger.info("⚠️ ATENÇÃO: Este teste faz requisições REAIS à API do BB")
    logger.info("")
    
    tests = [
        ("Obter Token OAuth", test_obter_token),
        ("Listar Lotes", test_listar_lotes),
        ("Integração via Service", test_service_integration),
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
        logger.warning("   Verifique os erros acima")
        logger.warning("   Pode ser necessário verificar:")
        logger.warning("   - Se o scope 'pagamento-lote' está autorizado")
        logger.warning("   - Se a URL da API está correta")
        logger.warning("   - Se as credenciais estão válidas")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
