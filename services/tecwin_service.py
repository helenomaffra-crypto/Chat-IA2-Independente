from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: str = "false") -> bool:
    return str(os.getenv(name, default)).strip().lower() in ("1", "true", "yes", "y", "on")


class TecwinService:
    """
    Cliente de consulta ao TECwin (Aduaneiras) usando Playwright.

    Motivo: o projeto já usa Playwright (e instala Chromium no Dockerfile),
    então evitamos depender de Selenium/ChromeDriver no runtime.

    Retorna um dict compatível com o formato esperado pelo `NcmPrecheckService`
    (inclui `url` e `html` quando disponíveis).
    """

    BASE_URL = "https://tecwinweb.aduaneiras.com.br"
    LOGIN_URL = f"{BASE_URL}/Modulos/Usuario/Login.aspx"

    def __init__(self, *, headless: bool = True, timeout_ms: int = 30_000) -> None:
        self.headless = bool(headless)
        self.timeout_ms = int(timeout_ms or 30_000)

        # Controle fino via env (pode desativar em produção se necessário)
        self.enabled = _env_bool("TECWIN_ENABLED", "true")
        self.ignore_https_errors = _env_bool("TECWIN_IGNORE_HTTPS_ERRORS", "false")

        self.email = (os.getenv("TECWIN_EMAIL") or "").strip()
        self.senha = (os.getenv("TECWIN_SENHA") or "").strip()

    def _ensure_ready(self) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return {
                "sucesso": False,
                "erro": "TECWIN_DISABLED",
                "mensagem": "TECwin está desabilitado (TECWIN_ENABLED=false).",
            }
        if not self.email or not self.senha:
            return {
                "sucesso": False,
                "erro": "TECWIN_CREDENTIALS_MISSING",
                "mensagem": "Credenciais TECwin não configuradas (defina TECWIN_EMAIL e TECWIN_SENHA).",
            }
        return None

    def consultar_ncm(self, codigo_ncm: str) -> Dict[str, Any]:
        """
        Consulta um NCM no TECwin e retorna HTML bruto para extração posterior.
        """
        pre = self._ensure_ready()
        if pre:
            return pre

        codigo = str(codigo_ncm or "").strip().replace(".", "")
        if not codigo or not codigo.isdigit():
            return {"sucesso": False, "erro": "PARAMETRO_INVALIDO", "mensagem": "NCM inválido."}

        url_ncm = f"{self.BASE_URL}/Modulos/CodigoNcm/CodigoNcm.aspx?codigoNcm={codigo}"

        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except Exception as e:
            return {
                "sucesso": False,
                "erro": "PLAYWRIGHT_NAO_DISPONIVEL",
                "mensagem": f"Playwright não está disponível no runtime: {e}",
            }

        try:
            with sync_playwright() as p:
                # Alguns sites abortam navegação em headless "default".
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                context = browser.new_context(
                    ignore_https_errors=self.ignore_https_errors,
                    user_agent=(
                        os.getenv("TECWIN_USER_AGENT")
                        or "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                    locale=os.getenv("TECWIN_LOCALE") or "pt-BR",
                )
                page = context.new_page()

                # 1) Login
                logger.info("🔐 TECwin: iniciando login (Playwright)")
                page.goto(self.LOGIN_URL, wait_until="domcontentloaded", timeout=self.timeout_ms)

                # Algumas telas podem ter ids específicos; mantemos fallback para inputs genéricos.
                email_selectors = [
                    "#txtEmail",
                    "#Email",
                    "input[type='email']",
                    "input[name*='email' i]",
                    "input[id*='email' i]",
                    "input[type='text']",
                ]
                pass_selectors = [
                    "#txtSenha",
                    "#Senha",
                    "input[type='password']",
                    "input[name*='senha' i]",
                    "input[name*='password' i]",
                ]
                submit_selectors = [
                    "#btnLogin",
                    "button[type='submit']",
                    "input[type='submit']",
                    "input[value*='Entrar' i]",
                    ".btn-primary",
                ]

                def _fill_first(selectors: list[str], value: str) -> bool:
                    for sel in selectors:
                        try:
                            loc = page.locator(sel).first
                            if loc.count() <= 0:
                                continue
                            loc.fill(value, timeout=2_000)
                            return True
                        except Exception:
                            continue
                    return False

                def _click_first(selectors: list[str]) -> bool:
                    for sel in selectors:
                        try:
                            loc = page.locator(sel).first
                            if loc.count() <= 0:
                                continue
                            loc.click(timeout=2_000)
                            return True
                        except Exception:
                            continue
                    return False

                if not _fill_first(email_selectors, self.email):
                    browser.close()
                    return {
                        "sucesso": False,
                        "erro": "TECWIN_LOGIN_FORM_MISSING",
                        "mensagem": "Não foi possível localizar campo de email no TECwin (HTML mudou?).",
                    }
                if not _fill_first(pass_selectors, self.senha):
                    browser.close()
                    return {
                        "sucesso": False,
                        "erro": "TECWIN_LOGIN_FORM_MISSING",
                        "mensagem": "Não foi possível localizar campo de senha no TECwin (HTML mudou?).",
                    }
                if not _click_first(submit_selectors):
                    # fallback: tentar qualquer submit/button
                    try:
                        page.locator("button, input[type='submit']").first.click(timeout=2_000)
                    except Exception:
                        browser.close()
                        return {
                            "sucesso": False,
                            "erro": "TECWIN_LOGIN_FORM_MISSING",
                            "mensagem": "Não foi possível localizar botão de login no TECwin (HTML mudou?).",
                        }

                # Esperar navegação / carregamento
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=self.timeout_ms)
                except PlaywrightTimeoutError:
                    # Segue adiante — alguns fluxos não disparam nav completa
                    pass

                # Aguardar um pouco para cookies/sessão estabilizarem
                try:
                    page.wait_for_timeout(800)
                except Exception:
                    pass

                # 2) Ir para a tela do NCM (se login falhou, costuma redirecionar de volta)
                logger.info(f"🔍 TECwin: consultando NCM {codigo}")
                # ✅ Robustez: em alguns casos o `goto` é abortado por navegações internas pós-login.
                # Usar uma nova aba + retry resolve a maioria dos "net::ERR_ABORTED".
                page_ncm = context.new_page()
                last_err: Optional[Exception] = None
                for attempt in range(2):
                    try:
                        page_ncm.goto(url_ncm, wait_until="domcontentloaded", timeout=self.timeout_ms)
                        break
                    except Exception as e:
                        last_err = e
                        if "net::ERR_ABORTED" in str(e) and attempt == 0:
                            try:
                                page_ncm.close()
                            except Exception:
                                pass
                            page_ncm = context.new_page()
                            continue
                        raise
                try:
                    page_ncm.wait_for_load_state("networkidle", timeout=10_000)
                except PlaywrightTimeoutError:
                    pass

                current_url = (page_ncm.url or "").strip()
                if "Login.aspx" in current_url:
                    browser.close()
                    return {
                        "sucesso": False,
                        "erro": "TECWIN_LOGIN_FAILED",
                        "mensagem": "Falha no login TECwin (verifique credenciais / captcha / bloqueio).",
                    }

                html = page_ncm.content()
                browser.close()

                # Heurística: garantir que o HTML contém ao menos referência ao NCM (pode não existir)
                if not html or len(html) < 200:
                    return {
                        "sucesso": False,
                        "erro": "TECWIN_EMPTY_RESPONSE",
                        "mensagem": "TECwin retornou página vazia/curta ao consultar o NCM.",
                        "url": current_url,
                        "html": html or "",
                    }

                # Não tentamos parsear profundamente aqui (deixa a regex atual do precheck fazer),
                # mas marcamos se aparece um <tr ncm="..."> para ajudar debug.
                tr_hit = bool(
                    re.search(rf'<tr[^>]*ncm=["\']?{re.escape(codigo)}["\']?[^>]*>', html, re.IGNORECASE)
                )

                return {
                    "sucesso": True,
                    "codigo_ncm": codigo,
                    "url": current_url,
                    "html": html,
                    "tr_ncm_encontrado": tr_hit,
                    "fonte": "playwright",
                }
        except Exception as e:
            logger.warning(f"⚠️ TECwin: erro ao consultar NCM {codigo}: {e}", exc_info=True)
            return {
                "sucesso": False,
                "erro": "TECWIN_EXCEPTION",
                "mensagem": str(e),
            }

