from __future__ import annotations

import logging
import sqlite3
from typing import Any, Dict
from flask import Blueprint, jsonify, request

from services.sync_status_repository import SyncStatusRepository

logger = logging.getLogger(__name__)

system_bp = Blueprint("system", __name__)


@system_bp.route("/api/system/sync-status", methods=["GET"])
def get_sync_status():
    """
    Retorna status das sincronizações (ex.: Kanban) para exibir na UI.
    """
    repo = SyncStatusRepository()
    kanban_result = repo.obter("kanban")
    kanban: Dict[str, Any] = kanban_result if kanban_result is not None else {}

    # Complementos: último updated_at do cache e contagem atual
    max_atualizado_em = None
    total_processos = None
    try:
        from db_manager import get_db_connection

        conn = get_db_connection()
        if conn:  # ✅ Verificar se conn não é None
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT MAX(atualizado_em) AS max_upd, COUNT(1) AS total FROM processos_kanban")
            row = cur.fetchone()
            conn.close()
            if row:
                max_atualizado_em = row["max_upd"]
                total_processos = row["total"]
    except Exception as e:
        logger.debug(f"[system_routes] erro ao ler processos_kanban: {e}")

    return jsonify(
        {
            "sucesso": True,
            "kanban": kanban,
            "processos_kanban": {
                "total": total_processos,
                "max_atualizado_em": max_atualizado_em,
            },
        }
    )


@system_bp.route("/api/system/sync-kanban", methods=["POST"])
def trigger_sync_kanban():
    """
    Dispara sincronização manual do Kanban (força atualização imediata).
    """
    try:
        from services.processo_kanban_service import ProcessoKanbanService

        svc = ProcessoKanbanService()
        sucesso = svc.sincronizar()
        if sucesso:
            return jsonify({"sucesso": True, "mensagem": "Sincronização concluída com sucesso"}), 200
        else:
            # Buscar último erro do sync_status para mensagem mais específica
            from services.sync_status_repository import SyncStatusRepository
            repo = SyncStatusRepository()
            status = repo.obter("kanban")
            erro_msg = status.get("last_error") if status else "Falha na sincronização (ver logs)"
            
            # Limpar mensagens técnicas para o usuário
            if "DNS não resolve" in erro_msg:
                erro_msg = "Servidor Kanban não encontrado. Verifique a configuração de rede."
            elif "API retornou" in erro_msg or "formato inválido" in erro_msg:
                erro_msg = "Servidor Kanban retornou resposta inválida. Verifique se o servidor está funcionando corretamente."
            elif "Erro de conexão" in erro_msg:
                erro_msg = "Não foi possível conectar ao servidor Kanban. Verifique se o servidor está online."
            
            return jsonify({"sucesso": False, "erro": erro_msg}), 500
    except Exception as e:
        logger.error(f"[system_routes] Erro ao disparar sync Kanban: {e}", exc_info=True)
        # Mensagem amigável para o usuário
        erro_msg = str(e)
        if "Unexpected token" in erro_msg or "JSON" in erro_msg:
            erro_msg = "Servidor retornou resposta inválida. Verifique se o servidor Kanban está funcionando corretamente."
        return jsonify({"sucesso": False, "erro": erro_msg}), 500

