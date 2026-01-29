from __future__ import annotations

import io
import logging
from flask import Blueprint, jsonify, request, render_template, send_file

from services.mercante_afrmm_pagamentos_service import MercanteAfrmmPagamentosService

logger = logging.getLogger(__name__)

mercante_bp = Blueprint("mercante", __name__)


@mercante_bp.route("/api/mercante/afrmm/pagamentos", methods=["GET"])
def listar_pagamentos_afrmm():
    """
    Lista pagamentos AFRMM gravados (SQL Server com fallback para SQLite).

    Query params:
    - processo: "GYM.0050/25" (opcional)
    - ce: "1325..." (opcional)
    - limite: int (opcional, default 50, max 200)
    """
    processo = (request.args.get("processo") or "").strip().upper() or None
    ce = (request.args.get("ce") or "").strip() or None
    limite_raw = (request.args.get("limite") or "").strip()
    try:
        limite = int(limite_raw) if limite_raw else 50
    except Exception:
        limite = 50

    svc = MercanteAfrmmPagamentosService()
    resultado = svc.listar(ce_mercante=ce, processo_referencia=processo, limite=limite)
    status = 200 if resultado.get("sucesso") else 500
    return jsonify(resultado), status


@mercante_bp.route("/mercante/afrmm/pagamentos", methods=["GET"])
def listar_pagamentos_afrmm_view():
    """
    View (HTML) para visualizar pagamentos AFRMM.
    Usa o mesmo service do endpoint /api/mercante/afrmm/pagamentos.
    """
    processo = (request.args.get("processo") or "").strip().upper() or None
    ce = (request.args.get("ce") or "").strip() or None
    limite_raw = (request.args.get("limite") or "").strip()
    try:
        limite = int(limite_raw) if limite_raw else 50
    except Exception:
        limite = 50

    svc = MercanteAfrmmPagamentosService()
    resultado = svc.listar(ce_mercante=ce, processo_referencia=processo, limite=limite)
    # Renderiza mesmo se der erro (mostra mensagem amigável)
    return render_template(
        "mercante_afrmm_pagamentos.html",
        processo=processo,
        ce=ce,
        limite=limite,
        resultado=resultado,
    )


@mercante_bp.route("/api/mercante/arquivo/<int:file_id>", methods=["GET"])
def baixar_arquivo_sql(file_id: int):
    """
    Serve um arquivo armazenado como BLOB no SQL Server (mAIke_assistente).
    Usado para comprovantes Mercante (AFRMM) sem depender do FS em downloads/.
    
    Query params:
    - format: "pdf" (opcional) - Se fornecido, tenta retornar PDF em vez de PNG
    """
    try:
        from utils.sql_server_adapter import get_sql_adapter
        from services.sql_server_arquivos_service import obter_arquivo_por_id
        from pathlib import Path
        import os

        format_requested = (request.args.get("format") or "").strip().lower()
        quer_pdf = format_requested == "pdf"

        sql_adapter = get_sql_adapter()
        if not sql_adapter:
            return jsonify({"sucesso": False, "erro": "SQL_ADAPTER_NAO_DISPONIVEL"}), 500

        row = obter_arquivo_por_id(sql_adapter=sql_adapter, file_id=file_id)
        if not row:
            return jsonify({"sucesso": False, "erro": "ARQUIVO_NAO_ENCONTRADO"}), 404

        # ✅ NOVO (26/01/2026): Se PDF foi solicitado, tentar retornar PDF do filesystem
        if quer_pdf:
            filename_original = row.get("filename") or f"arquivo_{file_id}"
            # Tentar encontrar PDF correspondente no filesystem
            try:
                # Buscar screenshot_relpath do pagamento AFRMM correspondente
                from services.mercante_afrmm_pagamentos_service import MercanteAfrmmPagamentosService
                svc = MercanteAfrmmPagamentosService()
                # Buscar pagamento que tem esse receipt_file_id
                # (precisamos buscar na tabela MERCANTE_AFRMM_PAGAMENTO)
                from services.sql_server_mercante_afrmm_pagamentos_schema import TABLE_FULL
                query = f"SELECT TOP 1 screenshot_relpath FROM {TABLE_FULL} WHERE receipt_file_id = {file_id}"
                r_query = sql_adapter.execute_query(query, database="mAIke_assistente", notificar_erro=False)
                if r_query and r_query.get("success") and r_query.get("data"):
                    rows = r_query.get("data") or []
                    if rows and len(rows) > 0:
                        rel = rows[0].get("screenshot_relpath")
                        if rel:
                            rel_clean = rel.replace("downloads/", "") if rel.startswith("downloads/") else rel
                            png_path = Path(rel_clean)
                            pdf_path = png_path.with_suffix('.pdf')
                            project_root = Path(__file__).parent.parent
                            downloads_dir = project_root / "downloads"
                            pdf_abs = downloads_dir / pdf_path
                            
                            if pdf_abs.exists():
                                # PDF existe - retornar PDF
                                with open(pdf_abs, "rb") as f:
                                    pdf_content = f.read()
                                return send_file(
                                    io.BytesIO(pdf_content),
                                    mimetype="application/pdf",
                                    as_attachment=False,
                                    download_name=pdf_path.name,
                                    max_age=3600,
                                )
                            elif png_path.suffix.lower() == '.png':
                                # PDF não existe mas PNG existe - tentar converter
                                png_abs = downloads_dir / png_path
                                if png_abs.exists():
                                    try:
                                        from utils.png_to_pdf import converter_png_para_pdf
                                        pdf_gerado = converter_png_para_pdf(str(png_abs), str(pdf_abs))
                                        if pdf_gerado and Path(pdf_gerado).exists():
                                            with open(pdf_gerado, "rb") as f:
                                                pdf_content = f.read()
                                            return send_file(
                                                io.BytesIO(pdf_content),
                                                mimetype="application/pdf",
                                                as_attachment=False,
                                                download_name=pdf_path.name,
                                                max_age=3600,
                                            )
                                    except Exception as e_conv:
                                        logger.debug(f"Erro ao converter PNG para PDF (file_id={file_id}): {e_conv}")
            except Exception as e_pdf:
                logger.debug(f"Erro ao buscar PDF para file_id={file_id}: {e_pdf}")
            # Se chegou aqui, PDF não está disponível - retornar PNG mesmo

        # Retornar PNG (padrão ou fallback)
        content = row.get("content_bytes") or b""
        if not content:
            return jsonify({"sucesso": False, "erro": "ARQUIVO_VAZIO"}), 404

        filename = row.get("filename") or f"arquivo_{file_id}"
        mime = row.get("mime_type") or "application/octet-stream"

        return send_file(
            io.BytesIO(content),
            mimetype=mime,
            as_attachment=False,
            download_name=filename,
            max_age=3600,
        )
    except Exception as e:
        logger.warning(f"⚠️ Erro ao servir arquivo SQL (id={file_id}): {e}", exc_info=True)
        return jsonify({"sucesso": False, "erro": "ERRO_INTERNO"}), 500

