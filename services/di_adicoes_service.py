"""
DiAdicoesService

Consulta as adições de uma DI no Integra Comex (Serpro):
GET /declaracao-importacao/{numeroDI}/adicoes/

Suporta paginação via header "links" (rel=self, rel=next).
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _primeiro_valor(*vals: Any) -> Any:
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return None


def extrair_produto_de_adicao(adicao: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza campos mais comuns de "produto/mercadoria" dentro de uma adição.
    Não assume schema fixo: tenta chaves no nível raiz e dentro de `mercadoria`.
    """
    a = adicao if isinstance(adicao, dict) else {}
    merc = a.get('mercadoria') if isinstance(a.get('mercadoria'), dict) else {}
    dados_gerais = a.get('dadosGerais') if isinstance(a.get('dadosGerais'), dict) else {}
    itens_raw = a.get('itens') if isinstance(a.get('itens'), list) else []
    exportador = a.get('exportador') if isinstance(a.get('exportador'), dict) else {}
    fabricante = a.get('fabricante') if isinstance(a.get('fabricante'), dict) else {}
    export_end = exportador.get('endereco') if isinstance(exportador.get('endereco'), dict) else {}
    fab_end = fabricante.get('endereco') if isinstance(fabricante.get('endereco'), dict) else {}
    carga = a.get('carga') if isinstance(a.get('carga'), dict) else {}
    cond_venda = a.get('condicaoVenda') if isinstance(a.get('condicaoVenda'), dict) else {}

    itens: List[Dict[str, Any]] = []
    for it in itens_raw:
        if not isinstance(it, dict):
            continue
        itens.append({
            'numero_sequencial_item': _primeiro_valor(it.get('numeroSequencialItem'), it.get('numero_sequencial_item')),
            'descricao_mercadoria': _primeiro_valor(it.get('descricaoMercadoria'), it.get('descricao_mercadoria'), it.get('descricao')),
            'quantidade': _primeiro_valor(it.get('quantidade')),
            'unidade_medida': _primeiro_valor(it.get('unidadeMedida'), it.get('unidade_medida')),
            'valor_unitario': _primeiro_valor(it.get('valorUnitario'), it.get('valor_unitario')),
        })

    numero_adicao = _primeiro_valor(
        a.get('numeroAdicao'),
        a.get('numero_adicao'),
        a.get('adicao'),
        a.get('sequencia'),
        a.get('numero'),
        dados_gerais.get('numeroAdicao'),
    )

    ncm = _primeiro_valor(
        a.get('codigoNCM'),
        a.get('codigoNcm'),
        a.get('codigo_ncm'),
        a.get('ncm'),
        merc.get('codigoNCM'),
        merc.get('codigoNcm'),
        merc.get('codigo_ncm'),
        merc.get('ncm'),
    )

    descricao = _primeiro_valor(
        a.get('descricaoMercadoria'),
        a.get('descricao'),
        merc.get('descricaoMercadoria'),
        merc.get('descricao'),
        merc.get('descricaoProduto'),
        merc.get('produto'),
        (itens[0].get('descricao_mercadoria') if itens else None),
    )

    peso_liquido = _primeiro_valor(a.get('pesoLiquido'), merc.get('pesoLiquido'))
    peso_bruto = _primeiro_valor(a.get('pesoBruto'), merc.get('pesoBruto'))
    quantidade = _primeiro_valor(
        a.get('quantidade'),
        merc.get('quantidade'),
        (itens[0].get('quantidade') if itens else None),
    )
    unidade = _primeiro_valor(
        a.get('unidade'),
        merc.get('unidade'),
        a.get('unidadeMedida'),
        merc.get('unidadeMedida'),
        (itens[0].get('unidade_medida') if itens else None),
    )
    aplicacao = _primeiro_valor(a.get('aplicacao'), merc.get('aplicacao'))

    # Exportador/Fabricante (sem endereço completo — apenas nome + códigos de país)
    exportador_nome = _primeiro_valor(
        exportador.get('nome'),
        export_end.get('nome'),
        exportador.get('razaoSocial'),
        exportador.get('razao_social'),
    )
    fabricante_nome = _primeiro_valor(
        fabricante.get('nome'),
        fab_end.get('nome'),
        fabricante.get('razaoSocial'),
        fabricante.get('razao_social'),
    )
    pais_aquisicao_codigo = _primeiro_valor(
        exportador.get('codigoPaisAquisicaoMercadoria'),
        exportador.get('codigo_pais_aquisicao_mercadoria'),
        exportador.get('codigoPaisAquisicao'),
        exportador.get('paisAquisicaoCodigo'),
        exportador.get('codigoPaisAquisicaoMercadoriaCodigo'),
        exportador.get('codigoPaisAquisicaoMercadoria_Codigo'),
        # Fallback (quando o exportador não traz o campo): país de procedência da carga
        carga.get('dadosCargaPaisProcedenciaCodigo'),
    )
    pais_origem_codigo = _primeiro_valor(
        fabricante.get('codigoPaisOrigemMercadoria'),
        fabricante.get('codigo_pais_origem_mercadoria'),
        fabricante.get('codigoPaisOrigem'),
        fabricante.get('paisOrigemCodigo'),
        fabricante.get('codigoPaisOrigemMercadoriaCodigo'),
        fabricante.get('codigoPaisOrigemMercadoria_Codigo'),
    )

    # Valores (quando existirem)
    valor_moeda = _primeiro_valor(a.get('moeda'), merc.get('moeda'), a.get('codigoMoeda'), merc.get('codigoMoeda'))
    valor_unit = _primeiro_valor(a.get('valorUnitario'), merc.get('valorUnitario'), a.get('valor_unitario'))
    valor_total = _primeiro_valor(a.get('valorTotal'), merc.get('valorTotal'), a.get('valor_total'))

    # Condição de venda (Incoterm/Moeda) — útil para interpretar se inclui frete/seguro etc.
    incoterm = _primeiro_valor(
        cond_venda.get('incoterm'),
        a.get('incoterm'),
    )
    moeda_cond_venda = _primeiro_valor(
        cond_venda.get('moeda'),
        cond_venda.get('codigoMoeda'),
        cond_venda.get('codigoMoedaNegociada'),
    )

    return {
        'numero_adicao': numero_adicao,
        'ncm': ncm,
        'descricao': descricao,
        'quantidade': quantidade,
        'unidade': unidade,
        'peso_liquido': peso_liquido,
        'peso_bruto': peso_bruto,
        'aplicacao': aplicacao,
        'exportador_nome': exportador_nome,
        'pais_aquisicao_codigo': pais_aquisicao_codigo,
        'fabricante_nome': fabricante_nome,
        'pais_origem_codigo': pais_origem_codigo,
        'incoterm': incoterm,
        'moeda_condicao_venda': moeda_cond_venda,
        'moeda': valor_moeda,
        'valor_unitario': valor_unit,
        'valor_total': valor_total,
        'itens': itens,
        # Raw para debug/auditoria/UI avançada
        'raw': a,
    }


