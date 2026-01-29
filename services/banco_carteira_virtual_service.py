"""
Serviço para gestão de Carteira Virtual por Cliente e Compliance IN 1986/2020.

Responsável por:
1. Gerenciar saldos de aportes de clientes para pagamento de impostos.
2. Registrar logs de entrada (Aportes) e saída (Utilização em impostos).
3. Validar lastro financeiro para pagamentos aduaneiros.
"""
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime

from utils.sql_server_adapter import get_sql_adapter

logger = logging.getLogger(__name__)

class BancoCarteiraVirtualService:
    def __init__(self):
        self.sql_adapter = get_sql_adapter()

    def obter_saldo_cliente(self, cnpj_cliente: str) -> Decimal:
        """Retorna o saldo disponível na carteira virtual do cliente."""
        if not self.sql_adapter:
            return Decimal('0.00')
        
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj_cliente))
        query = f"SELECT saldo_disponivel FROM dbo.SALDO_RECURSO_CLIENTE WHERE cnpj_cliente = '{cnpj_limpo}'"
        
        resultado = self.sql_adapter.execute_query(query)
        if resultado.get('success') and resultado.get('data'):
            return Decimal(str(resultado['data'][0].get('saldo_disponivel', 0)))
        return Decimal('0.00')

    def registrar_aporte(self, cnpj_cliente: str, nome_cliente: str, id_movimentacao: int, valor: float) -> Dict[str, Any]:
        """Registra uma entrada de recurso (Crédito) na carteira do cliente."""
        if not self.sql_adapter:
            return {'sucesso': False, 'erro': 'SQL Server indisponível'}

        cnpj_limpo = ''.join(filter(str.isdigit, cnpj_cliente))
        valor_dec = Decimal(str(valor))

        try:
            # 1. Atualizar ou Criar Saldo do Cliente
            query_upsert = f"""
            IF EXISTS (SELECT 1 FROM dbo.SALDO_RECURSO_CLIENTE WHERE cnpj_cliente = '{cnpj_limpo}')
            BEGIN
                UPDATE dbo.SALDO_RECURSO_CLIENTE 
                SET saldo_disponivel = saldo_disponivel + {valor},
                    total_aportado = total_aportado + {valor},
                    ultima_atualizacao = GETDATE()
                WHERE cnpj_cliente = '{cnpj_limpo}'
            END
            ELSE
            BEGIN
                INSERT INTO dbo.SALDO_RECURSO_CLIENTE (cnpj_cliente, nome_cliente, saldo_disponivel, total_aportado)
                VALUES ('{cnpj_limpo}', '{nome_cliente.replace("'", "''")}', {valor}, {valor})
            END
            """
            self.sql_adapter.execute_query(query_upsert)

            # 2. Registrar no Log (Razão)
            saldo_atual = self.obter_saldo_cliente(cnpj_limpo)
            query_log = f"""
            INSERT INTO dbo.CARTEIRA_VIRTUAL_LOG 
            (cnpj_cliente, id_movimentacao_bancaria, tipo_operacao, valor, saldo_anterior, saldo_posterior, data_operacao, observacoes)
            VALUES 
            ('{cnpj_limpo}', {id_movimentacao}, 'APORTE', {valor}, {float(saldo_atual - valor_dec)}, {float(saldo_atual)}, GETDATE(), 'Aporte identificado via conciliação bancária')
            """
            self.sql_adapter.execute_query(query_log)

            # 3. Marcar a natureza na classificação
            query_natureza = f"""
            UPDATE dbo.LANCAMENTO_TIPO_DESPESA 
            SET natureza_recurso = 'APORTE_TRIBUTOS'
            WHERE id_movimentacao_bancaria = {id_movimentacao}
            """
            self.sql_adapter.execute_query(query_natureza)

            return {'sucesso': True, 'saldo_atual': float(saldo_atual)}
        except Exception as e:
            logger.error(f"Erro ao registrar aporte: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e)}

    def registrar_utilizacao(self, cnpj_cliente: str, id_movimentacao: int, valor: float, processo_ref: str) -> Dict[str, Any]:
        """Registra o uso de recurso (Débito) para pagamento de imposto."""
        if not self.sql_adapter:
            return {'sucesso': False, 'erro': 'SQL Server indisponível'}

        cnpj_limpo = ''.join(filter(str.isdigit, cnpj_cliente))
        valor_dec = Decimal(str(valor))
        saldo_anterior = self.obter_saldo_cliente(cnpj_limpo)

        try:
            # 1. Deduzir do Saldo
            query_update = f"""
            UPDATE dbo.SALDO_RECURSO_CLIENTE 
            SET saldo_disponivel = saldo_disponivel - {valor},
                total_utilizado = total_utilizado + {valor},
                ultima_atualizacao = GETDATE()
            WHERE cnpj_cliente = '{cnpj_limpo}'
            """
            self.sql_adapter.execute_query(query_update)

            # 2. Registrar no Log
            saldo_posterior = saldo_anterior - valor_dec
            query_log = f"""
            INSERT INTO dbo.CARTEIRA_VIRTUAL_LOG 
            (cnpj_cliente, id_movimentacao_bancaria, tipo_operacao, valor, saldo_anterior, saldo_posterior, processo_referencia, data_operacao, observacoes)
            VALUES 
            ('{cnpj_limpo}', {id_movimentacao}, 'UTILIZACAO', {valor}, {float(saldo_anterior)}, {float(saldo_posterior)}, '{processo_ref}', GETDATE(), 'Pagamento de impostos aduaneiros')
            """
            self.sql_adapter.execute_query(query_log)

            return {'sucesso': True, 'saldo_atual': float(saldo_posterior)}
        except Exception as e:
            logger.error(f"Erro ao registrar utilização: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e)}
