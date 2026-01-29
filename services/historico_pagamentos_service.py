"""
Histórico de pagamentos (persistência).

Extraído de `db_manager.py` para reduzir o monolito e facilitar manutenção/testes.
Mantém a mesma assinatura pública via wrapper em `db_manager.salvar_historico_pagamento`.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from services.sqlite_db import get_db_connection

logger = logging.getLogger(__name__)


def salvar_historico_pagamento(
    payment_id: str,
    tipo_pagamento: str,
    banco: str,
    ambiente: str,
    status: str,
    valor: float,
    codigo_barras: Optional[str] = None,
    beneficiario: Optional[str] = None,
    vencimento: Optional[str] = None,
    agencia_origem: Optional[str] = None,
    conta_origem: Optional[str] = None,
    saldo_disponivel_antes: Optional[float] = None,
    saldo_apos_pagamento: Optional[float] = None,
    workspace_id: Optional[str] = None,
    payment_date: Optional[str] = None,
    dados_completos: Optional[Dict[str, Any]] = None,
    observacoes: Optional[str] = None,
    data_inicio: Optional[datetime] = None,
    data_efetivacao: Optional[datetime] = None,
) -> bool:
    """
    Salva ou atualiza histórico de pagamento.

    ✅ NOVO (13/01/2026): Grava em SQL Server (principal) e SQLite (cache).

    Args:
        payment_id: ID único do pagamento
        tipo_pagamento: 'BOLETO', 'PIX', 'TED', 'BARCODE'
        banco: 'SANTANDER', 'BANCO_DO_BRASIL'
        ambiente: 'SANDBOX', 'PRODUCAO'
        status: Status atual do pagamento
        valor: Valor do pagamento
        dados_completos: Dict com todos os dados retornados pela API (será convertido para JSON)
        data_inicio: Quando foi iniciado (None = agora)
        data_efetivacao: Quando foi efetivado (None = não efetivado ainda)

    Returns:
        True se salvou com sucesso (em pelo menos um banco), False caso contrário
    """
    sucesso_sqlite = False
    sucesso_sql_server = False

    # =========================================================================
    # 1. SALVAR NO SQL SERVER (PRINCIPAL)
    # =========================================================================
    try:
        from utils.sql_server_adapter import get_sql_adapter

        sql_adapter = get_sql_adapter()

        if sql_adapter:
            # Função auxiliar para escapar SQL
            def _escapar_sql(v):
                if v is None:
                    return "NULL"
                if isinstance(v, str):
                    v_esc = v.replace("'", "''")
                    return f"'{v_esc}'"
                if isinstance(v, (int, float)):
                    return str(v)
                if isinstance(v, bool):
                    return "1" if v else "0"
                v_str = str(v)
                v_esc = v_str.replace("'", "''")
                return f"'{v_esc}'"

            # Formatar datas para SQL Server
            def _formatar_data_sql(dt):
                if dt is None:
                    return "NULL"
                if isinstance(dt, str):
                    return f"'{dt}'"
                return f"'{dt.strftime('%Y-%m-%d %H:%M:%S')}'"

            # Converter dados_completos para JSON
            dados_json = json.dumps(dados_completos, ensure_ascii=False) if dados_completos else None
            if dados_json and len(dados_json) > 1000000:  # Limitar tamanho
                dados_json = dados_json[:1000000]

            # Verificar se já existe no SQL Server
            query_check = (
                "SELECT id_historico_pagamento FROM dbo.HISTORICO_PAGAMENTOS "
                f"WHERE payment_id = {_escapar_sql(payment_id)}"
            )
            resultado_check = sql_adapter.execute_query(query_check, database=sql_adapter.database)

            # Verificar se encontrou registro
            existe = False
            if resultado_check.get("success"):
                data = resultado_check.get("data", [])
                if data and len(data) > 0:
                    primeira_linha = data[0] if isinstance(data, list) else data
                    if primeira_linha:
                        if isinstance(primeira_linha, dict):
                            existe = primeira_linha.get("id_historico_pagamento") is not None
                        else:
                            existe = primeira_linha[0] is not None if len(primeira_linha) > 0 else False

            if existe:
                # Atualizar registro existente
                update_parts = [
                    f"tipo_pagamento = {_escapar_sql(tipo_pagamento)}",
                    f"banco = {_escapar_sql(banco)}",
                    f"ambiente = {_escapar_sql(ambiente)}",
                    f"status = {_escapar_sql(status)}",
                    f"valor = {valor}",
                    f"codigo_barras = {_escapar_sql(codigo_barras)}",
                    f"beneficiario = {_escapar_sql(beneficiario)}",
                    f"vencimento = {_escapar_sql(vencimento)}",
                    f"agencia_origem = {_escapar_sql(agencia_origem)}",
                    f"conta_origem = {_escapar_sql(conta_origem)}",
                    f"saldo_disponivel_antes = {saldo_disponivel_antes if saldo_disponivel_antes is not None else 'NULL'}",
                    f"saldo_apos_pagamento = {saldo_apos_pagamento if saldo_apos_pagamento is not None else 'NULL'}",
                    f"workspace_id = {_escapar_sql(workspace_id)}",
                    f"payment_date = {_escapar_sql(payment_date)}",
                    f"dados_completos = {_escapar_sql(dados_json)}",
                    f"observacoes = {_escapar_sql(observacoes)}",
                    "atualizado_em = GETDATE()",
                ]

                # Adicionar datas apenas se fornecidas
                if data_inicio is not None:
                    update_parts.append(f"data_inicio = {_formatar_data_sql(data_inicio)}")
                if data_efetivacao is not None:
                    update_parts.append(f"data_efetivacao = {_formatar_data_sql(data_efetivacao)}")

                query_update = f"""
                    UPDATE dbo.HISTORICO_PAGAMENTOS
                    SET {', '.join(update_parts)}
                    WHERE payment_id = {_escapar_sql(payment_id)}
                """

                resultado = sql_adapter.execute_query(query_update, database=sql_adapter.database)
                sucesso_sql_server = resultado.get("success", False)
            else:
                # Inserir novo registro
                campos = [
                    "payment_id",
                    "tipo_pagamento",
                    "banco",
                    "ambiente",
                    "status",
                    "valor",
                    "codigo_barras",
                    "beneficiario",
                    "vencimento",
                    "agencia_origem",
                    "conta_origem",
                    "saldo_disponivel_antes",
                    "saldo_apos_pagamento",
                    "workspace_id",
                    "payment_date",
                    "dados_completos",
                    "observacoes",
                    "data_inicio",
                    "data_efetivacao",
                    "criado_em",
                    "atualizado_em",
                ]

                valores = [
                    _escapar_sql(payment_id),
                    _escapar_sql(tipo_pagamento),
                    _escapar_sql(banco),
                    _escapar_sql(ambiente),
                    _escapar_sql(status),
                    str(valor),
                    _escapar_sql(codigo_barras),
                    _escapar_sql(beneficiario),
                    _escapar_sql(vencimento),
                    _escapar_sql(agencia_origem),
                    _escapar_sql(conta_origem),
                    str(saldo_disponivel_antes) if saldo_disponivel_antes is not None else "NULL",
                    str(saldo_apos_pagamento) if saldo_apos_pagamento is not None else "NULL",
                    _escapar_sql(workspace_id),
                    _escapar_sql(payment_date),
                    _escapar_sql(dados_json),
                    _escapar_sql(observacoes),
                    _formatar_data_sql(data_inicio or datetime.now()),
                    _formatar_data_sql(data_efetivacao),
                    "GETDATE()",
                    "GETDATE()",
                ]

                query_insert = f"""
                    INSERT INTO dbo.HISTORICO_PAGAMENTOS (
                        {', '.join(campos)}
                    ) VALUES (
                        {', '.join(valores)}
                    )
                """

                resultado = sql_adapter.execute_query(query_insert, database=sql_adapter.database)
                sucesso_sql_server = resultado.get("success", False)

            if sucesso_sql_server:
                logging.info(f"✅ Histórico de pagamento salvo no SQL Server: {payment_id}")
            else:
                erro_sql_server = (locals().get("resultado") or {}).get("error", "Erro desconhecido")
                logging.warning(f"⚠️ Erro ao salvar no SQL Server: {erro_sql_server}")
        else:
            logging.warning("⚠️ SQL Server adapter não disponível")
    except Exception as e:
        logging.warning(f"⚠️ Erro ao salvar histórico no SQL Server: {e}", exc_info=True)

    # =========================================================================
    # 2. SALVAR NO SQLITE (CACHE)
    # =========================================================================
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Converter dados_completos para JSON
        dados_json = json.dumps(dados_completos) if dados_completos else None

        # Verificar se já existe
        cursor.execute("SELECT id FROM historico_pagamentos WHERE payment_id = ?", (payment_id,))
        existe = cursor.fetchone()

        if existe:
            # Atualizar registro existente
            update_fields = [
                "tipo_pagamento = ?",
                "banco = ?",
                "ambiente = ?",
                "status = ?",
                "valor = ?",
                "codigo_barras = ?",
                "beneficiario = ?",
                "vencimento = ?",
                "agencia_origem = ?",
                "conta_origem = ?",
                "saldo_disponivel_antes = ?",
                "saldo_apos_pagamento = ?",
                "workspace_id = ?",
                "payment_date = ?",
                "dados_completos = ?",
                "observacoes = ?",
                "atualizado_em = CURRENT_TIMESTAMP",
            ]
            update_values = [
                tipo_pagamento,
                banco,
                ambiente,
                status,
                valor,
                codigo_barras,
                beneficiario,
                vencimento,
                agencia_origem,
                conta_origem,
                saldo_disponivel_antes,
                saldo_apos_pagamento,
                workspace_id,
                payment_date,
                dados_json,
                observacoes,
            ]

            # Adicionar data_inicio e data_efetivacao apenas se fornecidos
            if data_inicio is not None:
                update_fields.append("data_inicio = ?")
                update_values.append(data_inicio)
            if data_efetivacao is not None:
                update_fields.append("data_efetivacao = ?")
                update_values.append(data_efetivacao)

            update_values.append(payment_id)

            cursor.execute(
                f"""
                UPDATE historico_pagamentos SET
                    {', '.join(update_fields)}
                WHERE payment_id = ?
                """,
                update_values,
            )
        else:
            # Inserir novo registro
            cursor.execute(
                """
                INSERT INTO historico_pagamentos (
                    payment_id, tipo_pagamento, banco, ambiente, status, valor,
                    codigo_barras, beneficiario, vencimento,
                    agencia_origem, conta_origem,
                    saldo_disponivel_antes, saldo_apos_pagamento,
                    workspace_id, payment_date, dados_completos, observacoes,
                    data_inicio, data_efetivacao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payment_id,
                    tipo_pagamento,
                    banco,
                    ambiente,
                    status,
                    valor,
                    codigo_barras,
                    beneficiario,
                    vencimento,
                    agencia_origem,
                    conta_origem,
                    saldo_disponivel_antes,
                    saldo_apos_pagamento,
                    workspace_id,
                    payment_date,
                    dados_json,
                    observacoes,
                    data_inicio or datetime.now(),
                    data_efetivacao,
                ),
            )

        conn.commit()
        conn.close()
        sucesso_sqlite = True
        logging.info(f"✅ Histórico de pagamento salvo no SQLite (cache): {payment_id}")
    except Exception as e:
        logging.warning(f"⚠️ Erro ao salvar histórico no SQLite: {e}", exc_info=True)

    # Retornar sucesso se salvou em pelo menos um banco
    sucesso_total = sucesso_sql_server or sucesso_sqlite
    if sucesso_total:
        logging.info(
            f"✅ Histórico de pagamento salvo: {payment_id} ({tipo_pagamento}, {banco}, {status}) - "
            f"SQL Server: {sucesso_sql_server}, SQLite: {sucesso_sqlite}"
        )
    else:
        logging.error(f"❌ Falha ao salvar histórico de pagamento em ambos os bancos: {payment_id}")

    return sucesso_total