def _obter_di_base_url() -> str:
    """Replica a lógica de base URL do `DiPdfService` para DI."""
    env = os.getenv('INTEGRACOMEX_ENV', '').lower().strip()
    is_validacao = env in ('val', 'validacao', 'homologacao')

    di_base_url = (os.getenv('INTEGRACOMEX_DI_BASE_URL') or '').strip()
    if di_base_url:
        return di_base_url

    if is_validacao:
        return 'https://gateway.apiserpro.serpro.gov.br/integra-comex-di-hom/v1'
    return 'https://gateway.apiserpro.serpro.gov.br/integra-comex-di/v1'


def _parse_links_header(value: str) -> Dict[str, str]:
    """
    Parse do header "links" (ou "Link") conforme exemplo:
    URL ... rel="self" , URL ... rel="next"
    """
    links: Dict[str, str] = {}
    if not value or not isinstance(value, str):
        return links

    parts = [p.strip() for p in value.split(',') if p.strip()]
    for p in parts:
        m = re.search(r'([^;]+)\s*;\s*rel\s*=\s*"?([a-zA-Z0-9_-]+)"?', p)
        if not m:
            continue
        url = m.group(1).strip().strip('<>').strip()
        rel = m.group(2).strip()
        if url and rel:
            links[rel] = url
    return links


def _url_to_path(url: str) -> str:
    """Converte URL absoluta/relativa em path para `call_integracomex`."""
    if not url:
        return ''
    u = str(url).strip().strip('<>').strip()
    if u.startswith('http://') or u.startswith('https://'):
        p = urlparse(u)
        path = p.path or ''
        if p.query:
            path += '?' + p.query
        return path
    # já é path
    return u if u.startswith('/') else '/' + u


@dataclass
class DiAdicoesResult:
    sucesso: bool
    status_code: int
    adicoes: List[Dict[str, Any]]
    paginas_consultadas: int
    next_link: Optional[str] = None
    erro: Optional[str] = None


class DiAdicoesService:
    def consultar_adicoes(
        self,
        numero_di: str,
        *,
        max_paginas: int = 10,
        max_itens: int = 500,
        usou_api_publica_antes: bool = True,
    ) -> DiAdicoesResult:
        numero_di = (numero_di or '').strip()
        if not numero_di:
            return DiAdicoesResult(
                sucesso=False,
                status_code=400,
                adicoes=[],
                paginas_consultadas=0,
                erro='numero_di obrigatório',
            )

        di_base_url = _obter_di_base_url()
        path = f'/declaracao-importacao/{numero_di}/adicoes/'

        adicoes: List[Dict[str, Any]] = []
        paginas = 0
        next_url: Optional[str] = None

        from utils.integracomex_proxy import call_integracomex

        while True:
            paginas += 1
            status, body, headers = call_integracomex(
                path,
                method='GET',
                base_url_override=di_base_url,
                usou_api_publica_antes=usou_api_publica_antes,
                return_headers=True,
            )

            if status != 200:
                return DiAdicoesResult(
                    sucesso=False,
                    status_code=int(status),
                    adicoes=adicoes,
                    paginas_consultadas=paginas,
                    next_link=None,
                    erro=f'Integra Comex retornou status {status} ao consultar adições',
                )

            # Normalizar payload em lista
            if isinstance(body, list):
                for it in body:
                    if isinstance(it, dict):
                        adicoes.append(it)
            elif isinstance(body, dict):
                # tentativa de extrair array em chaves comuns
                candidatos = (
                    body.get('adicoes')
                    or body.get('itens')
                    or body.get('items')
                    or body.get('content')
                )
                if isinstance(candidatos, list):
                    for it in candidatos:
                        if isinstance(it, dict):
                            adicoes.append(it)
                else:
                    adicoes.append(body)

            # Limites
            if max_itens and len(adicoes) >= int(max_itens):
                adicoes = adicoes[: int(max_itens)]
                break
            if max_paginas and paginas >= int(max_paginas):
                break

            # Paginação: header links/link
            hv = None
            if isinstance(headers, dict):
                hv = headers.get('links') or headers.get('Links') or headers.get('Link') or headers.get('link')
            links = _parse_links_header(str(hv or ''))
            next_url = links.get('next') or links.get('rel-next')
            if not next_url:
                break

            path = _url_to_path(next_url)

        return DiAdicoesResult(
            sucesso=True,
            status_code=200,
            adicoes=adicoes,
            paginas_consultadas=paginas,
            next_link=next_url,
            erro=None,
        )

