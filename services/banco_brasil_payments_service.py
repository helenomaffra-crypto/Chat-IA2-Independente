"""
Serviço para integração com API de Pagamentos em Lote do Banco do Brasil.

Wrapper para facilitar integração com o sistema mAIke.
Baseado na documentação oficial: https://developers.bb.com.br
"""
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Importar do módulo interno
try:
    from utils.banco_brasil_payments_api import BancoBrasilPaymentsAPI, BancoBrasilPaymentsConfig
    BB_PAYMENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ Não foi possível importar banco_brasil_payments_api: {e}")
    BB_PAYMENTS_AVAILABLE = False
    BancoBrasilPaymentsAPI = None
    BancoBrasilPaymentsConfig = None


class BancoBrasilPaymentsService:
    """Serviço para integração com API de Pagamentos em Lote do Banco do Brasil."""
    
    def __init__(self):
        """Inicializa o serviço."""
        self.api: Optional[BancoBrasilPaymentsAPI] = None
        self.enabled = BB_PAYMENTS_AVAILABLE
        
        if not self.enabled:
            logger.warning("⚠️ API de Pagamentos em Lote do Banco do Brasil não disponível")
            return
        
        try:
            config = BancoBrasilPaymentsConfig()
            
            # Validar se credenciais estão configuradas
            if not config.client_id or not config.client_secret or not config.gw_dev_app_key:
                logger.warning("⚠️ Credenciais do Banco do Brasil (Pagamentos) não configuradas no .env")
                logger.warning("⚠️ Configure: BB_PAYMENTS_CLIENT_ID, BB_PAYMENTS_CLIENT_SECRET, BB_PAYMENTS_DEV_APP_KEY")
                logger.warning("⚠️ NOTA: Cada API (Extrato e Pagamento) tem credenciais SEPARADAS - não há fallback")
                self.enabled = False
                return
            
            self.api = BancoBrasilPaymentsAPI(config, debug=True)
            logger.info("✅ BancoBrasilPaymentsService inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar BancoBrasilPaymentsService: {e}", exc_info=True)
            self.enabled = False
    
    def iniciar_pagamento_lote(
        self,
        agencia: str,
        conta: str,
        pagamentos: List[Dict[str, Any]],
        data_pagamento: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inicia um pagamento em lote.
        
        Args:
            agencia: Agência da conta (4 dígitos)
            conta: Número da conta (sem dígito verificador)
            pagamentos: Lista de pagamentos
            data_pagamento: Data do pagamento YYYY-MM-DD (opcional)
        
        Returns:
            Dict com resultado contendo:
            - sucesso: bool
            - resposta: str (mensagem formatada)
            - dados: Dict (dados do lote criado)
            - erro: str (se houver)
        """
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ **API de Pagamentos em Lote do Banco do Brasil não está disponível.**\n\nVerifique se:\n- As credenciais BB_* estão configuradas no .env\n- As dependências estão instaladas'
            }
        
        try:
            resultado = self.api.iniciar_pagamento_lote(
                agencia=agencia,
                conta=conta,
                pagamentos=pagamentos,
                data_pagamento=data_pagamento
            )
            
            # Formatar resposta
            id_lote = resultado.get('idLote') or resultado.get('id_lote') or resultado.get('id')
            status = resultado.get('status', 'PENDENTE')
            
            resposta = f"✅ **Pagamento em Lote Iniciado!**\n\n"
            resposta += f"**ID do Lote:** `{id_lote}`\n"
            resposta += f"**Status:** {status}\n"
            resposta += f"**Quantidade de Pagamentos:** {len(pagamentos)}\n"
            
            if resultado.get('pagamentos'):
                resposta += f"\n**Pagamentos:**\n"
                for i, pag in enumerate(resultado.get('pagamentos', []), 1):
                    valor = pag.get('valor', 0)
                    tipo = pag.get('tipo', 'BOLETO')
                    resposta += f"{i}. {tipo}: R$ {valor:,.2f}\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': resultado,
                'id_lote': id_lote,
                'status': status
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar pagamento em lote: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao iniciar pagamento em lote:** {str(e)}\n\n💡 Verifique se:\n- As credenciais estão corretas\n- A agência e conta estão corretas\n- Os dados dos pagamentos estão válidos'
            }
    
    def consultar_lote(self, id_lote: str) -> Dict[str, Any]:
        """
        Consulta status de um lote de pagamentos.
        
        Args:
            id_lote: ID do lote
        
        Returns:
            Dict com resultado contendo:
            - sucesso: bool
            - resposta: str (mensagem formatada)
            - dados: Dict (dados do lote)
            - erro: str (se houver)
        """
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ **API de Pagamentos em Lote do Banco do Brasil não está disponível.**'
            }
        
        try:
            resultado = self.api.consultar_lote(id_lote)
            
            status = resultado.get('status', 'DESCONHECIDO')
            id_lote = resultado.get('idLote') or resultado.get('id_lote') or resultado.get('id', id_lote)
            
            resposta = f"📋 **Status do Lote:**\n\n"
            resposta += f"**ID do Lote:** `{id_lote}`\n"
            resposta += f"**Status:** {status}\n"
            
            if resultado.get('pagamentos'):
                total = len(resultado.get('pagamentos', []))
                processados = sum(1 for p in resultado.get('pagamentos', []) if p.get('status') == 'PROCESSADO')
                resposta += f"**Pagamentos:** {processados}/{total} processados\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': resultado,
                'status': status
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao consultar lote: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao consultar lote:** {str(e)}'
            }
    
    def listar_lotes(
        self,
        agencia: Optional[str] = None,
        conta: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lista lotes de pagamentos.
        
        Args:
            agencia: Agência (opcional)
            conta: Conta (opcional)
            data_inicio: Data inicial YYYY-MM-DD (opcional)
            data_fim: Data final YYYY-MM-DD (opcional)
        
        Returns:
            Dict com resultado contendo:
            - sucesso: bool
            - resposta: str (mensagem formatada)
            - dados: List[Dict] (lista de lotes)
            - erro: str (se houver)
        """
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ **API de Pagamentos em Lote do Banco do Brasil não está disponível.**'
            }
        
        try:
            resultado = self.api.listar_lotes(
                agencia=agencia,
                conta=conta,
                data_inicio=data_inicio,
                data_fim=data_fim
            )
            
            lotes = resultado.get('lotes') or resultado.get('_content') or []
            
            resposta = f"📋 **Lotes de Pagamentos:**\n\n"
            if not lotes:
                resposta += "Nenhum lote encontrado.\n"
            else:
                for i, lote in enumerate(lotes, 1):
                    id_lote = lote.get('idLote') or lote.get('id_lote') or lote.get('id', 'N/A')
                    status = lote.get('status', 'N/A')
                    data = lote.get('dataPagamento') or lote.get('data_pagamento', 'N/A')
                    resposta += f"**{i}. Lote {id_lote}**\n"
                    resposta += f"   - Status: {status}\n"
                    resposta += f"   - Data: {data}\n\n"
            
            resposta += f"💡 **Total:** {len(lotes)} lote(s) encontrado(s)\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': lotes
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar lotes: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao listar lotes:** {str(e)}'
            }
