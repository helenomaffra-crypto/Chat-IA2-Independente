#!/usr/bin/env python3
"""
Aplicação standalone para consultar NCM no TECwin (Aduaneiras).
Não modifica o código existente do Chat-IA-Independente.

Uso:
    python3 tecwin_scraper.py --ncm 96170010 --email seu_email@exemplo.com --senha sua_senha
"""

import argparse
import sys
import time
from typing import Optional, Dict, Any
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        WEBDRIVER_MANAGER_AVAILABLE = True
    except ImportError:
        WEBDRIVER_MANAGER_AVAILABLE = False
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    WEBDRIVER_MANAGER_AVAILABLE = False
    logger.warning("⚠️ Selenium não está instalado. Instale com: pip install selenium")


class TecwinScraper:
    """Classe para fazer scraping do TECwin e consultar NCM."""
    
    def __init__(self, headless: bool = False):
        """
        Inicializa o scraper.
        
        Args:
            headless: Se True, executa o navegador em modo headless (sem interface gráfica)
        """
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium não está instalado. Instale com: pip install selenium")
        
        self.driver = None
        self.headless = headless
        self.base_url = "https://tecwinweb.aduaneiras.com.br"
        
    def _init_driver(self):
        """Inicializa o driver do Selenium."""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # User agent para parecer um navegador real
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            # Tentar usar webdriver-manager primeiro (instala ChromeDriver automaticamente)
            if WEBDRIVER_MANAGER_AVAILABLE:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("✅ Driver do Chrome inicializado (usando webdriver-manager)")
            else:
                # Fallback: usar ChromeDriver do PATH
                self.driver = webdriver.Chrome(options=chrome_options)
                logger.info("✅ Driver do Chrome inicializado (usando ChromeDriver do PATH)")
            
            self.driver.implicitly_wait(10)
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar driver: {e}")
            logger.error("💡 Soluções:")
            if not WEBDRIVER_MANAGER_AVAILABLE:
                logger.error("   1. Instale webdriver-manager: pip install webdriver-manager")
            logger.error("   2. Ou instale ChromeDriver manualmente:")
            logger.error("      macOS: brew install chromedriver")
            logger.error("      Ou baixe de: https://chromedriver.chromium.org/")
            raise
    
    def login(self, email: str, senha: str) -> bool:
        """
        Faz login no TECwin.
        
        Args:
            email: Email do usuário
            senha: Senha do usuário
        
        Returns:
            True se login foi bem-sucedido, False caso contrário
        """
        try:
            if not self.driver:
                self._init_driver()
            
            logger.info(f"🔐 Fazendo login no TECwin...")
            self.driver.get(f"{self.base_url}/Modulos/Usuario/Login.aspx")
            
            # Aguardar página carregar
            time.sleep(2)
            
            # Encontrar campos de email e senha
            # Tentar diferentes seletores possíveis
            email_selectors = [
                "input[type='email']",
                "input[name*='email' i]",
                "input[id*='email' i]",
                "input[type='text']",
                "#txtEmail",
                "#Email",
            ]
            
            senha_selectors = [
                "input[type='password']",
                "input[name*='senha' i]",
                "input[name*='password' i]",
                "#txtSenha",
                "#Senha",
            ]
            
            botao_selectors = [
                "input[type='submit']",
                "button[type='submit']",
                "input[value*='Entrar' i]",
                "button:contains('Entrar')",
                ".btn-primary",
                "#btnLogin",
            ]
            
            # Tentar encontrar campo de email
            email_field = None
            for selector in email_selectors:
                try:
                    email_field = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"✅ Campo de email encontrado: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not email_field:
                # Tentar encontrar por XPath (primeiro input de texto)
                try:
                    email_field = self.driver.find_element(By.XPATH, "//input[@type='text' or @type='email']")
                    logger.info("✅ Campo de email encontrado por XPath")
                except NoSuchElementException:
                    logger.error("❌ Não foi possível encontrar campo de email")
                    return False
            
            # Tentar encontrar campo de senha
            senha_field = None
            for selector in senha_selectors:
                try:
                    senha_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    logger.info(f"✅ Campo de senha encontrado: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not senha_field:
                try:
                    senha_field = self.driver.find_element(By.XPATH, "//input[@type='password']")
                    logger.info("✅ Campo de senha encontrado por XPath")
                except NoSuchElementException:
                    logger.error("❌ Não foi possível encontrar campo de senha")
                    return False
            
            # Preencher campos
            email_field.clear()
            email_field.send_keys(email)
            logger.info("✅ Email preenchido")
            
            senha_field.clear()
            senha_field.send_keys(senha)
            logger.info("✅ Senha preenchida")
            
            # Encontrar e clicar no botão de login
            botao_login = None
            for selector in botao_selectors:
                try:
                    botao_login = self.driver.find_element(By.CSS_SELECTOR, selector)
                    logger.info(f"✅ Botão de login encontrado: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not botao_login:
                # Tentar encontrar qualquer botão ou input submit
                try:
                    botao_login = self.driver.find_element(By.XPATH, "//button | //input[@type='submit']")
                    logger.info("✅ Botão de login encontrado por XPath")
                except NoSuchElementException:
                    logger.error("❌ Não foi possível encontrar botão de login")
                    return False
            
            # Clicar no botão
            botao_login.click()
            logger.info("✅ Botão de login clicado")
            
            # Aguardar redirecionamento ou erro
            time.sleep(3)
            
            # Verificar se login foi bem-sucedido
            current_url = self.driver.current_url
            if "Login.aspx" not in current_url:
                logger.info(f"✅ Login bem-sucedido! Redirecionado para: {current_url}")
                return True
            else:
                # Verificar se há mensagem de erro
                try:
                    error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".error, .alert, .mensagem-erro, [class*='error'], [class*='alert']")
                    if error_elements:
                        error_text = error_elements[0].text
                        logger.error(f"❌ Erro no login: {error_text}")
                    else:
                        logger.error("❌ Login falhou - ainda na página de login")
                except:
                    logger.error("❌ Login falhou - não foi possível determinar o erro")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro durante login: {e}", exc_info=True)
            return False
    
    def consultar_ncm(self, codigo_ncm: str) -> Optional[Dict[str, Any]]:
        """
        Consulta um NCM no TECwin.
        
        Args:
            codigo_ncm: Código NCM a consultar (ex: "96170010")
        
        Returns:
            Dict com dados do NCM ou None se não encontrado
        """
        try:
            logger.info(f"🔍 Consultando NCM {codigo_ncm}...")
            
            # Navegar para página de consulta de NCM
            url = f"{self.base_url}/Modulos/CodigoNcm/CodigoNcm.aspx?codigoNcm={codigo_ncm}"
            self.driver.get(url)
            
            # Aguardar página carregar
            time.sleep(3)
            
            # Verificar se precisa fazer login
            if "Login.aspx" in self.driver.current_url:
                logger.warning("⚠️ Precisa fazer login primeiro")
                return None
            
            # Extrair dados da página
            dados_ncm = {
                'codigo_ncm': codigo_ncm,
                'url': self.driver.current_url
            }
            
            # Tentar encontrar informações do NCM na página
            # Procurar por tabelas, divs com informações, etc.
            try:
                # Tentar encontrar título ou cabeçalho com o código NCM
                page_text = self.driver.page_source
                
                # Procurar por padrões comuns de informações de NCM
                # (isso depende da estrutura real da página)
                
                # Tentar encontrar tabela com dados
                try:
                    tabelas = self.driver.find_elements(By.TAG_NAME, "table")
                    if tabelas:
                        logger.info(f"✅ Encontradas {len(tabelas)} tabela(s) na página")
                        for i, tabela in enumerate(tabelas):
                            try:
                                dados_tabela = tabela.text
                                if dados_tabela:
                                    dados_ncm[f'tabela_{i+1}'] = dados_tabela
                            except:
                                pass
                except:
                    pass
                
                # Tentar encontrar divs com informações
                try:
                    divs_info = self.driver.find_elements(By.CSS_SELECTOR, "div[class*='info'], div[class*='dados'], div[class*='resultado'], div[class*='ncm']")
                    if divs_info:
                        logger.info(f"✅ Encontrados {len(divs_info)} elemento(s) com informações")
                        for i, div in enumerate(divs_info):
                            try:
                                texto = div.text
                                if texto and len(texto) > 10:  # Ignorar textos muito curtos
                                    dados_ncm[f'info_{i+1}'] = texto
                            except:
                                pass
                except:
                    pass
                
                # Tentar encontrar todos os textos visíveis na página (pode conter informações do NCM)
                try:
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if body_text and len(body_text) > 50:
                        # Filtrar apenas linhas relevantes (que podem conter dados do NCM)
                        linhas_relevantes = []
                        for linha in body_text.split('\n'):
                            linha_limpa = linha.strip()
                            if linha_limpa and len(linha_limpa) > 5:
                                # Ignorar linhas muito comuns (navegação, rodapé, etc.)
                                if not any(palavra in linha_limpa.lower() for palavra in ['menu', 'login', 'sair', 'copyright', 'todos os direitos']):
                                    linhas_relevantes.append(linha_limpa)
                        
                        if linhas_relevantes:
                            dados_ncm['texto_pagina'] = '\n'.join(linhas_relevantes[:50])  # Limitar a 50 linhas
                except:
                    pass
                
                # Salvar HTML completo para análise
                dados_ncm['html'] = self.driver.page_source
                
                logger.info("✅ Dados extraídos da página")
                return dados_ncm
                
            except Exception as e:
                logger.error(f"❌ Erro ao extrair dados: {e}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao consultar NCM: {e}", exc_info=True)
            return None
    
    def fechar(self):
        """Fecha o navegador."""
        if self.driver:
            self.driver.quit()
            logger.info("✅ Navegador fechado")


def main():
    """Função principal."""
    import os
    
    parser = argparse.ArgumentParser(
        description='Consulta NCM no TECwin (Aduaneiras)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Consultar NCM específico (precisa estar logado)
  python3 tecwin_scraper.py --ncm 96170010 --email usuario@exemplo.com --senha senha123

  # Modo headless (sem interface gráfica)
  python3 tecwin_scraper.py --ncm 96170010 --email usuario@exemplo.com --senha senha123 --headless

  # Apenas fazer login (para testar credenciais)
  python3 tecwin_scraper.py --email usuario@exemplo.com --senha senha123 --apenas-login

  # Usar variáveis de ambiente
  export TECWIN_EMAIL="usuario@exemplo.com"
  export TECWIN_SENHA="senha123"
  python3 tecwin_scraper.py --ncm 96170010
        """
    )
    
    parser.add_argument('--ncm', type=str, help='Código NCM a consultar (ex: 96170010)')
    parser.add_argument('--email', type=str, help='Email do usuário TECwin (ou use TECWIN_EMAIL env var)')
    parser.add_argument('--senha', type=str, help='Senha do usuário TECwin (ou use TECWIN_SENHA env var)')
    parser.add_argument('--headless', action='store_true', help='Executar em modo headless (sem interface gráfica)')
    parser.add_argument('--apenas-login', action='store_true', help='Apenas fazer login, não consultar NCM')
    parser.add_argument('--salvar-html', type=str, help='Salvar HTML da página em arquivo (opcional)')
    
    args = parser.parse_args()
    
    # Buscar credenciais de variáveis de ambiente se não fornecidas
    email = args.email or os.getenv('TECWIN_EMAIL')
    senha = args.senha or os.getenv('TECWIN_SENHA')
    
    if not email or not senha:
        parser.error("É necessário fornecer --email e --senha ou definir TECWIN_EMAIL e TECWIN_SENHA como variáveis de ambiente")
    
    if not args.ncm and not args.apenas_login:
        parser.error("É necessário fornecer --ncm ou usar --apenas-login")
    
    scraper = None
    try:
        scraper = TecwinScraper(headless=args.headless)
        
        # Fazer login
        if scraper.login(email, senha):
            logger.info("✅ Login realizado com sucesso!")
            
            if not args.apenas_login and args.ncm:
                # Consultar NCM
                dados = scraper.consultar_ncm(args.ncm)
                
                if dados:
                    print("\n" + "="*80)
                    print(f"📋 DADOS DO NCM {args.ncm}")
                    print("="*80)
                    
                    for chave, valor in dados.items():
                        if chave != 'html':  # Não mostrar HTML completo no console
                            print(f"{chave}: {valor}")
                    
                    # Salvar HTML se solicitado
                    if args.salvar_html and 'html' in dados:
                        with open(args.salvar_html, 'w', encoding='utf-8') as f:
                            f.write(dados['html'])
                        logger.info(f"✅ HTML salvo em: {args.salvar_html}")
                    
                    print("="*80)
                else:
                    logger.error("❌ Não foi possível consultar o NCM")
                    sys.exit(1)
            else:
                logger.info("✅ Login testado com sucesso!")
        else:
            logger.error("❌ Falha no login")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erro: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if scraper:
            scraper.fechar()


if __name__ == "__main__":
    main()












