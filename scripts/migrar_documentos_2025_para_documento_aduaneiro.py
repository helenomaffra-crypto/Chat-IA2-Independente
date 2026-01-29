#!/usr/bin/env python3
"""
Migração de documentos DI/DUIMP de 2025 para DOCUMENTO_ADUANEIRO.

Objetivo:
- Popular mAIke_assistente.dbo.DOCUMENTO_ADUANEIRO com todos os DI/DUIMP de 2025
- Fonte: Serpro.dbo (DI) e Duimp.dbo (DUIMP)
- Usa DocumentoHistoricoService para garantir consistência

Estratégia:
1. Buscar todos os DI de 2025 do Serpro.dbo
2. Buscar todos os DUIMP de 2025 do Duimp.dbo
3. Para cada documento, construir payload mínimo e gravar via DocumentoHistoricoService
4. Evitar duplicatas (verificar se já existe antes de gravar)

Uso:
  python3 scripts/migrar_documentos_2025_para_documento_aduaneiro.py
  python3 scripts/migrar_documentos_2025_para_documento_aduaneiro.py --ano 2024 --limit 1000
  python3 scripts/migrar_documentos_2025_para_documento_aduaneiro.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, date

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.sql_server_adapter import get_sql_adapter  # noqa: E402
from services.documento_historico_service import DocumentoHistoricoService  # noqa: E402
from services.db_policy_service import get_primary_database  # noqa: E402

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _sql_escape(s: str) -> str:
    """Escapa strings para SQL."""
    return (s or "").replace("'", "''")


def _buscar_documentos_existentes_batch(adapter, tipo: str, numeros: List[str]) -> set:
    """
    Busca todos os documentos existentes em lote (muito mais eficiente).
    
    Retorna set de números (strings) que já existem.
    """
    if not numeros or not tipo:
        return set()
    
    db = get_primary_database()
    tipo_esc = _sql_escape(tipo)
    
    # Query em lote (limitar a 500 números por vez para não exceder limites do SQL)
    batch_size = 500
    existing = set()
    
    for i in range(0, len(numeros), batch_size):
        batch_numeros = numeros[i:i + batch_size]
        conditions = []
        for num in batch_numeros:
            num_esc = _sql_escape(num)
            conditions.append(f"CAST(numero_documento AS VARCHAR(50)) = '{num_esc}'")
        
        if not conditions:
            continue
        
        q = f"""
            SELECT DISTINCT CAST(numero_documento AS VARCHAR(50)) AS numero_documento
            FROM {db}.dbo.DOCUMENTO_ADUANEIRO
            WHERE CAST(tipo_documento AS VARCHAR(50)) = '{tipo_esc}'
              AND ({' OR '.join(conditions)})
        """
        
        for attempt in range(3):  # Retry até 3 vezes
            try:
                r = adapter.execute_query(q, database=db, notificar_erro=False)
                if r and r.get("success") and r.get("data"):
                    for row in r.get("data", []):
                        if isinstance(row, dict):
                            num_doc = str(row.get("numero_documento") or "").strip()
                            if num_doc:
                                existing.add(num_doc)
                break  # Sucesso - sair do retry
            except Exception as e:
                error_str = str(e).lower()
                is_timeout = "timeout" in error_str or "ETIMEOUT" in error_str
                if not is_timeout or attempt == 2:
                    logger.warning(f"⚠️ Erro ao buscar documentos existentes (batch {i//batch_size + 1}): {e}")
                    break
                time.sleep(2 ** attempt)  # Backoff: 1s, 2s
    
    return existing


def _verificar_documento_existe(adapter, tipo: str, numero: str, versao: Optional[str] = None, max_retries: int = 3) -> bool:
    """
    Verifica se documento já existe em DOCUMENTO_ADUANEIRO.
    
    Com retry para lidar com timeouts intermitentes.
    """
    db = get_primary_database()
    tipo_esc = _sql_escape(tipo)
    num_esc = _sql_escape(numero)
    
    if versao:
        ver_esc = _sql_escape(versao)
        q = f"""
            SELECT TOP 1 id_documento
            FROM {db}.dbo.DOCUMENTO_ADUANEIRO
            WHERE CAST(tipo_documento AS VARCHAR(50)) = '{tipo_esc}'
              AND CAST(numero_documento AS VARCHAR(50)) = '{num_esc}'
              AND (versao_documento = '{ver_esc}' OR versao_documento IS NULL)
        """
    else:
        q = f"""
            SELECT TOP 1 id_documento
            FROM {db}.dbo.DOCUMENTO_ADUANEIRO
            WHERE CAST(tipo_documento AS VARCHAR(50)) = '{tipo_esc}'
              AND CAST(numero_documento AS VARCHAR(50)) = '{num_esc}'
        """
    
    # Retry com backoff exponencial
    for attempt in range(max_retries):
        try:
            r = adapter.execute_query(q, database=db, notificar_erro=False)
            if r and r.get("success"):
                return bool(r.get("data") and len(r.get("data", [])) > 0)
            # Se não foi sucesso mas não foi timeout, retornar False
            error = r.get("error", "") if r else ""
            if "timeout" not in error.lower() and "ETIMEOUT" not in error:
                return False
        except Exception as e:
            error_str = str(e).lower()
            if "timeout" not in error_str and "ETIMEOUT" not in error_str:
                # Erro não relacionado a timeout - não retry
                logger.debug(f"Erro não-timeout ao verificar {tipo} {numero}: {e}")
                return False
        
        # Timeout - fazer retry
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            logger.debug(f"⚠️ Timeout ao verificar {tipo} {numero} (tentativa {attempt + 1}/{max_retries}), aguardando {wait_time}s...")
            time.sleep(wait_time)
    
    # Após todos os retries, assumir que não existe (para não bloquear migração)
    logger.warning(f"⚠️ Não foi possível verificar se {tipo} {numero} existe após {max_retries} tentativas - assumindo que não existe")
    return False


def _buscar_dis_2025(adapter, ano: int, limite: Optional[int] = None) -> List[Dict[str, Any]]:
    """Busca todos os DI de 2025 do Serpro.dbo."""
    db = get_primary_database()
    limit_clause = f"TOP {limite}" if limite else ""
    
    # ✅ CORREÇÃO: Começar de Hi_Historico_Di e usar LEFT JOIN com PROCESSO_IMPORTACAO
    # Isso garante que trazemos DIs mesmo que o processo não exista na tabela principal
    q = f"""
        SELECT {limit_clause}
            COALESCE(p.numero_processo, 'ID:' + CAST(diH.idImportacao as VARCHAR(50))) AS processo_referencia,
            ddg.numeroDi AS numero_documento,
            ddg.situacaoDi AS situacao_documento,
            ddg.dataHoraSituacaoDi AS data_situacao,
            diDesp.canalSelecaoParametrizada AS canal_documento,
            diDesp.dataHoraRegistro AS data_registro,
            diDesp.dataHoraDesembaraco AS data_desembaraco,
            diDesp.dataHoraAutorizacaoEntrega AS data_entrega,
            ddg.sequencialRetificacao AS sequencial_retificacao,
            diH.idImportacao
        FROM Serpro.dbo.Hi_Historico_Di diH WITH (NOLOCK)
        INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot WITH (NOLOCK)
            ON diH.diId = diRoot.dadosDiId
        INNER JOIN Serpro.dbo.Di_Dados_Gerais ddg WITH (NOLOCK)
            ON diRoot.dadosGeraisId = ddg.dadosGeraisId
        LEFT JOIN Serpro.dbo.Di_Dados_Despacho diDesp WITH (NOLOCK)
            ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
        LEFT JOIN {db}.dbo.PROCESSO_IMPORTACAO p WITH (NOLOCK)
            ON p.id_importacao = diH.idImportacao
        WHERE (
            (diDesp.dataHoraRegistro IS NOT NULL AND YEAR(diDesp.dataHoraRegistro) = {ano})
            OR
            (diDesp.dataHoraRegistro IS NULL AND ddg.dataHoraSituacaoDi IS NOT NULL AND YEAR(ddg.dataHoraSituacaoDi) = {ano})
        )
        ORDER BY COALESCE(diDesp.dataHoraRegistro, ddg.dataHoraSituacaoDi) DESC
    """
    
    r = adapter.execute_query(q, database="Make", notificar_erro=False)
    if not r.get("success"):
        logger.error(f"❌ Erro ao buscar DI de {ano}: {r.get('error')}")
        return []
    
    rows = r.get("data") or []
    
    # ✅ Deduplicar por número_documento (pegar o mais recente por DI)
    seen = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        num_doc = str(row.get("numero_documento") or "").strip()
        if not num_doc:
            continue
        
        data_ord = row.get("data_ordenacao")
        if num_doc not in seen:
            seen[num_doc] = row
        else:
            # Se já existe, manter o mais recente (maior data_ordenacao)
            existing_data = seen[num_doc].get("data_ordenacao")
            if data_ord and (not existing_data or data_ord > existing_data):
                seen[num_doc] = row
    
    rows_dedup = list(seen.values())
    # Remover campo temporário data_ordenacao
    for row in rows_dedup:
        if isinstance(row, dict):
            row.pop("data_ordenacao", None)
    
    logger.info(f"✅ Encontrados {len(rows)} DI(s) de {ano} ({len(rows_dedup)} únicos após deduplicação)")
    return rows_dedup


def _buscar_duimps_2025(adapter, ano: int, limite: Optional[int] = None) -> List[Dict[str, Any]]:
    """Busca todos os DUIMP de 2025 do Duimp.dbo."""
    limit_clause = f"TOP {limite}" if limite else ""
    
    # ✅ CORREÇÃO: Usar DISTINCT com LEFT JOIN simples (mesmo padrão de registros_periodo_service.py)
    # A deduplicação será feita em Python por número
    q = f"""
        SELECT DISTINCT {limit_clause}
            COALESCE(d.numero_processo, 'ID:' + CAST(d.id_processo_importacao as VARCHAR(50))) AS processo_referencia,
            d.numero AS numero_documento,
            d.ultima_situacao AS situacao_documento,
            d.data_ultimo_evento AS data_situacao,
            drar.canal_consolidado AS canal_documento,
            d.data_registro AS data_registro,
            d.versao AS versao_documento
        FROM Duimp.dbo.duimp d WITH (NOLOCK)
        LEFT JOIN Duimp.dbo.duimp_resultado_analise_risco drar WITH (NOLOCK)
            ON d.duimp_id = drar.duimp_id
        WHERE d.data_registro IS NOT NULL
          AND YEAR(d.data_registro) = {ano}
        ORDER BY d.data_registro DESC
    """
    
    r = adapter.execute_query(q, database="Make", notificar_erro=False)
    if not r.get("success"):
        logger.error(f"❌ Erro ao buscar DUIMP de {ano}: {r.get('error')}")
        return []
    
    rows = r.get("data") or []
    
    # ✅ CORREÇÃO: Deduplicar por número DUIMP (ignorar versão para migração - vamos migrar apenas a versão mais recente)
    # O DISTINCT na query pode não funcionar se houver múltiplos registros de análise de risco com canais diferentes
    # Então fazemos deduplicação em Python por número (mantendo o mais recente)
    seen = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        num_doc = str(row.get("numero_documento") or "").strip()
        if not num_doc:
            continue
        
        # Chave: apenas número (ignorar versão - vamos migrar apenas a versão mais recente de cada número)
        # Se já vimos este número, manter o mais recente (maior data_registro)
        if num_doc not in seen:
            seen[num_doc] = row
        else:
            existing_data = seen[num_doc].get("data_registro")
            current_data = row.get("data_registro")
            if current_data and (not existing_data or current_data > existing_data):
                seen[num_doc] = row
    
    rows_dedup = list(seen.values())
    
    # Debug: contar números únicos
    numeros_unicos = set()
    for r in rows_dedup:
        num = str(r.get("numero_documento") or "").strip()
        if num:
            numeros_unicos.add(num)
    
    if len(rows_dedup) < len(rows):
        logger.info(f"✅ Encontrados {len(rows)} DUIMP(s) de {ano} ({len(rows_dedup)} únicos após deduplicação, {len(numeros_unicos)} números diferentes)")
        # Debug: mostrar alguns exemplos de números únicos
        if len(numeros_unicos) <= 10:
            logger.info(f"   📋 Números únicos: {', '.join(sorted(list(numeros_unicos))[:10])}")
        else:
            logger.info(f"   📋 Primeiros 10 números: {', '.join(sorted(list(numeros_unicos))[:10])}...")
    else:
        logger.info(f"✅ Encontrados {len(rows)} DUIMP(s) de {ano} ({len(numeros_unicos)} números diferentes)")
    return rows_dedup


def _construir_payload_di(row: Dict[str, Any]) -> Dict[str, Any]:
    """Constrói payload mínimo de DI a partir de dados do Serpro."""
    return {
        "numero": row.get("numero_documento"),
        "numeroDi": row.get("numero_documento"),
        "situacaoDi": row.get("situacao_documento"),
        "dataHoraSituacaoDi": row.get("data_situacao"),
        "canalSelecaoParametrizada": row.get("canal_documento"),
        "dataHoraRegistro": row.get("data_registro"),
        "dataHoraDesembaraco": row.get("data_desembaraco"),
        "dataHoraAutorizacaoEntrega": row.get("data_entrega"),
        "sequencialRetificacao": row.get("sequencial_retificacao"),
        "_fonte": "SERPRO_MIGRACAO",
    }


def _construir_payload_duimp(row: Dict[str, Any]) -> Dict[str, Any]:
    """Constrói payload mínimo de DUIMP a partir de dados do Duimp.dbo."""
    return {
        "numero": row.get("numero_documento"),
        "situacao": row.get("situacao_documento"),
        "ultimaSituacao": row.get("situacao_documento"),
        "ultimaSituacaoData": row.get("data_situacao"),
        "dataRegistro": row.get("data_registro"),
        "versaoDocumento": row.get("versao_documento"),
        "numeroProcesso": row.get("processo_referencia"),
        "_fonte": "DUIMP_DB_MIGRACAO",
    }


def _migrar_documento(
    adapter,
    svc: DocumentoHistoricoService,
    tipo: str,
    numero: str,
    processo_referencia: Optional[str],
    payload: Dict[str, Any],
    versao: Optional[str] = None,
    dry_run: bool = False,
    max_retries: int = 2,
) -> bool:
    """
    Migra um documento para DOCUMENTO_ADUANEIRO.
    
    Com retry para lidar com timeouts intermitentes.
    """
    # Verificar se já existe (com retry)
    try:
        if _verificar_documento_existe(adapter, tipo, numero, versao, max_retries=3):
            logger.debug(f"⏭️  {tipo} {numero} já existe - pulando")
            return False
    except Exception as e:
        logger.warning(f"⚠️ Erro ao verificar existência de {tipo} {numero}: {e} - continuando...")
        # Continuar mesmo com erro na verificação
    
    if dry_run:
        logger.info(f"🔍 [DRY-RUN] Migraria {tipo} {numero} (processo: {processo_referencia})")
        return True
    
    # Gravar via DocumentoHistoricoService (com retry)
    for attempt in range(max_retries):
        try:
            svc.detectar_e_gravar_mudancas(
                numero_documento=numero,
                tipo_documento=tipo,
                dados_novos=payload,
                fonte_dados="MIGRACAO_2025",
                api_endpoint="migracao_historica",
                processo_referencia=processo_referencia,
            )
            logger.info(f"✅ Migrado {tipo} {numero} (processo: {processo_referencia})")
            return True
        except Exception as e:
            error_str = str(e).lower()
            is_timeout = "timeout" in error_str or "ETIMEOUT" in error_str
            
            if not is_timeout or attempt == max_retries - 1:
                # Erro não-timeout ou último retry - logar e retornar False
                logger.error(f"❌ Erro ao migrar {tipo} {numero}: {e}", exc_info=not is_timeout)
                return False
            
            # Timeout - fazer retry
            wait_time = 2 ** attempt  # 1s, 2s
            logger.warning(f"⚠️ Timeout ao migrar {tipo} {numero} (tentativa {attempt + 1}/{max_retries}), aguardando {wait_time}s...")
            time.sleep(wait_time)
    
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrar documentos DI/DUIMP de 2025 para DOCUMENTO_ADUANEIRO.")
    parser.add_argument("--ano", type=int, default=2025, help="Ano para migrar (default: 2025).")
    parser.add_argument("--limit", type=int, default=None, help="Limite de documentos por tipo (default: sem limite).")
    parser.add_argument("--dry-run", action="store_true", help="Não grava; apenas mostra o que seria migrado.")
    parser.add_argument("--tipo", choices=["DI", "DUIMP", "TODOS"], default="TODOS", help="Tipo de documento para migrar.")
    args = parser.parse_args()

    adapter = get_sql_adapter()
    if not adapter:
        logger.error("❌ SQL Server adapter não disponível")
        return 2

    svc = DocumentoHistoricoService()
    
    total_migrados = 0
    total_pulados = 0
    total_erros = 0

    # Migrar DI
    if args.tipo in ("DI", "TODOS"):
        logger.info(f"\n{'='*60}")
        logger.info(f"📋 Migrando DI de {args.ano}")
        logger.info(f"{'='*60}\n")
        
        dis = _buscar_dis_2025(adapter, args.ano, args.limit)
        
        # ✅ OTIMIZAÇÃO: Buscar todos os DI existentes de uma vez (batch)
        if not args.dry_run and dis:
            logger.info(f"🔍 Verificando quais DI já existem (batch)...")
            numeros_di = [str(d.get("numero_documento") or "").strip() for d in dis if str(d.get("numero_documento") or "").strip()]
            numeros_di = [n for n in numeros_di if n]  # Remover vazios
            existing_di = _buscar_documentos_existentes_batch(adapter, "DI", numeros_di)
            logger.info(f"✅ {len(existing_di)} DI(s) já existem (de {len(numeros_di)} verificados)")
        else:
            existing_di = set()
        
        for idx, di in enumerate(dis, 1):
            numero = str(di.get("numero_documento") or "").strip()
            processo = str(di.get("processo_referencia") or "").strip()
            
            if not numero:
                total_pulados += 1
                continue
            
            # Verificar se já existe (usar cache em memória)
            ja_existe = False
            if args.dry_run:
                ja_existe = _verificar_documento_existe(adapter, "DI", numero, max_retries=1)
            else:
                ja_existe = numero in existing_di
            
            if ja_existe:
                if idx <= 5:  # Log apenas os primeiros 5 para não poluir
                    logger.info(f"⏭️  DI {numero} já existe - pulando")
                total_pulados += 1
                continue
            
            # Pequeno delay para não sobrecarregar SQL Server
            if idx > 1 and not args.dry_run:
                time.sleep(0.1)
            
            payload = _construir_payload_di(di)
            versao = None  # DI não tem versão explícita no Serpro
            
            sucesso = _migrar_documento(
                adapter, svc, "DI", numero, processo, payload, versao, args.dry_run
            )
            
            if sucesso:
                total_migrados += 1
                # Adicionar ao cache para próximas verificações
                if not args.dry_run:
                    existing_di.add(numero)
            else:
                # Verificar se realmente falhou ou se já existe (com retry)
                try:
                    if _verificar_documento_existe(adapter, "DI", numero, max_retries=2):
                        total_pulados += 1
                        if not args.dry_run:
                            existing_di.add(numero)
                    else:
                        total_erros += 1
                except Exception:
                    # Se não conseguir verificar, contar como erro
                    total_erros += 1

    # Migrar DUIMP
    if args.tipo in ("DUIMP", "TODOS"):
        logger.info(f"\n{'='*60}")
        logger.info(f"📋 Migrando DUIMP de {args.ano}")
        logger.info(f"{'='*60}\n")
        
        duimps = _buscar_duimps_2025(adapter, args.ano, args.limit)
        
        # ✅ OTIMIZAÇÃO: Buscar todos os DUIMP existentes de uma vez (batch)
        if not args.dry_run and duimps:
            logger.info(f"🔍 Verificando quais DUIMP já existem (batch)...")
            numeros_duimp = [str(d.get("numero_documento") or "").strip() for d in duimps if str(d.get("numero_documento") or "").strip()]
            numeros_duimp = [n for n in numeros_duimp if n]  # Remover vazios
            existing_duimp = _buscar_documentos_existentes_batch(adapter, "DUIMP", numeros_duimp)
            logger.info(f"✅ {len(existing_duimp)} DUIMP(s) já existem (de {len(numeros_duimp)} verificados)")
            if existing_duimp:
                logger.info(f"   📋 Exemplos de DUIMPs existentes: {list(existing_duimp)[:3]}")
        else:
            existing_duimp = set()
        
        # ✅ A deduplicação já foi feita em _buscar_duimps_2025, então podemos processar diretamente
        # Mas vamos fazer uma verificação final para garantir que não há duplicatas
        duimps_processar = []
        numeros_vistos = set()
        for duimp in duimps:
            numero = str(duimp.get("numero_documento") or "").strip()
            if not numero:
                continue
            if numero not in numeros_vistos:
                numeros_vistos.add(numero)
                duimps_processar.append(duimp)
        
        if len(duimps_processar) < len(duimps):
            logger.info(f"🔍 {len(duimps)} DUIMP(s) encontrados, {len(duimps_processar)} únicos após verificação final")
        
        for idx, duimp in enumerate(duimps_processar, 1):
            numero = str(duimp.get("numero_documento") or "").strip()
            processo = str(duimp.get("processo_referencia") or "").strip()
            versao = str(duimp.get("versao_documento") or "").strip() or None
            
            if not numero:
                total_pulados += 1
                continue
            
            # Verificar se já existe (usar cache em memória)
            ja_existe = False
            if args.dry_run:
                ja_existe = _verificar_documento_existe(adapter, "DUIMP", numero, versao, max_retries=1)
            else:
                ja_existe = numero in existing_duimp
            
            if ja_existe:
                if idx <= 5:  # Log apenas os primeiros 5 para não poluir
                    logger.info(f"⏭️  DUIMP {numero} já existe - pulando")
                total_pulados += 1
                continue
            
            # Pequeno delay para não sobrecarregar SQL Server
            if idx > 1 and not args.dry_run:
                time.sleep(0.1)
            
            # Log progresso a cada 10 documentos
            if idx % 10 == 0:
                logger.info(f"📋 Processando DUIMP {idx}/{len(duimps_processar)}... (migrados: {total_migrados}, pulados: {total_pulados})")
            
            payload = _construir_payload_duimp(duimp)
            
            sucesso = _migrar_documento(
                adapter, svc, "DUIMP", numero, processo, payload, versao, args.dry_run
            )
            
            if sucesso:
                total_migrados += 1
                # Adicionar ao cache para próximas verificações
                if not args.dry_run:
                    existing_duimp.add(numero)
                if idx <= 5 or total_migrados <= 5:  # Log primeiros 5
                    logger.info(f"✅ Migrado DUIMP {numero} (processo: {processo})")
            else:
                # Verificar se realmente falhou ou se já existe (com retry)
                try:
                    if _verificar_documento_existe(adapter, "DUIMP", numero, versao, max_retries=2):
                        total_pulados += 1
                        if not args.dry_run:
                            existing_duimp.add(numero)
                        if idx <= 5:  # Log primeiros 5
                            logger.info(f"⏭️  DUIMP {numero} já existe (verificado após falha) - pulando")
                    else:
                        total_erros += 1
                        if idx <= 5:  # Log primeiros 5 erros
                            logger.warning(f"❌ Erro ao migrar DUIMP {numero} (processo: {processo})")
                except Exception as e:
                    # Se não conseguir verificar, contar como erro
                    total_erros += 1
                    if idx <= 5:  # Log primeiros 5 erros
                        logger.warning(f"❌ Exceção ao verificar DUIMP {numero}: {e}")

    # Resumo
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 RESUMO DA MIGRAÇÃO ({args.ano})")
    logger.info(f"{'='*60}")
    logger.info(f"✅ Migrados: {total_migrados}")
    logger.info(f"⏭️  Pulados (já existiam): {total_pulados}")
    logger.info(f"❌ Erros: {total_erros}")
    logger.info(f"📋 Total processado: {total_migrados + total_pulados + total_erros}")
    
    if args.dry_run:
        logger.info(f"\n⚠️  MODO DRY-RUN: Nenhum dado foi gravado")
    
    return 0 if total_erros == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
