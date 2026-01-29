#!/usr/bin/env python3
"""
Script para testar manualmente o serviço de RSS do Siscomex.
Execute: python3 testar_rss_manual.py
"""
import sys
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("🧪 Testando serviço de RSS do Siscomex...")
        
        # Importar serviço
        from services.rss_siscomex_service import RssSiscomexService
        
        # Criar instância
        service = RssSiscomexService()
        logger.info(f"✅ Serviço criado com {len(service.feeds)} feeds")
        
        # Processar notícias
        logger.info("📰 Processando feeds RSS...")
        estatisticas = service.processar_novas_noticias()
        
        # Mostrar resultados
        print("\n" + "="*60)
        print("📊 RESULTADOS DO PROCESSAMENTO")
        print("="*60)
        print(f"Feeds processados: {estatisticas['feeds_processados']}")
        print(f"Notícias encontradas: {estatisticas['noticias_encontradas']}")
        print(f"Notícias novas: {estatisticas['noticias_novas']}")
        print(f"Notificações criadas: {estatisticas['notificacoes_criadas']}")
        print(f"Erros: {estatisticas['erros']}")
        print("="*60)
        
        if estatisticas['notificacoes_criadas'] > 0:
            print("\n✅ Notificações criadas com sucesso!")
            print("💡 Verifique no frontend (http://localhost:5001/chat-ia)")
        else:
            print("\nℹ️ Nenhuma notificação nova criada (pode ser que já existam todas)")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Erro ao testar RSS: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
