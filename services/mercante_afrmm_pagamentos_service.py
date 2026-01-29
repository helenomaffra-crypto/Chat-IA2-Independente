"""
MercanteAfrmmPagamentosService

Consulta pagamentos AFRMM gravados:
- Preferência: SQL Server `mAIke_assistente` (auditoria/fonte de verdade)
- Fallback: SQLite (cache local)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MercanteAfrmmPagamentosService:
    def listar(
        self,
        *,
        ce_mercante: Optional[str] = None,
        processo_referencia: Optional[str] = None,
        limite: int = 50,
    ) -> Dict[str, Any]:
        lim = int(limite or 50)
        if lim <= 0:
            lim = 50
        if lim > 200:
            lim = 200

        # 1) Tentar SQL Server (mAIke_assistente)
        try:
            from utils.sql_server_adapter import get_sql_adapter
            from services.sql_server_mercante_afrmm_pagamentos_schema import ensure_table

            sql_adapter = get_sql_adapter()
            if sql_adapter:
                try:
                    ensure_table(sql_adapter)
                except Exception:
                    pass

                # Considerar pagamento como "pago" tanto em success quanto em confirmed_external
                where = ["status IN ('success', 'confirmed_external')"]
                if ce_mercante:
                    ce = str(ce_mercante).strip().replace("'", "''")
                    where.append(f"ce_mercante = '{ce}'")
                if processo_referencia:
                    proc = (processo_referencia or "").strip().upper().replace("'", "''")
                    where.append(f"processo_referencia = '{proc}'")

                sql = f"""
                    SELECT TOP ({lim})
                        created_at, processo_referencia, ce_mercante, status,
                        pedido, banco, agencia, conta_corrente,
                        valor_afrmm, valor_total_debito,
                        screenshot_relpath, receipt_file_id
                    FROM mAIke_assistente.dbo.MERCANTE_AFRMM_PAGAMENTO
                    WHERE {' AND '.join(where)}
                    ORDER BY created_at DESC, id_mercante_afrmm_pagamento DESC
                """
                r = sql_adapter.execute_query(sql, database="mAIke_assistente", notificar_erro=False)
                if r and r.get("success"):
                    rows = r.get("data") or []
                    # ✅ Se SQL Server respondeu mas não há registros, cair para o fallback SQLite
                    if not rows:
                        raise RuntimeError("SEM_REGISTROS_SQL_SERVER")
                    items = []
                    for row in rows:
                        if not isinstance(row, dict):
                            continue
                        rel = row.get("screenshot_relpath")
                        receipt_id = row.get("receipt_file_id")
                        screenshot_url = None
                        pdf_url = None
                        
                        if receipt_id:
                            try:
                                receipt_id_int = int(receipt_id)
                                screenshot_url = f"/api/mercante/arquivo/{receipt_id_int}"
                                # ✅ NOVO (26/01/2026): URL para PDF via endpoint com ?format=pdf
                                # O endpoint vai buscar PDF no filesystem ou converter automaticamente
                                pdf_url = f"/api/mercante/arquivo/{receipt_id_int}?format=pdf"
                            except Exception:
                                screenshot_url = None
                                pdf_url = None
                        
                        if not screenshot_url:
                            screenshot_url = f"/api/download/{rel}" if rel else None
                        
                        # ✅ NOVO (26/01/2026): Tentar encontrar PDF correspondente no filesystem
                        # (apenas se não há receipt_file_id, pois nesse caso o arquivo está no SQL Server)
                        if not pdf_url and rel:
                            try:
                                from pathlib import Path
                                import os
                                # rel é relativo (ex: "mercante/xxx.png" ou "downloads/mercante/xxx.png")
                                # Remover "downloads/" se presente para construir caminho correto
                                rel_clean = rel.replace("downloads/", "") if rel.startswith("downloads/") else rel
                                png_path = Path(rel_clean)
                                pdf_path = png_path.with_suffix('.pdf')
                                # Verificar se PDF existe (mesmo diretório do PNG, relativo ao projeto)
                                project_root = Path(__file__).parent.parent
                                downloads_dir = project_root / "downloads"
                                png_abs = downloads_dir / png_path
                                pdf_abs = downloads_dir / pdf_path
                                
                                if pdf_abs.exists():
                                    # PDF já existe
                                    pdf_url = f"/api/download/{pdf_path}"
                                elif png_abs.exists() and png_abs.suffix.lower() == '.png':
                                    # ✅ NOVO (26/01/2026): PNG existe mas PDF não - converter automaticamente
                                    try:
                                        from utils.png_to_pdf import converter_png_para_pdf
                                        pdf_gerado = converter_png_para_pdf(str(png_abs), str(pdf_abs))
                                        if pdf_gerado and Path(pdf_gerado).exists():
                                            pdf_url = f"/api/download/{pdf_path}"
                                            logger.info(f"✅ PDF gerado automaticamente para PNG antigo: {rel} → {pdf_path}")
                                    except Exception as e_conv:
                                        logger.debug(f"Erro ao converter PNG antigo para PDF ({rel}): {e_conv}")
                            except Exception as e:
                                logger.debug(f"Erro ao verificar PDF para {rel}: {e}")
                        
                        item = dict(row)
                        item["screenshot_url"] = screenshot_url
                        item["pdf_url"] = pdf_url  # URL do PDF se existir
                        items.append(item)
                    return {
                        "sucesso": True,
                        "fonte": "sql_server",
                        "dados": {"itens": items, "limite": lim},
                    }
        except Exception as e:
            logger.debug(f"[Mercante][Service] SQL Server indisponível/erro: {e}")

        # 2) Fallback: SQLite
        try:
            from services.mercante_afrmm_pagamentos_repository import MercanteAfrmmPagamentosRepository

            repo = MercanteAfrmmPagamentosRepository()
            rows = repo.listar_sucessos(
                ce_mercante=ce_mercante,
                processo_referencia=processo_referencia,
                limite=lim,
            )
            items = []
            for row in rows:
                rel = row.get("screenshot_relpath")
                screenshot_url = f"/api/download/{rel}" if rel else None
                
                # ✅ NOVO (26/01/2026): Tentar encontrar PDF correspondente
                # Se não existir, tentar converter PNG antigo para PDF automaticamente
                pdf_url = None
                if rel:
                    try:
                        from pathlib import Path
                        import os
                        # rel é relativo (ex: "mercante/xxx.png" ou "downloads/mercante/xxx.png")
                        rel_clean = rel.replace("downloads/", "") if rel.startswith("downloads/") else rel
                        png_path = Path(rel_clean)
                        pdf_path = png_path.with_suffix('.pdf')
                        # Verificar se PDF existe (mesmo diretório do PNG, relativo ao projeto)
                        project_root = Path(__file__).parent.parent
                        downloads_dir = project_root / "downloads"
                        png_abs = downloads_dir / png_path
                        pdf_abs = downloads_dir / pdf_path
                        
                        if pdf_abs.exists():
                            # PDF já existe
                            pdf_url = f"/api/download/{pdf_path}"
                        elif png_abs.exists() and png_abs.suffix.lower() == '.png':
                            # ✅ NOVO (26/01/2026): PNG existe mas PDF não - converter automaticamente
                            try:
                                from utils.png_to_pdf import converter_png_para_pdf
                                pdf_gerado = converter_png_para_pdf(str(png_abs), str(pdf_abs))
                                if pdf_gerado and Path(pdf_gerado).exists():
                                    pdf_url = f"/api/download/{pdf_path}"
                                    logger.info(f"✅ PDF gerado automaticamente para PNG antigo: {rel} → {pdf_path}")
                            except Exception as e_conv:
                                logger.debug(f"Erro ao converter PNG antigo para PDF ({rel}): {e_conv}")
                    except Exception as e:
                        logger.debug(f"Erro ao verificar PDF para {rel}: {e}")
                
                item = dict(row)
                item["screenshot_url"] = screenshot_url
                item["pdf_url"] = pdf_url  # URL do PDF se existir
                items.append(item)
            return {
                "sucesso": True,
                "fonte": "sqlite_cache",
                "dados": {"itens": items, "limite": lim},
            }
        except Exception as e:
            return {
                "sucesso": False,
                "erro": "FALHA_LISTAGEM",
                "resposta": f"❌ Erro ao listar pagamentos AFRMM: {e}",
            }

