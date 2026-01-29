"""
Robo (RPA) para Mercante - navegação até Pagamento -> Pagar AFRMM.

⚠️ Segurança / compliance:
- NÃO automatiza login por certificado digital nem tenta burlar controles.
- Fluxo recomendado: (A) login manual + CDP, ou (B) login via usuário/senha por ENV (sem hardcode).
- O script apenas navega nos menus e para antes de ações irreversíveis.
- Não coloque CPF/senha/certificado no código.
- Sessão: o script pode salvar cookies/localStorage (storage state) localmente para evitar relogar.
  ⚠️ Trate esse arquivo como sensível (equivale a “ficar logado”).

Pré-requisitos (local, fora do Cursor sandbox):
  pip install playwright
  python -m playwright install chromium

Como usar (macOS):
  1) Feche o Chrome (opcional, recomendado).
  2) Inicie Chrome com porta de debug:
     /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\
       --remote-debugging-port=9222 \\
       --user-data-dir=/tmp/chrome-mercante-profile
  3) Faça login no Mercante manualmente (certificado/CPF/senha).
  4) Rode este script:
     python scripts/mercante_bot.py --cdp http://127.0.0.1:9222 --acao pagar_afrmm

Login por usuário/senha (sem CDP):
  export MERCANTE_USER="seu_cpf"
  export MERCANTE_PASS="sua_senha"
  python scripts/mercante_bot.py --acao login_e_ir_pagar_afrmm --screenshot /tmp/mercante.png

Reusar sessão (evita relogar):
  # primeira vez (salva sessão)
  python scripts/mercante_bot.py --acao login_e_ir_pagar_afrmm --no_cdp --ignore_https_errors
  # depois (usa sessão salva)
  python scripts/mercante_bot.py --acao pagar_afrmm --no_cdp --ignore_https_errors
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from typing import Any, Dict, Optional, Tuple


MERCANTE_LOGIN_URL = "https://www.mercante.transportes.gov.br/g33159MT/jsp/logon.jsp"
MERCANTE_CONTROLLER_HINT = "MercanteController"
MERCANTE_PROFILE_DEFAULT = ".mercante_flow_profile.json"


def _pause_keep_open(*, seconds: int = 0) -> None:
    """
    Mantém o processo vivo para o usuário acompanhar a tela.

    ⚠️ Importante:
    - Quando rodando via Flask/subprocess (stdin NÃO é TTY), `input()` pode falhar/retornar imediatamente,
      fazendo o navegador fechar e o popup "piscar" e sumir.
    - Neste caso, fazemos um sleep por alguns segundos.
    """
    secs = int(seconds or 0)
    if sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
        try:
            input()
        except Exception:
            pass
        return
    # stdin não interativo (ex.: Flask). Segurar um tempo para permitir acompanhar popups.
    if secs <= 0:
        secs = 600  # 10 min padrão
    try:
        time.sleep(secs)
    except Exception:
        pass


def _wait_for_new_popup_page(context: Any, *, timeout_ms: int = 10_000) -> Optional[Any]:
    """
    Tenta detectar se um clique abriu uma nova aba/janela (popup).
    Retorna a nova Page (se surgir) ou None.
    """
    try:
        start_pages = set(getattr(context, "pages", []) or [])
    except Exception:
        start_pages = set()
    deadline = time.time() + (timeout_ms / 1000.0)
    while time.time() < deadline:
        try:
            pages_now = list(getattr(context, "pages", []) or [])
        except Exception:
            pages_now = []
        for p in pages_now:
            if p not in start_pages:
                return p
        time.sleep(0.2)
    return None


def _install_dialog_auto_accept(page: Any, *, debug: bool = False) -> None:
    """
    Instala handler para aceitar dialogs JS (confirm/alert/prompt).

    Playwright por padrão auto-dismiss dialogs se não houver handler, o que faz o popup "piscar".
    """
    try:
        def _on_dialog(dialog: Any) -> None:
            try:
                if debug:
                    try:
                        print(f"[debug] 🟢 Dialog detectado: type={dialog.type} message={dialog.message}", file=sys.stderr)
                    except Exception:
                        print("[debug] 🟢 Dialog detectado", file=sys.stderr)
                dialog.accept()
            except Exception:
                try:
                    dialog.accept()
                except Exception:
                    pass

        page.on("dialog", _on_dialog)
    except Exception:
        # Não falhar se não conseguir instalar handler
        pass


def _extrair_comprovante_pagamento(page: Any) -> Dict[str, Any]:
    """
    Extrai campos principais da tela de "Débito efetuado com sucesso" (quando disponível).
    Retorna dict vazio se não conseguir.
    """
    # Labels exibidos na tela do Mercante (podem variar em espaços/acentos)
    label_map = {
        "pedido": ["Nº. do Pedido", "No. do Pedido", "Nº do Pedido", "No do Pedido"],
        "ce_mercante": ["Nº. do CE-MERCANTE", "No. do CE-MERCANTE", "Nº do CE-MERCANTE", "No do CE-MERCANTE"],
        "consignatario": ["Consignatário", "Consignatario"],
        "banco": ["Banco"],
        "agencia": ["Agência", "Agencia"],
        "conta_corrente": ["Conta Corrente"],
        "valor_afrmm": ["Valor do AFRMM"],
        "valor_tarifa": ["Valor da Tarifa"],
        "valor_taxa_utilizacao": ["Valor da Taxa de Utilização do Mercante", "Valor da Taxa de Utilizacao do Mercante"],
        "valor_total_debito": ["Valor Total do Débito", "Valor Total do Debito"],
        "diagnostico_banco": ["Diagnóstico do Banco", "Diagnostico do Banco"],
    }

    js = r"""
    (labelMap) => {
      function norm(s) {
        return (s || '')
          .toString()
          .replace(/\s+/g, ' ')
          .trim()
          .toUpperCase()
          .normalize('NFD')
          .replace(/[\u0300-\u036f]/g, '');
      }
      const cells = Array.from(document.querySelectorAll('td, th'));
      const out = {};
      const wanted = {};
      for (const [k, arr] of Object.entries(labelMap)) {
        wanted[k] = arr.map(norm);
      }
      for (let i = 0; i < cells.length; i++) {
        const t = norm(cells[i].textContent || '');
        if (!t) continue;
        for (const [key, labels] of Object.entries(wanted)) {
          if (labels.includes(t)) {
            // valor geralmente na próxima célula da linha
            let val = '';
            const next = cells[i].nextElementSibling;
            if (next) val = (next.textContent || '').replace(/\s+/g, ' ').trim();
            if (!val) {
              // fallback: próximo td no DOM
              const nextTd = cells[i].parentElement ? cells[i].parentElement.querySelector('td:last-child') : null;
              if (nextTd) val = (nextTd.textContent || '').replace(/\s+/g, ' ').trim();
            }
            if (val) out[key] = val;
          }
        }
      }
      return out;
    }
    """

    for container in _iter_containers(page):
        try:
            data = container.evaluate(js, label_map)
            if isinstance(data, dict) and data:
                return data
        except Exception:
            continue
    return {}


def _try_load_dotenv_if_needed(*, debug: bool = False) -> None:
    """
    Carrega automaticamente variáveis do arquivo .env do projeto
    (somente se ainda não existirem no ambiente).

    Isso evita precisar usar `export` no terminal.
    """
    if os.getenv("MERCANTE_USER") and os.getenv("MERCANTE_PASS"):
        return

    # raiz do projeto: ../ (scripts/ -> projeto)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env_path = os.path.join(project_root, ".env")
    if not os.path.exists(env_path):
        return

    found_user = False
    found_pass = False
    mercante_keys_seen: list[str] = []
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for raw in f.readlines():
                line = raw.strip().lstrip("\ufeff")
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.replace("\u00a0", " ").strip()  # nbsp -> space
                # Suportar linhas como: export MERCANTE_USER=...
                if k.lower().startswith("export "):
                    k = k[7:].strip()
                k = k.strip().strip('"').strip("'")
                # Remover caracteres de controle/invisíveis na chave (ex.: \r no meio da chave)
                k_clean = "".join(ch for ch in k if (ch.isalnum() or ch == "_"))
                k_upper = k_clean.upper()
                # Remover comentários inline comuns: KEY=VAL # comment
                v = v.strip()
                if " #" in v:
                    v = v.split(" #", 1)[0].strip()
                v = v.strip().strip('"').strip("'")
                # Remover caracteres de controle/invisíveis no valor (ex: \r, \x03)
                v = "".join(ch for ch in v if ch.isprintable())
                if not k:
                    continue
                if "MERCANTE" in k_upper and len(mercante_keys_seen) < 50:
                    mercante_keys_seen.append(k_upper)
                # Aceitar alias comuns / truncamentos (ex.: MERCANTE_USE)
                if k_upper in ("MERCANTE_USER", "MERCANTE_USE"):
                    found_user = True
                    # normalizar para a forma padrão
                    k_clean = "MERCANTE_USER"
                    k_upper = "MERCANTE_USER"
                if k_upper == "MERCANTE_PASS":
                    found_pass = True
                    k_clean = "MERCANTE_PASS"
                    k_upper = "MERCANTE_PASS"
                # não sobrescrever variáveis já definidas
                if os.getenv(k_clean) is None or os.getenv(k_clean) == "":
                    os.environ[k_clean] = v
        if debug:
            loaded_user = bool(os.getenv("MERCANTE_USER"))
            loaded_pass = bool(os.getenv("MERCANTE_PASS"))
            print(
                f"[debug] .env carregado automaticamente ({env_path}). "
                f"found_user_line={found_user} found_pass_line={found_pass} | "
                f"MERCANTE_USER set={loaded_user} | MERCANTE_PASS set={loaded_pass}",
                file=sys.stderr,
            )
            if mercante_keys_seen:
                uniq = sorted(set(mercante_keys_seen))
                print(f"[debug] chaves 'MERCANTE*' vistas no .env: {uniq}", file=sys.stderr)
    except Exception as e:
        if debug:
            print(f"[debug] falha ao ler .env ({env_path}): {e}", file=sys.stderr)
        return


def _safe_dump_inputs(page) -> list[Dict[str, Any]]:
    """
    Retorna uma lista com atributos dos inputs (sem valores), para debug de seletores.
    Não inclui nenhum valor preenchido.
    """
    try:
        return page.evaluate(
            """() => Array.from(document.querySelectorAll('input')).map(i => ({
              type: (i.getAttribute('type') || '').toLowerCase(),
              id: i.id || '',
              name: i.name || '',
              placeholder: i.getAttribute('placeholder') || '',
              className: i.className || '',
              autocomplete: i.getAttribute('autocomplete') || '',
            }))"""
        )
    except Exception:
        return []


def _debug_dump_nav_candidates(page) -> None:
    """
    Dump (seguro) de elementos de navegação para ajustar seletores do menu pós-login.
    Não inclui valores de campos.
    """
    try:
        url = page.url
    except Exception:
        url = ""
    print(f"[debug] page url: {url}", file=sys.stderr)

    # Links candidatos
    try:
        links = page.evaluate(
            """() => Array.from(document.querySelectorAll('a')).map(a => ({
              text: (a.textContent || '').trim().slice(0, 80),
              href: a.getAttribute('href') || ''
            })).filter(x => x.text || x.href).slice(0, 600)"""
        )
    except Exception:
        links = []

    keywords = ("pag", "afrmm", "mercante", "menu")
    links_filtrados = [
        l
        for l in links
        if any(k in (l.get("text", "").lower()) for k in keywords)
        or any(k in (l.get("href", "").lower()) for k in keywords)
    ][:40]
    if links_filtrados:
        print(f"[debug] links candidatos (até 40): {links_filtrados}", file=sys.stderr)
    else:
        print("[debug] nenhum link candidato encontrado por keywords", file=sys.stderr)

    # Selects e opções (dropdowns) no documento principal + frames
    def _dump_selects(container, label: str):
        try:
            selects = container.evaluate(
                """() => Array.from(document.querySelectorAll('select')).map(s => ({
                  name: s.name || '',
                  id: s.id || '',
                  options: Array.from(s.options || []).map(o => (o.label || o.text || '').trim()).slice(0, 80)
                })).slice(0, 50)"""
            )
        except Exception:
            selects = []
        if not selects:
            return None
        relevantes = []
        for s in selects:
            opts = s.get("options") or []
            opts_rel = [o for o in opts if "afrmm" in (o or "").lower() or "pag" in (o or "").lower()]
            if opts_rel:
                relevantes.append({"name": s.get("name"), "id": s.get("id"), "options_rel": opts_rel[:30]})
        return {"label": label, "total": len(selects), "relevantes": relevantes}

    info_all = []
    main_info = _dump_selects(page, "main")
    if main_info:
        info_all.append(main_info)
    for idx, frame in enumerate(getattr(page, "frames", []) or []):
        fr_info = _dump_selects(frame, f"frame[{idx}]")
        if fr_info:
            info_all.append(fr_info)

    if info_all:
        print(f"[debug] selects encontrados: {info_all}", file=sys.stderr)
    else:
        print("[debug] nenhum <select> encontrado (main + frames)", file=sys.stderr)


def _mercante_needs_login(page) -> bool:
    """
    Heurística: detecta quando estamos no MercanteController "público" (sem sessão autenticada).
    Esse estado costuma ter link para logon.jsp e não tem frames/header/cmbAcoes.
    """
    try:
        # se já temos a UI carregada, não precisa login
        for c in _iter_containers(page):
            try:
                if c.locator("select[name='cmbAcoes']").count() > 0:
                    return False
            except Exception:
                continue
        # link visível para logon
        has_login_link = False
        try:
            has_login_link = page.locator("a[href*='logon.jsp']").count() > 0
        except Exception:
            has_login_link = False
        # sem frames úteis
        try:
            frames = list(getattr(page, "frames", []) or [])
            has_named_frames = any((getattr(fr, "name", "") or "").strip() for fr in frames)
        except Exception:
            has_named_frames = False
        return bool(has_login_link) and not has_named_frames
    except Exception:
        return True


def _wait_for_mercante_ui(page, *, timeout_ms: int = 25_000) -> bool:
    """
    Aguarda a UI do Mercante (frames/header ou select cmbAcoes) carregar.
    """
    import time

    deadline = time.time() + (timeout_ms / 1000.0)
    while time.time() < deadline:
        # cmbAcoes (header) é o melhor sinal
        for c in _iter_containers(page):
            try:
                if c.locator("select[name='cmbAcoes']").count() > 0:
                    return True
            except Exception:
                continue
        # ou frames nomeados (header/main)
        try:
            frames = list(getattr(page, "frames", []) or [])
            for fr in frames:
                try:
                    n = (getattr(fr, "name", "") or "").strip().lower()
                    if n in ("header", "main"):
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        try:
            page.wait_for_timeout(250)
        except Exception:
            pass
    return False


def _load_profile(path: str) -> Dict[str, Any]:
    try:
        if not path or not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_profile(path: str, data: Dict[str, Any]) -> None:
    try:
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _try_goto_known_urls(page, profile: Dict[str, Any], *, debug: bool = False) -> bool:
    """
    Tenta navegar direto usando URLs aprendidos (evita depender do clique na aba Pagamento).
    Retorna True se conseguiu chegar na tela do AFRMM (CE-Mercante).
    """
    # ⚠️ Importante:
    # No Mercante, muitas telas mudam apenas o conteúdo em frames (URL não muda).
    # Navegar via page.goto aqui tende a atrapalhar e pode quebrar a sessão.
    # Mantemos a função por compatibilidade, mas ela não faz navegação ativa.
    return False


def _containers_with_text(page, text: str) -> list[Any]:
    """Retorna uma lista de containers (page/frames) cujo body contém o texto."""
    text_l = (text or "").lower()
    found: list[Any] = []
    for container in _iter_containers(page):
        try:
            ok = container.evaluate(
                """(t) => {
                  const b = document.body;
                  if (!b) return false;
                  const txt = ((b.innerText || b.textContent || '') + ' ' +
                               (b.getAttribute && (b.getAttribute('alt') || b.getAttribute('title') || '') || '')
                              ).toLowerCase();
                  return txt.includes(t);
                }""",
                text_l,
            )
            if ok:
                found.append(container)
        except Exception:
            continue
    return found


def _find_container_with_select(page, select_name: str):
    """Encontra page/frame que contém select[name=select_name]."""
    for container in _iter_containers(page):
        try:
            if container.locator(f"select[name='{select_name}']").count() > 0:
                return container
        except Exception:
            continue
    return None


def _find_frame_by_name(page, frame_name: str):
    """Retorna o frame cujo name() == frame_name (case-insensitive), se existir."""
    wanted = (frame_name or "").strip().lower()
    if not wanted:
        return None
    for fr in getattr(page, "frames", []) or []:
        try:
            if (fr.name or "").strip().lower() == wanted:
                return fr
        except Exception:
            continue
    return None


def _debug_dump_frames(page) -> None:
    """Dump rápido de frames (name + url) para debug."""
    frames = list(getattr(page, "frames", []) or [])
    items = []
    for i, fr in enumerate(frames):
        try:
            items.append({"i": i, "name": (fr.name or ""), "url": (fr.url or "")[:120]})
        except Exception:
            continue
    if items:
        print(f"[debug] frames: {items}", file=sys.stderr)


def _click_menu_pagamento_no_header(page) -> bool:
    """
    Tenta clicar na aba/menu 'Pagamento' usando o frame 'header',
    igual o projeto CeMercante-main faz (Puppeteer).
    """
    header = _find_frame_by_name(page, "header")
    if not header:
        return False
    # Preferir href que troca o menu (padrão do Mercante: MENU-<...>)
    for sel in (
        'a[href*="MENU-PAGAMENTO"]',
        'a[href*="menu-pagamento"]',
        'a[href*="PAGAMENTO"]',
        'a:has-text("Pagamento")',
        'td:has-text("Pagamento")',
        'div:has-text("Pagamento")',
    ):
        try:
            loc = header.locator(sel).first
            if loc.count() == 0:
                continue
            loc.click(timeout=1500, force=True)
            return True
        except Exception:
            continue
    # Fallback: JS best-effort no header
    if _js_click_label_best_effort(header, "Pagamento"):
        return True
    # Fallback extra: procurar por onclick/href contendo "pagamento"
    js = r"""
    () => {
      const norm = (s) => (s || '').replace(/\s+/g,' ').trim().toLowerCase();
      const nodes = Array.from(document.querySelectorAll('a,td,div,span'));
      const hits = [];
      for (const el of nodes) {
        const txt = norm(el.textContent);
        const href = norm(el.getAttribute && el.getAttribute('href'));
        const oc = norm(el.getAttribute && el.getAttribute('onclick'));
        const hay = `${txt} ${href} ${oc}`;
        if (!hay.includes('pagamento')) continue;
        const tag = (el.tagName || '').toLowerCase();
        const clickableScore =
          (oc ? 200 : 0) + (href ? 150 : 0) + ((tag === 'a') ? 50 : 0);
        hits.push({ el, score: clickableScore - Math.min(hay.length, 120) });
      }
      hits.sort((a,b) => b.score - a.score);
      if (!hits.length) return false;
      try { hits[0].el.click(); } catch (e) { return false; }
      return true;
    }
    """
    try:
        return bool(header.evaluate(js))
    except Exception:
        return False


def _debug_dump_cmbacoes(page) -> None:
    """Debug: lista options atuais do select cmbAcoes em page/frames."""
    out = []
    js = r"""
    () => {
      const s = document.querySelector("select[name='cmbAcoes']");
      if (!s) return null;
      const opts = Array.from(s.options || []).map(o => (o.label || o.text || '').trim()).filter(Boolean);
      return { count: opts.length, sample: opts.slice(0, 25) };
    }
    """
    for container in _iter_containers(page):
        try:
            got = container.evaluate(js)
            if got:
                out.append(got)
        except Exception:
            continue
    if out:
        print(f"[debug] cmbAcoes options snapshot: {out}", file=sys.stderr)


def _debug_dump_bank_section(page) -> None:
    """Debug: imprime inputs detectados dentro da seção 'Informações Bancárias'."""
    js = r"""
    () => {
      const norm = (s) => (s || '').replace(/\s+/g,' ').trim().toLowerCase();
      const nodes = Array.from(document.querySelectorAll('td,th,div,span,font,b'));
      let headerNode = null;
      for (const n of nodes) {
        const t = norm(n.textContent);
        if (t.includes('informações bancárias') || t.includes('informacoes bancarias')) { headerNode = n; break; }
      }
      if (!headerNode) return { ok:false, reason:'section_header_not_found' };

      let scope = headerNode;
      for (let i=0; i<12 && scope; i++) {
        const tag = (scope.tagName || '').toLowerCase();
        if (tag === 'table' || tag === 'div' || tag === 'fieldset' || tag === 'form') break;
        scope = scope.parentElement;
      }
      scope = scope || headerNode.parentElement || headerNode;

      const inputs = Array.from(scope.querySelectorAll("input:not([type=hidden])")).map(i => ({
        type: (i.type || '').toLowerCase(),
        name: i.name || '',
        id: i.id || '',
        value: (i.value || ''),
        maxLength: (i.maxLength || null),
        disabled: !!i.disabled,
        readOnly: !!i.readOnly
      }));
      return { ok:true, found: inputs.length, inputs: inputs.slice(0, 20) };
    }
    """
    out = []
    for c in _iter_containers(page):
        try:
            got = c.evaluate(js)
            if got:
                out.append(got)
        except Exception:
            continue
    if out:
        print(f"[debug] bank section snapshot: {out}", file=sys.stderr)


def _wait_for_bank_screen(page, *, timeout_ms: int = 35_000) -> bool:
    """Espera a tela/trecho de 'Informações Bancárias' aparecer (com ou sem acento)."""
    return _wait_for_text_anywhere(page, "Informações Bancárias", timeout_ms=timeout_ms) or _wait_for_text_anywhere(
        page, "Informacoes Bancarias", timeout_ms=timeout_ms
    )


def _extrair_valor_debito_brl(page) -> Optional[Dict[str, Any]]:
    """
    Extrai "Valor do Débito" (BRL) da tela de Informações Bancárias.
    Retorna dict com:
      - valor_debito_raw (ex: "894,60")
      - valor_debito_float (ex: 894.60)
    """
    # Padrões tolerantes (com/sem acento; com espaços)
    rx = re.compile(
        r"valor\s+do\s+d[ée]bito\s+R?\$?\s*([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2})",
        re.IGNORECASE,
    )
    for c in _iter_containers(page):
        try:
            txt = c.evaluate("""() => (document.body && (document.body.innerText || '')) || ''""") or ""
        except Exception:
            continue
        m = rx.search(txt)
        if not m:
            continue
        raw = (m.group(1) or "").strip()
        try:
            num = float(raw.replace(".", "").replace(",", "."))
        except Exception:
            num = None
        return {"valor_debito_raw": raw, "valor_debito_float": num}
    return None


def _js_fill_bank_section_inputs(container, *, banco_codigo: str, agencia: str, conta_com_dv: str):
    """
    Fallback bem robusto: encontra a seção "Informações Bancárias" e preenche
    os 3 primeiros inputs text (banco, agência, conta) por ordem.
    Retorna dict com detalhes para debug.
    """
    js = r"""
    (banco, agencia, conta) => {
      const norm = (s) => (s || '').replace(/\s+/g,' ').trim().toLowerCase();
      const targets = [String(banco||''), String(agencia||''), String(conta||'')];
      if (!targets[0] || !targets[1] || !targets[2]) return { ok:false, reason:'missing_values' };

      // achar um nó que contenha "Informações Bancárias"
      const nodes = Array.from(document.querySelectorAll('td,th,div,span,font,b'));
      let headerNode = null;
      for (const n of nodes) {
        if (norm(n.textContent).includes('informações bancárias') || norm(n.textContent).includes('informacoes bancarias')) {
          headerNode = n;
          break;
        }
      }
      if (!headerNode) return { ok:false, reason:'section_header_not_found' };

      // subir até um container grande (table/div) e coletar inputs dentro
      let scope = headerNode;
      for (let i=0; i<10 && scope; i++) {
        const tag = (scope.tagName || '').toLowerCase();
        if (tag === 'table' || tag === 'div' || tag === 'fieldset' || tag === 'form') break;
        scope = scope.parentElement;
      }
      scope = scope || headerNode.parentElement || headerNode;

      // ⚠️ Ignorar checkbox/radio/etc (há um checkbox antes do campo do banco)
      const inputs = Array.from(scope.querySelectorAll("input[type='text'], input[type=''], input:not([type])"))
        .filter(i => true);
      const meta = inputs.slice(0, 10).map(i => ({
        name: i.name || '',
        id: i.id || '',
        type: (i.type || '').toLowerCase(),
        maxLength: i.maxLength || null
      }));
      if (inputs.length < 3) return { ok:false, reason:'not_enough_inputs', found: inputs.length, inputs: meta };

      // Se os 3 primeiros estão desabilitados, tentar clicar um checkbox na seção (se existir)
      const first3 = inputs.slice(0, 3);
      const allDisabled = first3.every(i => !!i.disabled || !!i.readOnly);
      let checkboxClicked = false;
      if (allDisabled) {
        const cb = scope.querySelector("input[type='checkbox']");
        if (cb && !cb.checked) {
          try {
            cb.click();
            cb.dispatchEvent(new Event('change', { bubbles: true }));
            checkboxClicked = true;
          } catch (e) {}
        }
      }
      // re-obter inputs após possível clique (algumas telas recriam DOM)
      const inputs2 = Array.from(scope.querySelectorAll("input[type='text'], input[type=''], input:not([type])"));
      const useInputs = (inputs2.length >= 3) ? inputs2 : inputs;

      const values = [targets[0], targets[1], targets[2]];
      const filled = [];
      for (let idx=0; idx<3; idx++) {
        const el = useInputs[idx];
        try {
          el.focus();
          el.value = values[idx];
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
          filled.push(true);
        } catch (e) {
          filled.push(false);
        }
      }
      const meta2 = useInputs.slice(0, 10).map(i => ({
        name: i.name || '',
        id: i.id || '',
        type: (i.type || '').toLowerCase(),
        maxLength: i.maxLength || null,
        disabled: !!i.disabled,
        readOnly: !!i.readOnly
      }));
      return { ok: filled.every(Boolean), filled, checkboxClicked, inputs: meta2, found: useInputs.length };
    }
    """
    try:
        return container.evaluate(js, banco_codigo, agencia, conta_com_dv)
    except Exception as e:
        return {"ok": False, "reason": f"js_eval_error: {e}"}


def _select_option_in_named_select(page, select_name: str, option_label: str, *, timeout_ms: int = 25_000) -> bool:
    """
    Seleciona option_label no select[name=select_name] (em page/frames),
    aguardando até a opção existir.
    """
    import time

    deadline = time.time() + (timeout_ms / 1000.0)
    option_css = f"select[name='{select_name}'] option:has-text('{option_label}')"
    while time.time() < deadline:
        for container in _iter_containers(page):
            try:
                if container.locator(option_css).count() == 0:
                    continue
                container.locator(f"select[name='{select_name}']").first.select_option(label=option_label)
                return True
            except Exception:
                continue
        try:
            page.wait_for_timeout(250)
        except Exception:
            pass
    return False


def _js_select_option_contains_in_named_select(
    page,
    select_name: str,
    option_text_contains: str,
    *,
    timeout_ms: int = 25_000,
) -> bool:
    """
    Seleciona uma option cujo texto CONTENHA option_text_contains dentro de select[name=select_name],
    usando JS (mais robusto para HTML antigo). Dispara eventos change/input.
    """
    import time

    wanted = (option_text_contains or "").strip().lower()
    if not wanted:
        return False

    js = r"""
    (selectName, wantedText) => {
      const s = document.querySelector(`select[name="${selectName}"]`);
      if (!s) return { ok:false, reason:'select_not_found' };
      const wanted = (wantedText || '').toLowerCase();
      const opts = Array.from(s.options || []);
      let idx = -1;
      for (let i=0; i<opts.length; i++) {
        const t = ((opts[i].label || opts[i].text || '') + '').replace(/\s+/g,' ').trim().toLowerCase();
        if (!t) continue;
        if (t.includes(wanted)) { idx = i; break; }
      }
      if (idx < 0) return { ok:false, reason:'option_not_found', sample: opts.slice(0, 20).map(o => ((o.label||o.text||'')+'').trim()) };
      try {
        s.selectedIndex = idx;
        s.dispatchEvent(new Event('input', { bubbles: true }));
        s.dispatchEvent(new Event('change', { bubbles: true }));
        return { ok:true, selected: ((opts[idx].label||opts[idx].text||'')+'').trim(), count: opts.length };
      } catch (e) {
        return { ok:false, reason:'select_error', error: String(e) };
      }
    }
    """

    deadline = time.time() + (timeout_ms / 1000.0)
    last_details = None
    while time.time() < deadline:
        for container in _iter_containers(page):
            try:
                details = container.evaluate(js, select_name, wanted)
                last_details = details
                if isinstance(details, dict) and details.get("ok"):
                    return True
            except Exception:
                continue
        try:
            page.wait_for_timeout(250)
        except Exception:
            pass
    return False


def learn_pagamento_flow(page, *, profile_path: str, debug: bool = False) -> Dict[str, Any]:
    """
    Modo interativo de aprendizado:
    - você clica em Pagamento
    - você seleciona Pagar AFRMM
    - salvamos as URLs observadas para o bot repetir automaticamente depois
    """
    profile = _load_profile(profile_path)
    if "urls" not in profile or not isinstance(profile.get("urls"), dict):
        profile["urls"] = {}

    try:
        profile["urls"]["controller_url"] = page.url
    except Exception:
        pass

    print(
        "🧠 APRENDER: clique manualmente na aba 'Pagamento'. Depois pressione ENTER aqui.",
        file=sys.stderr,
    )
    try:
        input()
    except Exception:
        pass
    try:
        profile["urls"]["pagamento_tab_url"] = page.url
    except Exception:
        pass
    if debug:
        print(f"[debug] aprendido pagamento_tab_url: {profile['urls'].get('pagamento_tab_url')}", file=sys.stderr)
        _debug_dump_nav_candidates(page)

    print(
        "🧠 APRENDER: agora selecione no combo 'Selecione uma opção' a opção 'Pagar AFRMM'. "
        "Quando a tela do AFRMM abrir, pressione ENTER aqui.",
        file=sys.stderr,
    )
    try:
        input()
    except Exception:
        pass

    # A tela do AFRMM pode trocar apenas conteúdo em frame (sem mudar URL).
    # Vamos aguardar o marcador "CE-Mercante" para confirmar.
    arrived = _wait_for_text_anywhere(page, "CE-Mercante", timeout_ms=25_000)
    profile["urls"]["pagar_afrmm_url"] = getattr(page, "url", "")
    profile["urls"]["arrived_afrmm"] = bool(arrived)

    # Capturar a dica técnica observada: o combo costuma ser select[name=cmbAcoes] em um frame.
    profile.setdefault("ui", {})
    profile["ui"]["select_name"] = "cmbAcoes"
    try:
        container = _find_container_with_select(page, "cmbAcoes")
        if container is not None:
            # best-effort: identificar índice do frame para debug
            try:
                frames = list(getattr(page, "frames", []) or [])
                if container in frames:
                    profile["ui"]["select_container"] = f"frame[{frames.index(container)}]"
                else:
                    profile["ui"]["select_container"] = "main"
            except Exception:
                pass
    except Exception:
        pass
    if debug:
        print(f"[debug] aprendido pagar_afrmm_url: {profile['urls'].get('pagar_afrmm_url')}", file=sys.stderr)
        print(f"[debug] arrived_afrmm={profile['urls'].get('arrived_afrmm')}", file=sys.stderr)
        _debug_dump_nav_candidates(page)

    _save_profile(profile_path, profile)
    print(f"✅ Fluxo aprendido e salvo em: {profile_path}", file=sys.stderr)
    return profile

def _find_frame_with_option(page, option_text: str):
    """Encontra o frame (ou page) que contém um <select> com uma opção específica."""
    option_css = f"select option:has-text('{option_text}')"

    # 1) Tentar no documento principal (CSS é mais confiável que role em HTML antigo)
    try:
        if page.locator(option_css).count() > 0:
            return page
    except Exception:
        pass

    # 2) Tentar em frames
    for frame in page.frames:
        try:
            if frame.locator(option_css).count() > 0:
                return frame
        except Exception:
            continue
    return None


def _iter_containers(page):
    """Itera sobre page + frames (para Mercante que usa frames)."""
    yield page
    for frame in getattr(page, "frames", []):
        yield frame


def _click_css_anywhere(page, selector: str) -> bool:
    """Tenta clicar em um seletor CSS no page ou frames."""
    for container in _iter_containers(page):
        try:
            loc = container.locator(selector).first
            if loc.count() == 0:
                continue
            loc.click(timeout=1500, force=True)
            return True
        except Exception:
            continue
    return False


def _js_click_text_anywhere(page, text: str) -> bool:
    """
    Fallback agressivo: clica via JS no primeiro elemento clicável cujo texto (trim) == text.
    Útil para menus antigos (td/div com onclick).
    """
    js = r"""
    (t) => {
      const target = (t || '').replace(/\s+/g,' ').trim().toLowerCase();
      if (!target) return false;
      // fallback amplo: procurar qualquer elemento que pareça clicável
      const candidates = Array.from(document.querySelectorAll('*'));
      const scored = [];
      for (const el of candidates) {
        const txt = (el.textContent || '').replace(/\s+/g,' ').trim().toLowerCase();
        const alt = (el.getAttribute && (el.getAttribute('alt') || el.getAttribute('title') || '') || '').trim().toLowerCase();
        const hay = (txt || alt);
        if (!hay) continue;
        if (!(hay === target || hay.includes(target))) continue;
        const tag = (el.tagName || '').toLowerCase();
        const hasOnclick = !!(el.getAttribute && el.getAttribute('onclick'));
        const hasHref = tag === 'a' && !!(el.getAttribute && el.getAttribute('href'));
        const isFormControl = (tag === 'button' || tag === 'input');
        const clickableScore = (hasOnclick ? 200 : 0) + (hasHref ? 150 : 0) + (isFormControl ? 100 : 0);
        // preferir elementos menores (mais específicos)
        const lenPenalty = Math.min(hay.length, 120);
        const score = clickableScore - lenPenalty;
        if (clickableScore > 0 || tag === 'td' || tag === 'div' || tag === 'span') {
          scored.push({ el, score });
        }
      }
      scored.sort((a,b) => b.score - a.score);
      if (scored.length === 0) return false;
      try { scored[0].el.click(); } catch (e) { return false; }
      return true;
    }
    """
    for container in _iter_containers(page):
        try:
            ok = container.evaluate(js, text)
            if ok:
                return True
        except Exception:
            continue
    return False


def _has_option_in_named_select(page, select_name: str, option_label: str) -> bool:
    """Checa (sem esperar) se existe option_label dentro de select[name=select_name] em page/frames."""
    option_css = f"select[name='{select_name}'] option:has-text('{option_label}')"
    for container in _iter_containers(page):
        try:
            if container.locator(option_css).count() > 0:
                return True
        except Exception:
            continue
    return False


def _find_frames_with_text(page, text: str) -> list[int]:
    """Retorna índices de frames cujo DOM contém o texto (case-insensitive)."""
    text_l = (text or "").lower()
    found: list[int] = []
    frames = list(getattr(page, "frames", []) or [])
    for idx, frame in enumerate(frames):
        try:
            ok = frame.evaluate(
                """(t) => (document.body && (document.body.innerText || '').toLowerCase().includes(t)) || false""",
                text_l,
            )
            if ok:
                found.append(idx)
        except Exception:
            continue
    return found


def _js_click_text_in_container(container, text: str) -> bool:
    """Clique via JS dentro de um container (page/frame) específico."""
    js = r"""
    (t) => {
      const target = (t || '').replace(/\s+/g,' ').trim().toLowerCase();
      if (!target) return false;
      const candidates = Array.from(document.querySelectorAll('*'));
      const scored = [];
      for (const el of candidates) {
        const txt = (el.textContent || '').replace(/\s+/g,' ').trim().toLowerCase();
        const alt = (el.getAttribute && (el.getAttribute('alt') || el.getAttribute('title') || '') || '').trim().toLowerCase();
        const hay = (txt || alt);
        if (!hay) continue;
        if (!(hay === target || hay.includes(target))) continue;
        const tag = (el.tagName || '').toLowerCase();
        const hasOnclick = !!(el.getAttribute && el.getAttribute('onclick'));
        const hasHref = tag === 'a' && !!(el.getAttribute && el.getAttribute('href'));
        const isFormControl = (tag === 'button' || tag === 'input');
        const clickableScore = (hasOnclick ? 200 : 0) + (hasHref ? 150 : 0) + (isFormControl ? 100 : 0);
        const lenPenalty = Math.min(hay.length, 120);
        const score = clickableScore - lenPenalty;
        if (clickableScore > 0 || tag === 'td' || tag === 'div' || tag === 'span') {
          scored.push({ el, score });
        }
      }
      scored.sort((a,b) => b.score - a.score);
      if (scored.length === 0) return false;
      try { scored[0].el.click(); } catch (e) { return false; }
      return true;
    }
    """
    try:
        return bool(container.evaluate(js, text))
    except Exception:
        return False


def _js_click_label_best_effort(container, label: str) -> bool:
    """
    Clique robusto para abas/menus antigos:
    - encontra um nó cujo texto/alt/title contenha 'label'
    - sobe na árvore até achar um ancestral com onclick/href
    - clica nesse ancestral (ou no próprio)
    """
    js = r"""
    (label) => {
      const target = (label || '').replace(/\s+/g,' ').trim().toLowerCase();
      if (!target) return false;

      const all = Array.from(document.querySelectorAll('*'));
      const candidates = [];

      for (const el of all) {
        const txt = (el.textContent || '').replace(/\s+/g,' ').trim().toLowerCase();
        const alt = (el.getAttribute && (el.getAttribute('alt') || el.getAttribute('title') || '') || '').trim().toLowerCase();
        if (!txt && !alt) continue;
        if (!(txt.includes(target) || alt.includes(target))) continue;

        let cur = el;
        for (let i = 0; i < 8 && cur; i++) {
          const tag = (cur.tagName || '').toLowerCase();
          const onclick = cur.getAttribute && cur.getAttribute('onclick');
          const href = (tag === 'a' && cur.getAttribute && cur.getAttribute('href')) || '';
          if (onclick || href) {
            candidates.push(cur);
            break;
          }
          cur = cur.parentElement;
        }
      }

      const uniq = Array.from(new Set(candidates));
      if (uniq.length === 0) return false;

      uniq.sort((a, b) => {
        const score = (x) => {
          const tag = (x.tagName || '').toLowerCase();
          const hasOnclick = !!(x.getAttribute && x.getAttribute('onclick'));
          const hasHref = tag === 'a' && !!(x.getAttribute && x.getAttribute('href'));
          const txt = (x.textContent || '').replace(/\s+/g,' ').trim();
          return (hasOnclick ? 100 : 0) + (hasHref ? 80 : 0) - Math.min(txt.length, 80);
        };
        return score(b) - score(a);
      });

      try { uniq[0].click(); } catch (e) { return false; }
      return true;
    }
    """
    try:
        return bool(container.evaluate(js, label))
    except Exception:
        return False


def _wait_for_text_anywhere(page, text: str, *, timeout_ms: int = 15_000) -> bool:
    """
    Aguarda aparecer um texto em qualquer frame/página.
    Retorna True se encontrou antes do timeout.
    """
    import time

    deadline = time.time() + (timeout_ms / 1000.0)
    while time.time() < deadline:
        for container in _iter_containers(page):
            try:
                if container.get_by_text(text, exact=False).count() > 0:
                    return True
            except Exception:
                continue
        try:
            page.wait_for_timeout(250)
        except Exception:
            pass
    return False


def _has_text_anywhere(page, text: str) -> bool:
    """Checagem rápida (sem esperar) se um texto existe em page/frames."""
    for container in _iter_containers(page):
        try:
            if container.get_by_text(text, exact=False).count() > 0:
                return True
        except Exception:
            continue
    return False


def _wait_for_container_with_option(page, option_text: str, *, timeout_ms: int = 20_000):
    """Espera até existir um frame/page com option_text no select."""
    import time

    deadline = time.time() + (timeout_ms / 1000.0)
    while time.time() < deadline:
        container = _find_frame_with_option(page, option_text=option_text)
        if container:
            return container
        try:
            page.wait_for_timeout(250)
        except Exception:
            pass
    return None


def _click_by_text_anywhere(page, text: str, *, exact: bool = True) -> bool:
    """
    Tenta clicar em link/botão/texto com determinado texto em page ou frames.
    Retorna True se clicou.
    """
    for container in _iter_containers(page):
        # HTML antigo do Mercante nem sempre tem roles/a11y; usar texto puro é mais confiável
        try:
            container.get_by_text(text, exact=exact).first.click(timeout=800, force=True)
            return True
        except Exception:
            pass
    return False


def _click_link_href_contains_anywhere(page, needle: str) -> bool:
    """
    Tenta clicar no primeiro <a> cujo href contém 'needle' (case-insensitive),
    em page ou frames.
    """
    needle_l = (needle or "").lower()
    for container in _iter_containers(page):
        try:
            anchors = container.locator("a[href]").all()
        except Exception:
            anchors = []
        for a in anchors[:200]:
            try:
                href = (a.get_attribute("href") or "").lower()
                if needle_l and needle_l in href:
                    a.click(timeout=1500)
                    return True
            except Exception:
                continue
    return False


def _fill_input_anywhere(page, selector: str, value: str) -> bool:
    """Tenta preencher um input por seletor CSS em page/frames."""
    v = (value or "").strip()
    if not v:
        return False
    for container in _iter_containers(page):
        try:
            loc = container.locator(selector).first
            if loc.count() == 0:
                continue
            loc.fill(v, timeout=2000)
            return True
        except Exception:
            continue
    return False


def _fill_input_by_label_text_anywhere(page, label_text: str, value: str) -> bool:
    """
    Heurística para HTML antigo: acha o input logo após um texto de label
    (CE-Mercante / Nr. da Parcela etc.), em page/frames.
    """
    v = (value or "").strip()
    if not v:
        return False
    # xpath mais tolerante: encontra um nó que contenha o texto e pega o próximo input
    xp = (
        "xpath=//*[contains(translate(normalize-space(string(.)), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ', "
        "'abcdefghijklmnopqrstuvwxyzáàâãéèêíìîóòôõúùûç'), "
        f"'{label_text.lower()}')]/following::input[1]"
    )
    for container in _iter_containers(page):
        try:
            loc = container.locator(xp).first
            if loc.count() == 0:
                continue
            loc.fill(v, timeout=2000)
            return True
        except Exception:
            continue
    return False


def _click_button_anywhere(page, text: str) -> bool:
    """Clica em botão/link com texto (Enviar/Limpar etc.) em page/frames."""
    return _click_by_text_anywhere(page, text, exact=True) or _click_by_text_anywhere(page, text, exact=False)


def _sanitize_env_value(raw: str) -> str:
    """
    Sanitiza valores vindos de env/.env:
    - remove caracteres não-imprimíveis (ex: \\x03)
    - remove comentários inline após '#'
    - trim de espaços/\\r/\\t e NBSP
    """
    if raw is None:
        return ""
    s = str(raw).replace("\u00a0", " ")
    # remover não-imprimíveis (inclui controles)
    s = "".join(ch for ch in s if ch.isprintable())
    s = s.strip()
    if "#" in s:
        # só tratar como comentário se houver espaço ou se for claramente um inline comment
        s = s.split("#", 1)[0].strip()
    return s


def _digits_only(raw: str) -> str:
    """Mantém apenas dígitos (útil para banco/agência)."""
    s = _sanitize_env_value(raw)
    return re.sub(r"\D+", "", s)


def _js_fill_input_for_label(container, label: str, value: str) -> bool:
    """
    Preenche, via JS, o primeiro input "próximo" a um label (mesma linha/área).
    É mais robusto para HTML antigo (tabelas do Mercante).
    """
    v = (value or "").strip()
    if not v:
        return False
    js = r"""
    (label, value) => {
      const target = (label || '').toLowerCase();
      const v = (value || '');
      if (!target || !v) return false;

      const norm = (s) => (s || '').replace(/\s+/g,' ').trim().toLowerCase();
      const nodes = Array.from(document.querySelectorAll('td,th,div,span,label,b,font'));

      for (const n of nodes) {
        const t = norm(n.textContent);
        if (!t || !t.includes(target)) continue;

        // subir até uma linha de tabela (tr) se existir
        let row = n;
        for (let i = 0; i < 6 && row; i++) {
          if (row.tagName && row.tagName.toLowerCase() === 'tr') break;
          row = row.parentElement;
        }

        const scope = (row && row.tagName && row.tagName.toLowerCase() === 'tr') ? row : n.parentElement || n;
        // ⚠️ Na tela do Mercante há checkbox antes do campo. Ignorar checkbox/radio/etc.
        const input = scope.querySelector("input[type='text'], input[type=''], input:not([type])");
        if (!input) continue;
        if (input.disabled || input.readOnly) continue;

        try {
          input.focus();
          input.value = v;
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        } catch (e) {
          continue;
        }
      }
      return false;
    }
    """
    try:
        return bool(container.evaluate(js, label, v))
    except Exception:
        return False


def preencher_afrmm_ce(page, *, ce_mercante: str, parcela: Optional[str] = None, clicar_enviar: bool = True) -> bool:
    """
    Preenche CE-Mercante (e opcional parcela) na tela Pagar AFRMM.
    Não confirma pagamento (apenas 'Enviar' da consulta).
    """
    # garantir que estamos na tela certa (texto aparece em frames)
    _wait_for_text_anywhere(page, "CE-Mercante", timeout_ms=25_000)

    # 1) tentar seletores por name/id (se existirem)
    filled_ce = (
        _fill_input_anywhere(page, "input[name*='ce' i]", ce_mercante)
        or _fill_input_anywhere(page, "input[id*='ce' i]", ce_mercante)
        or _fill_input_by_label_text_anywhere(page, "CE-Mercante", ce_mercante)
        or _fill_input_by_label_text_anywhere(page, "CE Mercante", ce_mercante)
    )

    filled_parcela = True
    if parcela:
        filled_parcela = (
            _fill_input_anywhere(page, "input[name*='parcela' i]", parcela)
            or _fill_input_anywhere(page, "input[id*='parcela' i]", parcela)
            or _fill_input_by_label_text_anywhere(page, "Nr. da Parcela", parcela)
            or _fill_input_by_label_text_anywhere(page, "Parcela", parcela)
        )

    if not filled_ce:
        return False
    if parcela and not filled_parcela:
        return False

    if clicar_enviar:
        _click_button_anywhere(page, "Enviar")
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10_000)
        except Exception:
            try:
                page.wait_for_timeout(1500)
            except Exception:
                pass
    return True


def preencher_dados_bancarios_afrmm(
    page,
    *,
    banco_codigo: str,
    agencia: str,
    conta_com_dv: str,
    debug: bool = False,
) -> bool:
    """
    Preenche os campos bancários na tela final do AFRMM:
    - Código do Banco
    - Cod. Agência (sem DV)
    - Conta Corrente (com DV)

    ⚠️ Não clica em "Pagar AFRMM".
    """
    # garantir que estamos na tela certa (pode estar em frame; com/sem acento)
    _wait_for_bank_screen(page, timeout_ms=35_000)

    # Sanitizar valores (evita casos como BB_CODIGO="001\\x03" ou comentário inline)
    banco_codigo = _digits_only(banco_codigo)
    agencia = _digits_only(agencia)
    conta_com_dv = _sanitize_env_value(conta_com_dv)
    # Conta pode ter DV com caractere (ex: X). Remover espaços e manter só [0-9A-Za-z]
    conta_com_dv = re.sub(r"[^0-9A-Za-z]+", "", conta_com_dv)

    ok1 = False
    ok2 = False
    ok3 = False

    # Preferir JS fill em cada container (main/frame) — mais robusto que XPATH following::input
    for c in _iter_containers(page):
        ok1 = ok1 or _js_fill_input_for_label(c, "Código do Banco", banco_codigo) or _js_fill_input_for_label(
            c, "Codigo do Banco", banco_codigo
        )
        ok2 = ok2 or _js_fill_input_for_label(c, "Cod. Agência", agencia) or _js_fill_input_for_label(
            c, "Cod. Agencia", agencia
        )
        ok3 = ok3 or _js_fill_input_for_label(c, "Conta Corrente", conta_com_dv) or _js_fill_input_for_label(
            c, "Conta", conta_com_dv
        )
        if ok1 and ok2 and ok3:
            break

    # Fallback super robusto: preencher por ordem dentro da seção "Informações Bancárias"
    if not (ok1 and ok2 and ok3):
        for c in _iter_containers(page):
            details = _js_fill_bank_section_inputs(
                c,
                banco_codigo=banco_codigo,
                agencia=agencia,
                conta_com_dv=conta_com_dv,
            )
            if isinstance(details, dict) and details.get("ok"):
                ok1, ok2, ok3 = True, True, True
                break
            if debug and isinstance(details, dict) and (details.get("reason") or details.get("found") is not None):
                print(f"[debug] bank section fill attempt: {details}", file=sys.stderr)

    # Fallback antigo (xpath)
    if not ok1:
        ok1 = _fill_input_by_label_text_anywhere(page, "Código do Banco", banco_codigo) or _fill_input_by_label_text_anywhere(
            page, "Codigo do Banco", banco_codigo
        )
    if not ok2:
        ok2 = (
            _fill_input_by_label_text_anywhere(page, "Cod. Agência", agencia)
            or _fill_input_by_label_text_anywhere(page, "Cod. Agencia", agencia)
            or _fill_input_by_label_text_anywhere(page, "Agência", agencia)
            or _fill_input_by_label_text_anywhere(page, "Agencia", agencia)
        )
    if not ok3:
        ok3 = _fill_input_by_label_text_anywhere(page, "Conta Corrente", conta_com_dv) or _fill_input_by_label_text_anywhere(
            page, "Conta", conta_com_dv
        )

    ok = bool(ok1 and ok2 and ok3)
    if debug and not ok:
        _debug_dump_bank_section(page)
    return ok


def _click_payment_tab(container) -> None:
    """Clica na aba 'Pagamento' se existir."""
    # O Mercante costuma ter abas como links; preferir texto exato.
    try:
        container.get_by_text("Pagamento", exact=True).click(timeout=1500, force=True)
        return
    except Exception:
        pass
    # Fallback: não-exato (às vezes vem com espaços/markup)
    try:
        container.get_by_text("Pagamento", exact=False).first.click(timeout=1500, force=True)
        return
    except Exception:
        pass


def _select_menu_option(container, option_text: str) -> None:
    """Seleciona uma opção do dropdown (combobox/select)."""
    # Tentar por role (se houver acessibilidade)
    try:
        combobox = container.get_by_role("combobox").first
        combobox.select_option(label=option_text)
        return
    except Exception:
        pass

    # Fallback: primeiro <select> da tela
    sel = container.locator("select").first
    sel.select_option(label=option_text)


def _tentar_login_usuario_senha(page, *, debug: bool = False, screenshot_path: Optional[str] = None) -> bool:
    """
    Tenta efetuar login via usuário/senha usando variáveis de ambiente:
    - MERCANTE_USER
    - MERCANTE_PASS

    Retorna True se aparentemente logou, False caso contrário.
    ⚠️ Não imprime credenciais.
    """
    _try_load_dotenv_if_needed(debug=debug)
    user = (os.getenv("MERCANTE_USER") or "").strip()
    pw = (os.getenv("MERCANTE_PASS") or "").strip()
    if debug:
        print(
            f"[debug] env MERCANTE_USER set={bool(user)} len={len(user)} | "
            f"MERCANTE_PASS set={bool(pw)} len={len(pw)}",
            file=sys.stderr,
        )
    if not user or not pw:
        return False

    page.goto(MERCANTE_LOGIN_URL, wait_until="domcontentloaded")
    if debug:
        print(f"[debug] login url: {page.url}", file=sys.stderr)
        print(f"[debug] inputs: {_safe_dump_inputs(page)[:25]}", file=sys.stderr)

    # Campo usuário (CPF): tentar por name/id comuns; fallback: primeiro input text.
    user_locators = [
        "input[name*=cpf i]",
        "input[id*=cpf i]",
        "input[name*=usuario i]",
        "input[id*=usuario i]",
        "input[name*=login i]",
        "input[id*=login i]",
        "input[type=text]",
    ]
    pw_locators = [
        "input[type=password]",
        "input[name*=senha i]",
        "input[id*=senha i]",
    ]

    user_filled = False
    for sel in user_locators:
        try:
            loc = page.locator(sel).first
            if loc.count() == 0:
                continue
            loc.fill(user, timeout=1500)
            user_filled = True
            break
        except Exception:
            continue

    pw_filled = False
    for sel in pw_locators:
        try:
            loc = page.locator(sel).first
            if loc.count() == 0:
                continue
            loc.fill(pw, timeout=1500)
            pw_filled = True
            break
        except Exception:
            continue

    if not user_filled or not pw_filled:
        if debug:
            print(f"[debug] user_filled={user_filled} pw_filled={pw_filled}", file=sys.stderr)
        return False

    # Submeter login:
    # ✅ Mercante (CPF/Senha) geralmente usa um input type=image name="Image7" (botão "Avançar").
    # Isso é bem mais rápido/confiável do que heurísticas genéricas.
    clicked = False
    for selector in (
        "input[type='image'][name='Image7']",
        "input[name='Image7']",
        "img[name='Image7']",
    ):
        try:
            btn = page.locator(selector).first
            if btn.count() == 0:
                continue
            btn.click(timeout=1500)
            clicked = True
            if debug:
                print(f"[debug] clicked login advance via selector: {selector}", file=sys.stderr)
            break
        except Exception:
            continue

    # Fallback: tentar botões/inputs comuns; último fallback: Enter.
    for selector in (
        "input[type=submit]",
        "button[type=submit]",
        "input[value*=Entrar i]",
        "input[value*=Acessar i]",
        "input[value*=Login i]",
    ):
        if clicked:
            break
        try:
            btn = page.locator(selector).first
            if btn.count() == 0:
                continue
            btn.click(timeout=1500)
            clicked = True
            if debug:
                print(f"[debug] clicked login submit via selector: {selector}", file=sys.stderr)
            break
        except Exception:
            continue

    if not clicked:
        for txt in ("Entrar", "Acessar", "Login", "Confirmar"):
            try:
                page.get_by_role("button", name=txt).click(timeout=1500)
                clicked = True
                if debug:
                    print(f"[debug] clicked login submit via role button: {txt}", file=sys.stderr)
                break
            except Exception:
                try:
                    page.get_by_text(txt, exact=True).click(timeout=1500)
                    clicked = True
                    if debug:
                        print(f"[debug] clicked login submit via text: {txt}", file=sys.stderr)
                    break
                except Exception:
                    continue

    if not clicked:
        try:
            page.keyboard.press("Enter")
            clicked = True
            if debug:
                print("[debug] clicked login submit via Enter key", file=sys.stderr)
        except Exception:
            pass

    # Aguardar navegação / mudança (páginas antigas às vezes nunca ficam 'idle')
    try:
        page.wait_for_load_state("domcontentloaded", timeout=10_000)
    except Exception:
        pass
    try:
        page.wait_for_url("**MercanteController**", timeout=5_000)
    except Exception:
        pass

    # Heurística (mais robusta):
    # - Sucesso se saiu de logon.jsp e/ou entrou no MercanteController
    # - Falha se continuou na página de logon OU se inputs do login ainda existem
    try:
        current_url = page.url or ""
        on_controller = "MercanteController" in current_url
        on_logon = "logon.jsp" in current_url

        try:
            still_has_login_fields = (
                page.locator("input[name='cpfTemp']").count() > 0
                or page.locator("input[name='senhaTemp']").count() > 0
            )
        except Exception:
            still_has_login_fields = False

        ok = (on_controller or not on_logon) and not still_has_login_fields
        if not ok and screenshot_path:
            try:
                page.screenshot(path=screenshot_path, full_page=True)
            except Exception:
                pass
        if debug:
            print(f"[debug] after submit url: {current_url}", file=sys.stderr)
            print(
                f"[debug] heuristic on_controller={on_controller} on_logon={on_logon} "
                f"still_has_login_fields={still_has_login_fields} => ok={ok}",
                file=sys.stderr,
            )
        return ok
    except Exception:
        return False


def run_pagar_afrmm(page, *, debug: bool = False) -> Tuple[str, str]:
    """Navega até Pagamento -> Pagar AFRMM. Retorna (title, url) após a navegação."""
    option_text = "Pagar AFRMM"
    # Se o usuário já navegou manualmente até a tela do AFRMM, não navegar de novo.
    if _has_text_anywhere(page, "CE-Mercante") or _has_text_anywhere(page, "Pagar AFRMM (NOVO)"):
        return page.title(), page.url

    # Estratégia A (robusta): garantir que o combo "cmbAcoes" contenha "Pagar AFRMM"
    # Observação: no Mercante o URL pode não mudar; a troca acontece em frames.
    _wait_for_mercante_ui(page, timeout_ms=20_000)
    # ✅ Mais rápido: poucas tentativas curtas (evita “ficar girando”)
    for _ in range(5):
        # Se a opção já existe, pode selecionar direto (sem depender do clique na aba)
        if _has_option_in_named_select(page, "cmbAcoes", option_text):
            break

        clicked = False
        # 0) Tentar o jeito do CeMercante-main: clicar no menu via frame "header"
        clicked = _click_menu_pagamento_no_header(page)

        # 1) tentativa robusta em todos os containers (page + frames)
        if not clicked:
            for c in _iter_containers(page):
                if _js_click_label_best_effort(c, "Pagamento"):
                    clicked = True
                    break

        # 2) fallbacks antigos
        if not clicked:
            _js_click_text_anywhere(page, "Pagamento")
            _click_css_anywhere(page, "a:has-text('Pagamento')") or _click_css_anywhere(page, "td:has-text('Pagamento')") or _click_css_anywhere(page, "div:has-text('Pagamento')")
            _click_by_text_anywhere(page, "Pagamento", exact=True) or _click_by_text_anywhere(page, "Pagamento", exact=False)

        if debug:
            has_opt = _has_option_in_named_select(page, "cmbAcoes", option_text)
            _debug_dump_frames(page)
            print(
                f"[debug] tentar_abrir_pagamento: clicked_pagamento={clicked} has_Pagar_AFRMM_in_cmbAcoes={has_opt}",
                file=sys.stderr,
            )

        try:
            page.wait_for_timeout(300)
        except Exception:
            pass

    # Agora tentar selecionar no combo (frame[2] geralmente)
    # ✅ Preferir seleção via JS (mais robusto)
    selected = _js_select_option_contains_in_named_select(page, "cmbAcoes", option_text, timeout_ms=8_000) or _select_option_in_named_select(
        page, "cmbAcoes", option_text, timeout_ms=12_000
    )
    if selected:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10_000)
        except Exception:
            try:
                page.wait_for_timeout(1500)
            except Exception:
                pass
        # ✅ Só considerar sucesso se realmente abriu a tela do CE
        if _wait_for_text_anywhere(page, "CE-Mercante", timeout_ms=18_000):
            return page.title(), page.url
        if debug:
            print("[debug] selecionei cmbAcoes='Pagar AFRMM', mas não apareceu 'CE-Mercante' (ainda).", file=sys.stderr)
            _debug_dump_frames(page)
            _debug_dump_cmbacoes(page)

    container = _wait_for_container_with_option(page, option_text=option_text, timeout_ms=25_000)
    if container:
        # clicar aba dentro do container é "best effort" (não bloqueia se não conseguir)
        _click_payment_tab(container)
        _select_menu_option(container, option_text=option_text)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10_000)
        except Exception:
            page.wait_for_timeout(1500)
        if _wait_for_text_anywhere(page, "CE-Mercante", timeout_ms=25_000):
            return page.title(), page.url
        if debug:
            print("[debug] selecionei opção no container, mas não apareceu 'CE-Mercante'.", file=sys.stderr)
            _debug_dump_frames(page)
            _debug_dump_cmbacoes(page)

    # Estratégia B: clicar em "Pagamento" e depois clicar em "Pagar AFRMM" como link/botão/texto
    _click_by_text_anywhere(page, "Pagamento", exact=True) or _click_by_text_anywhere(page, "Pagamento", exact=False)
    if _click_by_text_anywhere(page, option_text, exact=True) or _click_by_text_anywhere(page, option_text, exact=False):
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10_000)
        except Exception:
            page.wait_for_timeout(1500)
        if _wait_for_text_anywhere(page, "CE-Mercante", timeout_ms=25_000):
            return page.title(), page.url
        if debug:
            print("[debug] cliquei texto 'Pagar AFRMM', mas não apareceu 'CE-Mercante'.", file=sys.stderr)
            _debug_dump_frames(page)
            _debug_dump_cmbacoes(page)

    # Estratégia C: procurar por href contendo "afrmm" (muitos sistemas antigos navegam por href)
    if _click_link_href_contains_anywhere(page, "afrmm"):
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10_000)
        except Exception:
            page.wait_for_timeout(1500)
        if _wait_for_text_anywhere(page, "CE-Mercante", timeout_ms=25_000):
            return page.title(), page.url
        if debug:
            print("[debug] cliquei href contendo 'afrmm', mas não apareceu 'CE-Mercante'.", file=sys.stderr)
            _debug_dump_frames(page)
            _debug_dump_cmbacoes(page)

    raise RuntimeError(
        "Não consegui encontrar o caminho até 'Pagar AFRMM'. "
        "Pode ser menu em frame/JS não detectado. Rode com --debug para listar links/selects."
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="RPA Mercante (via Chrome CDP).")
    parser.add_argument(
        "--cdp",
        default="http://127.0.0.1:9222",
        help="Endpoint CDP do Chrome (ex.: http://127.0.0.1:9222).",
    )
    parser.add_argument(
        "--acao",
        choices=["pagar_afrmm", "login_e_ir_pagar_afrmm", "apenas_clicar_pagar"],
        default="pagar_afrmm",
        help="Ação a executar: navegar até pagar_afrmm, fazer login e ir até pagar_afrmm, ou apenas clicar no botão Pagar AFRMM se já estiver na tela.",
    )
    parser.add_argument(
        "--ce",
        default=None,
        help="CE-Mercante para preencher na tela 'Pagar AFRMM' (opcional).",
    )
    parser.add_argument(
        "--parcela",
        default=None,
        help="Nr. da parcela (opcional) para preencher junto com o CE-Mercante.",
    )
    parser.add_argument(
        "--nao_enviar",
        action="store_true",
        help="Se definido, NÃO clica no botão 'Enviar' após preencher (apenas preenche).",
    )
    parser.add_argument(
        "--bb_codigo",
        default=None,
        help="Código do banco para AFRMM (ex: 001). Se omitido, tenta ler de BB_CODIGO no .env.",
    )
    parser.add_argument(
        "--bb_agencia",
        default=None,
        help="Agência (sem DV) para AFRMM. Se omitido, tenta ler de BB_TEST_AGENCIA no .env.",
    )
    parser.add_argument(
        "--bb_conta_dv",
        default=None,
        help="Conta corrente com DV para AFRMM. Se omitido, tenta ler de BB_TEST_CONTA_DV no .env.",
    )
    parser.add_argument(
        "--clicar_pagar",
        action="store_true",
        help="Se definido, após preencher dados bancários clica no botão 'Pagar AFRMM'. ⚠️ Ação sensível.",
    )
    parser.add_argument(
        "--confirmar_popup",
        action="store_true",
        help=(
            "Aceita automaticamente o popup de confirmação (window.confirm) do Mercante após clicar em 'Pagar AFRMM'. "
            "⚠️ Ação irreversível: só use após confirmação explícita do usuário."
        ),
    )
    parser.add_argument(
        "--emit_json",
        action="store_true",
        help="Se definido, emite um JSON parseável com resultados (ex: valor_debito) para integração com o mAIke.",
    )
    parser.add_argument(
        "--screenshot",
        default=None,
        help="Se definido, salva screenshot após a navegação (ex.: /tmp/mercante.png).",
    )
    parser.add_argument(
        "--no_cdp",
        action="store_true",
        help="Se definido, NÃO usa CDP. Abre um Chromium novo (login via MERCANTE_USER/MERCANTE_PASS).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Logs de debug (sem imprimir credenciais). Útil para ajustar seletores do login.",
    )
    parser.add_argument(
        "--keep_open",
        action="store_true",
        help="Mantém o navegador aberto ao final (útil para debug de login).",
    )
    parser.add_argument(
        "--keep_open_seconds",
        type=int,
        default=0,
        help=(
            "Quando usado com --keep_open em execução NÃO-interativa (ex.: Flask), mantém o processo vivo por N segundos "
            "para você acompanhar (evita popup abrir/fechar rápido). Se 0, usa padrão (600s)."
        ),
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executa o navegador sem interface gráfica (sem mostrar janela).",
    )
    parser.add_argument(
        "--ignore_https_errors",
        action="store_true",
        help="Ignora erros de certificado HTTPS (necessário em alguns ambientes para o Mercante).",
    )
    parser.add_argument(
        "--storage_state",
        default=".mercante_storage_state.json",
        help=(
            "Caminho do arquivo de sessão do Playwright (cookies/localStorage). "
            "Se existir, será carregado para tentar pular o login; após login, será salvo."
        ),
    )
    parser.add_argument(
        "--fresh_session",
        action="store_true",
        help="Ignora storage_state e força sessão nova (login do zero).",
    )
    parser.add_argument(
        "--pause_before_payment",
        action="store_true",
        help=(
            "Pausa após o login (ou ao abrir o controller) para você clicar manualmente na aba "
            "'Pagamento' e selecionar 'Pagar AFRMM'. Depois pressione ENTER no terminal para continuar."
        ),
    )
    parser.add_argument(
        "--learn_pagamento_flow",
        action="store_true",
        help=(
            "Modo interativo para 'ensinar' o caminho Pagamento -> Pagar AFRMM. "
            "Salva URLs observados em um profile local, para o bot repetir automaticamente depois."
        ),
    )
    parser.add_argument(
        "--flow_profile",
        default=MERCANTE_PROFILE_DEFAULT,
        help="Arquivo JSON local para salvar/carregar URLs aprendidos do Mercante.",
    )

    args = parser.parse_args(argv)

    # Estado para integração (emit_json)
    pagamento_sucesso: Optional[bool] = None

    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print("❌ Dependência faltando: playwright. Instale com: pip install playwright", file=sys.stderr)
        print(f"Detalhe: {e}", file=sys.stderr)
        return 2

    with sync_playwright() as p:
        browser = None
        if args.acao == "apenas_clicar_pagar":
            # ✅ CRÍTICO: Para apenas clicar, tentar primeiro conectar à janela existente
            # O problema é que o bot roda em background na primeira execução, então precisamos
            # encontrar a janela que está aberta. Tentamos várias estratégias:
            page = None
            browser = None
            context = None
            
            # ✅ Estratégia 1: Tentar conectar via CDP (porta 9222) se houver Chrome aberto com debug
            # Se o Chrome não estiver rodando com debug, essa estratégia falha
            if not args.no_cdp:
                try:
                    browser = p.chromium.connect_over_cdp(args.cdp if hasattr(args, 'cdp') and args.cdp else "http://127.0.0.1:9222")
                    contexts = browser.contexts
                    for ctx in contexts:
                        pages_list = ctx.pages
                        for p_temp in pages_list:
                            try:
                                url = p_temp.url or ""
                                content = p_temp.content() or ""
                                if "mercante" in url.lower() or "Informações Bancárias" in content or "Informacoes Bancarias" in content:
                                    page = p_temp
                                    if args.debug:
                                        print(f"[debug] ✅ Encontrei janela Mercante existente via CDP: {url}", file=sys.stderr)
                                    break
                            except Exception:
                                continue
                        if page:
                            break
                except Exception as e:
                    if args.debug:
                        print(f"[debug] Não consegui conectar via CDP (tentando outras estratégias): {e}", file=sys.stderr)
            
            # ✅ Estratégia 2: Se não encontrou via CDP, retornar erro claro
            # SEM CDP não podemos conectar a uma janela já aberta - isso é fundamental
            if not page:
                print(
                    "❌ **IMPOSSÍVEL**: Não consigo encontrar a janela do Mercante já aberta.\n\n"
                    "💡 **Problema**: Sem CDP (Chrome DevTools Protocol), não posso conectar\n"
                    "   a uma janela que foi aberta por outro processo.\n\n"
                    "**Solução**: Use CDP para permitir conectar à janela:\n"
                    "   1. Feche todas as janelas do Chrome\n"
                    "   2. Inicie Chrome COM debug:\n"
                    "      /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\\n"
                    "        --remote-debugging-port=9222 \\\n"
                    "        --user-data-dir=/tmp/chrome-mercante\n"
                    "   3. Faça login no Mercante manualmente\n"
                    "   4. Execute o preview novamente (pague a AFRMM do GYM.0050/25)\n"
                    "   5. Confirme o pagamento (sim/pagar)\n\n"
                    "⚠️ **Por segurança, não vou refazer todo o fluxo automaticamente.**\n"
                    "   Isso evitaria bloqueio de senha por múltiplas tentativas.",
                    file=sys.stderr,
                )
                if args.keep_open:
                    print("⏸️ Mantendo navegador aberto. Pressione ENTER para fechar...", file=sys.stderr)
                    _pause_keep_open(seconds=getattr(args, "keep_open_seconds", 0))
                return 7
        elif args.no_cdp:
            # ✅ Usar --no_cdp abre nova instância (não pode conectar a janelas anteriores)
            browser = p.chromium.launch(headless=args.headless)
            storage_state_path = None if args.fresh_session else ((args.storage_state or "").strip() or None)
            if storage_state_path and os.path.exists(storage_state_path):
                context = browser.new_context(
                    ignore_https_errors=args.ignore_https_errors,
                    storage_state=storage_state_path,
                )
            else:
                context = browser.new_context(ignore_https_errors=args.ignore_https_errors)
            page = context.new_page()
        else:
            # ✅ Usar CDP para conectar a janela existente (ou criar nova se não houver)
            try:
                cdp_url = args.cdp if hasattr(args, 'cdp') and args.cdp else "http://127.0.0.1:9222"
                if args.debug:
                    print(f"[debug] Tentando conectar via CDP em {cdp_url}...", file=sys.stderr)
                browser = p.chromium.connect_over_cdp(cdp_url)
                # Pegar o primeiro contexto/página existente, ou criar novo se não houver
                if browser.contexts:
                    context = browser.contexts[0]
                    if context.pages:
                        page = context.pages[0]
                        if args.debug:
                            print(f"[debug] ✅ Conectado via CDP - usando página existente: {page.url}", file=sys.stderr)
                    else:
                        page = context.new_page()
                        if args.debug:
                            print("[debug] ✅ Conectado via CDP - criando nova página", file=sys.stderr)
                else:
                    context = browser.new_context()
                    page = context.new_page()
                    if args.debug:
                        print("[debug] ✅ Conectado via CDP - criando novo contexto/página", file=sys.stderr)
            except Exception as e:
                # Se CDP falhar, retornar erro claro (não abrir nova janela)
                error_msg = str(e)
                print(
                    f"❌ Não consegui conectar via CDP em {cdp_url}.\n\n"
                    "💡 **Solução**: Inicie o Chrome COM debug antes de executar:\n"
                    "   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\\n"
                    "     --remote-debugging-port=9222 \\\n"
                    "     --user-data-dir=/tmp/chrome-mercante\n\n"
                    f"Erro detalhado: {error_msg}",
                    file=sys.stderr,
                )
                # ✅ IMPORTANTE: Emitir JSON mesmo em caso de erro para o serviço saber que falhou
                if args.emit_json:
                    payload = {
                        "erro": "CDP_CONNECTION_FAILED",
                        "mensagem": f"Não consegui conectar via CDP: {error_msg}",
                        "cdp_url": cdp_url,
                    }
                    print("__MAIKE_JSON__=" + json.dumps(payload, ensure_ascii=False))
                return 8

        try:
            if args.acao == "login_e_ir_pagar_afrmm":
                fail_shot = None
                if args.screenshot:
                    if args.screenshot.lower().endswith(".png"):
                        fail_shot = args.screenshot[:-4] + ".login_fail.png"
                    else:
                        fail_shot = args.screenshot + ".login_fail.png"
                ok = _tentar_login_usuario_senha(page, debug=args.debug, screenshot_path=fail_shot)
                # Alguns fluxos abrem o pós-login em nova aba/janela.
                if not ok:
                    try:
                        pages = list(context.pages)
                    except Exception:
                        pages = []
                    if args.debug and pages:
                        try:
                            urls = [p.url for p in pages]
                        except Exception:
                            urls = []
                        print(f"[debug] context.pages urls: {urls}", file=sys.stderr)
                    for candidate in reversed(pages):
                        try:
                            if "MercanteController" in (candidate.url or ""):
                                page = candidate
                                ok = True
                                if args.debug:
                                    print(
                                        f"[debug] usando aba/janela pós-login: {candidate.url}",
                                        file=sys.stderr,
                                    )
                                break
                        except Exception:
                            continue
                if not ok:
                    print(
                        "❌ Login automático falhou.\n"
                        "⚠️ Possíveis causas:\n"
                        "   • Senha pode ter expirado (renovação a cada 20 dias)\n"
                        "   • CPF ou senha incorretos\n"
                        "   • Captcha requerido\n"
                        "\n"
                        "💡 Solução: Atualize as credenciais em Configurações ou use login manual + CDP.",
                        file=sys.stderr,
                    )
                    if fail_shot:
                        print(f"📸 Screenshot de falha salvo em: {fail_shot}", file=sys.stderr)
                    if args.keep_open:
                        print("⏸️ Mantendo navegador aberto. Pressione ENTER para fechar...", file=sys.stderr)
                        _pause_keep_open(seconds=getattr(args, "keep_open_seconds", 0))
                    # ✅ NOVO (21/01/2026): Retornar código de erro específico para senha expirada
                    # O código 10 indica senha expirada (para o Maike detectar e avisar)
                    return 10

                # Pós-login: se falhar para achar o menu, esse dump ajuda a ajustar seletores.
                if args.debug:
                    _debug_dump_nav_candidates(page)

                # Tentar usar URLs aprendidos antes de depender do clique na aba
                if args.flow_profile and not args.learn_pagamento_flow:
                    profile = _load_profile(args.flow_profile)
                    _try_goto_known_urls(page, profile, debug=args.debug)

                # Se o usuário pediu aprendizado, fazemos o fluxo guiado e salvamos.
                if args.learn_pagamento_flow:
                    learn_pagamento_flow(page, profile_path=args.flow_profile, debug=args.debug)

                if args.pause_before_payment:
                    print(
                        "⏸️ Pausa manual: clique na aba 'Pagamento' e selecione 'Pagar AFRMM'. "
                        "Quando a tela do AFRMM abrir, pressione ENTER aqui para o bot continuar.",
                        file=sys.stderr,
                    )
                    try:
                        input()
                    except Exception:
                        pass

                # Salvar sessão para reuso (apenas modo no_cdp; no CDP o perfil do Chrome já persiste)
                if args.no_cdp and not args.fresh_session:
                    storage_state_path = (args.storage_state or "").strip() or None
                    if storage_state_path:
                        try:
                            context.storage_state(path=storage_state_path)
                            if args.debug:
                                print(
                                    f"[debug] storage_state salvo em: {storage_state_path}",
                                    file=sys.stderr,
                                )
                        except Exception as e:
                            if args.debug:
                                print(
                                    f"[debug] falha ao salvar storage_state ({storage_state_path}): {e}",
                                    file=sys.stderr,
                                )
                title, url = run_pagar_afrmm(page, debug=args.debug)
                if args.ce:
                    ok_fill = preencher_afrmm_ce(
                        page,
                        ce_mercante=args.ce,
                        parcela=args.parcela,
                        clicar_enviar=not args.nao_enviar,
                    )
                    if not ok_fill:
                        print(
                            "⚠️ Não consegui preencher CE/Parcela automaticamente. "
                            "Você pode preencher manualmente e seguir; rode com --keep_open.",
                            file=sys.stderr,
                        )
                # Se já estiver na tela de Informações Bancárias, preencher dados do BB (sem clicar pagar)
                try:
                    _try_load_dotenv_if_needed(debug=args.debug)
                    bb_codigo = (args.bb_codigo or os.getenv("BB_CODIGO") or "").strip()
                    bb_agencia = (args.bb_agencia or os.getenv("BB_TEST_AGENCIA") or "").strip()
                    bb_conta = (args.bb_conta_dv or os.getenv("BB_TEST_CONTA_DV") or "").strip()
                    if bb_codigo and bb_agencia and bb_conta:
                        found_bank = _wait_for_bank_screen(page, timeout_ms=35_000)
                        if not found_bank and args.debug:
                            print("[debug] não encontrei 'Informações Bancárias' a tempo (vou dump de frames).", file=sys.stderr)
                            _debug_dump_frames(page)
                            _debug_dump_bank_section(page)
                        if found_bank:
                            ok_bb = preencher_dados_bancarios_afrmm(
                                page,
                                banco_codigo=bb_codigo,
                                agencia=bb_agencia,
                                conta_com_dv=bb_conta,
                                debug=args.debug,
                            )
                            if args.debug:
                                print(f"[debug] preenchimento dados bancários: ok={ok_bb}", file=sys.stderr)
                            # ✅ Aguardar um pouco após preencher para garantir que a tela atualizou
                            if ok_bb:
                                try:
                                    page.wait_for_timeout(2000)  # 2 segundos para tela atualizar
                                except Exception:
                                    pass
                            if ok_bb and args.clicar_pagar:
                                _click_button_anywhere(page, "Pagar AFRMM")
                except Exception as e:
                    if args.debug:
                        print(f"[debug] erro ao preencher dados bancários: {e}", file=sys.stderr)

            elif args.acao == "apenas_clicar_pagar":
                # ✅ NOVO: Apenas clicar no botão "Pagar AFRMM" se já estiver na tela correta
                # Não refaz login/navegação - apenas clica no botão que já está visível
                if args.debug:
                    try:
                        print(f"[debug] Modo apenas_clicar_pagar: URL atual = {page.url}", file=sys.stderr)
                    except Exception:
                        print("[debug] Modo apenas_clicar_pagar: página inicializada", file=sys.stderr)
                    print("[debug] Verificando se está na tela de Informações Bancárias...", file=sys.stderr)
                
                # ✅ CRÍTICO: Tentar encontrar a janela/tab correta com tela bancária
                found_bank = False
                page_final = None
                
                # Estratégia 1: Verificar página atual
                try:
                    found_bank = _wait_for_bank_screen(page, timeout_ms=3_000)
                    if found_bank:
                        page_final = page
                        if args.debug:
                            print("[debug] ✅ Tela bancária encontrada na página atual", file=sys.stderr)
                except Exception:
                    pass
                
                # Estratégia 2: Procurar em todas as páginas do contexto
                if not found_bank:
                    try:
                        context = page.context
                        all_pages = context.pages
                        if args.debug:
                            print(f"[debug] Procurando em {len(all_pages)} página(s) do contexto...", file=sys.stderr)
                        for p_temp in all_pages:
                            try:
                                if _has_text_anywhere(p_temp, "Informações Bancárias") or _has_text_anywhere(p_temp, "Informacoes Bancarias"):
                                    page_final = p_temp
                                    found_bank = True
                                    if args.debug:
                                        print(f"[debug] ✅ Encontrei tela bancária em outra página: {p_temp.url}", file=sys.stderr)
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass
                
                # Estratégia 3: Se ainda não encontrou e browser foi criado via CDP, procurar em todos os contextos
                if not found_bank and browser and hasattr(browser, 'contexts'):
                    try:
                        for ctx in browser.contexts:
                            for p_temp in ctx.pages:
                                try:
                                    if _has_text_anywhere(p_temp, "Informações Bancárias") or _has_text_anywhere(p_temp, "Informacoes Bancarias"):
                                        page_final = p_temp
                                        found_bank = True
                                        if args.debug:
                                            print(f"[debug] ✅ Encontrei tela bancária via CDP: {p_temp.url}", file=sys.stderr)
                                        break
                                except Exception:
                                    continue
                            if found_bank:
                                break
                    except Exception:
                        pass
                
                if not found_bank or not page_final:
                    # ✅ CRÍTICO: Se não encontrou a tela, isso significa que a janela anterior foi fechada
                    # ou está em outro processo. Nesse caso, não devemos fazer login/navegação novamente.
                    # O usuário precisa manter a janela aberta do preview anterior.
                    print(
                        "❌ Não encontrei a tela 'Informações Bancárias'.\n\n"
                        "💡 **Problema**: A janela do Mercante não está mais aberta ou não está na tela correta.\n\n"
                        "**Solução**:\n"
                        "   1. Execute o preview novamente (pague a AFRMM do GYM.0050/25)\n"
                        "   2. Mantenha a janela do navegador aberta na tela 'Informações Bancárias'\n"
                        "   3. Confirme o pagamento novamente (sim/pagar)\n\n"
                        "⚠️ **Importante**: A janela do Mercante precisa estar aberta da execução anterior do preview.",
                        file=sys.stderr,
                    )
                    if args.keep_open:
                        print("⏸️ Mantendo navegador aberto. Pressione ENTER para fechar...", file=sys.stderr)
                        _pause_keep_open(seconds=getattr(args, "keep_open_seconds", 0))
                    return 5
                
                # Usar a página correta encontrada
                page = page_final
                
                # Aguardar um pouco para garantir que a tela está pronta
                try:
                    page.wait_for_timeout(1000)
                except Exception:
                    pass
                
                # Clicar no botão "Pagar AFRMM"
                # ✅ Se solicitado, aceitar automaticamente o popup (window.confirm) do Mercante
                if args.confirmar_popup:
                    _install_dialog_auto_accept(page, debug=args.debug)
                clicked = _click_button_anywhere(page, "Pagar AFRMM")
                if not clicked:
                    print(
                        "❌ Não consegui clicar no botão 'Pagar AFRMM'.\n"
                        "💡 Verifique se o botão está visível na tela.",
                        file=sys.stderr,
                    )
                    if args.keep_open:
                        print("⏸️ Mantendo navegador aberto. Pressione ENTER para fechar...", file=sys.stderr)
                        _pause_keep_open(seconds=getattr(args, "keep_open_seconds", 0))
                    return 6
                
                print("✅ Botão 'Pagar AFRMM' clicado com sucesso!", file=sys.stderr)
                
                # Aguardar navegação para próxima tela (confirmação de pagamento)
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=10_000)
                except Exception:
                    try:
                        page.wait_for_timeout(2000)
                    except Exception:
                        pass

                # ✅ Se confirmamos popup, aguardar confirmação de sucesso na tela
                if args.confirmar_popup:
                    ok_sucesso = _wait_for_text_anywhere(page, "Débito efetuado com sucesso", timeout_ms=20_000)
                    if not ok_sucesso:
                        ok_sucesso = _wait_for_text_anywhere(page, "Debito efetuado com sucesso", timeout_ms=5_000)
                    pagamento_sucesso = bool(ok_sucesso)
                    if args.debug:
                        print(f"[debug] pós-pagamento (click-only): sucesso_detectado={ok_sucesso}", file=sys.stderr)
                
                title = page.title() or "Sem título"
                url = page.url or "Sem URL"
                
                print(f"✅ OK. Página atual: {title} | {url}")
                if args.keep_open:
                    print("⏸️ Mantendo navegador aberto. Pressione ENTER para fechar...", file=sys.stderr)
                    _pause_keep_open(seconds=getattr(args, "keep_open_seconds", 0))
                return 0

            elif args.acao == "pagar_afrmm":
                # Se estivermos sem CDP e com sessão carregada, tentar ir direto ao controller
                # para garantir que a página está no domínio correto antes de buscar menus.
                try:
                    if args.no_cdp and MERCANTE_CONTROLLER_HINT not in (page.url or ""):
                        page.goto(
                            "https://www.mercante.transportes.gov.br/g36127/servlet/serpro.siscomex.mercante.servlet.MercanteController",
                            wait_until="domcontentloaded",
                        )
                except Exception:
                    pass
                # Se caiu no controller "público" (sem sessão), fazer login antes de seguir.
                if _mercante_needs_login(page):
                    if args.debug:
                        print("[debug] Mercante parece sem sessão (página pública). Fazendo login...", file=sys.stderr)
                    ok = _tentar_login_usuario_senha(page, debug=args.debug, screenshot_path=None)
                    if not ok:
                        # ✅ NOVO (21/01/2026): Erro específico para senha expirada (sem retry múltiplo)
                        raise RuntimeError(
                            "❌ Não consegui autenticar no Mercante.\n"
                            "⚠️ Senha pode ter expirado (renovação a cada 20 dias).\n"
                            "💡 Atualize as credenciais em Configurações."
                        )
                # Tentar usar URLs aprendidos antes de depender do clique na aba
                if args.flow_profile and not args.learn_pagamento_flow:
                    profile = _load_profile(args.flow_profile)
                    _try_goto_known_urls(page, profile, debug=args.debug)

                # Se o usuário pediu aprendizado, fazemos o fluxo guiado e salvamos.
                if args.learn_pagamento_flow:
                    learn_pagamento_flow(page, profile_path=args.flow_profile, debug=args.debug)
                if args.pause_before_payment:
                    print(
                        "⏸️ Pausa manual: clique na aba 'Pagamento' e selecione 'Pagar AFRMM'. "
                        "Quando a tela do AFRMM abrir, pressione ENTER aqui para o bot continuar.",
                        file=sys.stderr,
                    )
                    try:
                        input()
                    except Exception:
                        pass
                if args.debug:
                    _debug_dump_nav_candidates(page)
                title, url = run_pagar_afrmm(page, debug=args.debug)
                if args.ce:
                    ok_fill = preencher_afrmm_ce(
                        page,
                        ce_mercante=args.ce,
                        parcela=args.parcela,
                        clicar_enviar=not args.nao_enviar,
                    )
                    if not ok_fill:
                        print(
                            "⚠️ Não consegui preencher CE/Parcela automaticamente. "
                            "Você pode preencher manualmente e seguir; rode com --keep_open.",
                            file=sys.stderr,
                        )
                # Preencher dados bancários (se informados) na tela final, sem clicar pagar (a menos que --clicar_pagar)
                try:
                    _try_load_dotenv_if_needed(debug=args.debug)
                    bb_codigo = (args.bb_codigo or os.getenv("BB_CODIGO") or "").strip()
                    bb_agencia = (args.bb_agencia or os.getenv("BB_TEST_AGENCIA") or "").strip()
                    bb_conta = (args.bb_conta_dv or os.getenv("BB_TEST_CONTA_DV") or "").strip()
                    if bb_codigo and bb_agencia and bb_conta:
                        found_bank = _wait_for_bank_screen(page, timeout_ms=35_000)
                        if not found_bank and args.debug:
                            print("[debug] não encontrei 'Informações Bancárias' a tempo (vou dump de frames).", file=sys.stderr)
                            _debug_dump_frames(page)
                            _debug_dump_bank_section(page)
                        if found_bank:
                            ok_bb = preencher_dados_bancarios_afrmm(
                                page,
                                banco_codigo=bb_codigo,
                                agencia=bb_agencia,
                                conta_com_dv=bb_conta,
                                debug=args.debug,
                            )
                            if args.debug:
                                print(f"[debug] preenchimento dados bancários: ok={ok_bb}", file=sys.stderr)
                            if ok_bb and args.clicar_pagar:
                                try:
                                    ctx = page.context
                                except Exception:
                                    ctx = None
                                # ✅ Se solicitado, aceitar automaticamente o popup (window.confirm) do Mercante
                                if args.confirmar_popup:
                                    _install_dialog_auto_accept(page, debug=args.debug)
                                _click_button_anywhere(page, "Pagar AFRMM")
                                # ✅ Depois do clique, o Mercante pode abrir confirmação em popup (nova aba/janela).
                                # Se isso acontecer e a aba fechar rápido, tentamos "segurar" focando nela e aguardando load.
                                if ctx is not None:
                                    popup = _wait_for_new_popup_page(ctx, timeout_ms=12_000)
                                    if popup:
                                        if args.confirmar_popup:
                                            _install_dialog_auto_accept(popup, debug=args.debug)
                                        try:
                                            popup.bring_to_front()
                                        except Exception:
                                            pass
                                        try:
                                            popup.wait_for_load_state("domcontentloaded", timeout=12_000)
                                        except Exception:
                                            pass
                                        if args.debug:
                                            try:
                                                print(f"[debug] ✅ Popup/aba de confirmação detectada: {popup.url}", file=sys.stderr)
                                            except Exception:
                                                print("[debug] ✅ Popup/aba de confirmação detectada", file=sys.stderr)
                                # ✅ Após confirmar popup, aguardar tela de sucesso ("Débito efetuado com sucesso")
                                if args.confirmar_popup:
                                    ok_sucesso = _wait_for_text_anywhere(page, "Débito efetuado com sucesso", timeout_ms=20_000)
                                    if not ok_sucesso:
                                        ok_sucesso = _wait_for_text_anywhere(page, "Debito efetuado com sucesso", timeout_ms=5_000)
                                    pagamento_sucesso = bool(ok_sucesso)
                                    if args.debug:
                                        print(f"[debug] pós-pagamento: sucesso_detectado={ok_sucesso}", file=sys.stderr)
                except Exception as e:
                    if args.debug:
                        print(f"[debug] erro ao preencher dados bancários: {e}", file=sys.stderr)
            else:
                raise RuntimeError("Ação não suportada")
        except Exception as e:
            print(f"❌ Erro ao executar ação {args.acao}: {e}", file=sys.stderr)
            err_shot = None
            if args.screenshot:
                if args.screenshot.lower().endswith(".png"):
                    err_shot = args.screenshot[:-4] + ".error.png"
                else:
                    err_shot = args.screenshot + ".error.png"
            if err_shot:
                try:
                    page.screenshot(path=err_shot, full_page=True)
                    print(f"📸 Screenshot do erro salvo em: {err_shot}", file=sys.stderr)
                except Exception:
                    pass
            if args.keep_open:
                print("⏸️ Mantendo navegador aberto. Pressione ENTER para fechar...", file=sys.stderr)
                _pause_keep_open(seconds=getattr(args, "keep_open_seconds", 0))
            return 4

        # ✅ CRÍTICO (21/01/2026): Screenshot deve ser tirado DEPOIS de confirmar sucesso,
        # e especialmente na tela de "Débito efetuado com sucesso" se pagamento foi bem-sucedido.
        screenshot_ok = False
        screenshot_path_actual = None
        if args.screenshot:
            try:
                # Se pagamento foi bem-sucedido, garantir que estamos na tela de sucesso antes de capturar
                if pagamento_sucesso:
                    # Aguardar um pouco mais para garantir que a tela de sucesso está totalmente carregada
                    try:
                        page.wait_for_timeout(2000)
                    except Exception:
                        pass
                    # Verificar novamente se ainda estamos na tela de sucesso (pode ter mudado de página)
                    ok_confirm = _wait_for_text_anywhere(page, "Débito efetuado com sucesso", timeout_ms=5_000)
                    if not ok_confirm:
                        ok_confirm = _wait_for_text_anywhere(page, "Debito efetuado com sucesso", timeout_ms=2_000)
                    if ok_confirm and args.debug:
                        print("[debug] ✅ Confirmando tela de sucesso antes de capturar screenshot", file=sys.stderr)
                
                # Tentar capturar screenshot (múltiplas tentativas se necessário)
                for tentativa in range(3):
                    try:
                        page.screenshot(path=args.screenshot, full_page=True)
                        # Verificar se arquivo foi realmente criado
                        if os.path.exists(args.screenshot) and os.path.getsize(args.screenshot) > 0:
                            screenshot_ok = True
                            screenshot_path_actual = args.screenshot
                            
                            # ✅ NOVO (26/01/2026): Converter PNG para PDF automaticamente
                            try:
                                from utils.png_to_pdf import converter_png_para_pdf
                                pdf_path = converter_png_para_pdf(args.screenshot)
                                if pdf_path and os.path.exists(pdf_path):
                                    if args.debug:
                                        print(f"[debug] ✅ PDF gerado automaticamente: {pdf_path}", file=sys.stderr)
                                    # Opcional: manter PNG também ou substituir? Por enquanto mantemos ambos
                            except Exception as e_pdf:
                                # Não falhar se conversão PDF falhar - PNG já está salvo
                                if args.debug:
                                    print(f"[debug] ⚠️ Conversão PNG→PDF falhou (não crítico): {e_pdf}", file=sys.stderr)
                            
                            if args.debug:
                                print(f"[debug] ✅ Screenshot capturado com sucesso (tentativa {tentativa + 1})", file=sys.stderr)
                            break
                        elif args.debug:
                            print(f"[debug] ⚠️ Screenshot retornou sem erro mas arquivo não existe ou está vazio (tentativa {tentativa + 1})", file=sys.stderr)
                    except Exception as e_shot:
                        if args.debug:
                            print(f"[debug] ⚠️ Erro ao capturar screenshot (tentativa {tentativa + 1}): {e_shot}", file=sys.stderr)
                        if tentativa < 2:
                            try:
                                page.wait_for_timeout(1000)
                            except Exception:
                                pass
                if not screenshot_ok and args.debug:
                    print("[debug] ❌ Não consegui capturar screenshot após 3 tentativas", file=sys.stderr)
            except Exception as e:
                if args.debug:
                    print(f"[debug] ❌ Erro geral ao processar screenshot: {e}", file=sys.stderr)
                # Não falhar por screenshot, mas marcar como falhou

        # ✅ Resultado estruturado (para integração)
        if args.emit_json:
            payload: Dict[str, Any] = {
                "title": title,
                "url": url,
            }
            # Metadados do pagamento (quando aplicável)
            payload["acao"] = args.acao
            payload["confirmar_popup"] = bool(getattr(args, "confirmar_popup", False))
            payload["pagamento_sucesso"] = pagamento_sucesso
            # ✅ CRÍTICO: Incluir screenshot_path apenas se arquivo foi realmente criado
            if screenshot_ok and screenshot_path_actual:
                payload["screenshot_path"] = screenshot_path_actual
                payload["screenshot_ok"] = True
            elif args.screenshot:
                # Screenshot foi solicitado mas falhou - incluir path solicitado mas marcar como falhou
                payload["screenshot_path"] = args.screenshot
                payload["screenshot_ok"] = False
                if args.debug:
                    print("[debug] ⚠️ Screenshot solicitado mas não foi capturado com sucesso", file=sys.stderr)
            try:
                # ✅ IMPORTANTE: Aguardar tela bancária antes de extrair valor do débito
                if _wait_for_bank_screen(page, timeout_ms=10_000):
                    # Aguardar mais um pouco para garantir que valor do débito apareceu
                    try:
                        page.wait_for_timeout(1500)
                    except Exception:
                        pass
                    deb = _extrair_valor_debito_brl(page)
                    if deb:
                        payload.update(deb)
                        if args.debug:
                            print(f"[debug] ✅ Valor do débito extraído: R$ {deb.get('valor_debito_float', 0):,.2f}", file=sys.stderr)
                    elif args.debug:
                        print("[debug] ⚠️ Não consegui extrair valor do débito (pode não ter aparecido ainda)", file=sys.stderr)
            except Exception as e:
                if args.debug:
                    print(f"[debug] ⚠️ Erro ao extrair valor do débito: {e}", file=sys.stderr)
            # Se o pagamento foi confirmado, tentar extrair campos da tela de comprovante
            try:
                if pagamento_sucesso:
                    payload["comprovante"] = _extrair_comprovante_pagamento(page)
            except Exception:
                pass
            # Linha única, fácil de parsear
            print("__MAIKE_JSON__=" + json.dumps(payload, ensure_ascii=False))

        print(f"✅ OK. Página atual: {title} | {url}")
        if getattr(args, "confirmar_popup", False):
            print("✅ O script confirmou o popup (OK).", file=sys.stderr)
        else:
            print("⚠️ O script NÃO confirma pagamento. Confira manualmente antes de prosseguir.")
        if args.keep_open:
            print("⏸️ Mantendo navegador aberto. Pressione ENTER para fechar...", file=sys.stderr)
            _pause_keep_open(seconds=getattr(args, "keep_open_seconds", 0))

        try:
            browser.close()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

