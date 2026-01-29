#!/usr/bin/env python3
"""
Script de teste para simular pagamento de boleto no sandbox Santander.

Este script:
1. Extrai dados do boleto (código de barras, valor, vencimento)
2. Consulta saldo no Santander
3. Inicia pagamento no sandbox
4. Efetiva pagamento no sandbox

Uso:
    python3 scripts/teste_pagamento_boleto_sandbox.py <caminho_do_boleto.pdf>
    
Exemplo:
    python3 scripts/teste_pagamento_boleto_sandbox.py downloads/60608-Cobranca.pdf
"""

import sys
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ✅ CARREGAR .env ANTES DE IMPORTAR SERVIÇOS
def load_env_from_file(filepath: str = '.env') -> None:
    """Carrega variáveis de ambiente do arquivo .env"""
    possible_paths = [
        Path(filepath),
        Path(__file__).parent.parent / filepath,  # Relativo ao diretório raiz
        Path(os.getcwd()) / filepath,
    ]
    
    for path in possible_paths:
        if path and path.exists():
            abs_path = path.absolute()
            try:
                with open(abs_path, 'r', encoding='utf-8') as env_file:
                    for line in env_file:
                        # ✅ CORREÇÃO: Remover espaços no início ANTES de processar
                        # Isso corrige linhas com indentação no .env
                        s = line.strip()
                        if not s or s.startswith('#') or '=' not in s:
                            continue
                        k, v = s.split('=', 1)
                        # Remover espaços das chaves e valores
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        # Ignorar linhas vazias após strip
                        if not k:
                            continue
                        os.environ[k] = v
                        # Debug: mostrar variáveis críticas sendo carregadas
                        if 'SANTANDER_PAYMENTS' in k or 'SANTANDER_WORKSPACE' in k:
                            print(f"   ✅ Carregado: {k}={'*' * min(len(v), 10)}...")
                print(f"✅ Variáveis de ambiente carregadas do .env: {abs_path}")
                return
            except (OSError, PermissionError) as e:
                # .env pode estar protegido - isso é normal
                # As variáveis podem já estar no ambiente (se rodar via Flask)
                if "Operation not permitted" in str(e):
                    print(f"⚠️ .env está protegido (normal). Verificando variáveis de ambiente...")
                    # Verificar se variáveis críticas já estão no ambiente
                    if os.getenv('SANTANDER_PAYMENTS_CLIENT_ID') or os.getenv('SANTANDER_CLIENT_ID'):
                        print(f"✅ Variáveis de ambiente já carregadas (provavelmente via Flask)")
                        return
                else:
                    print(f"⚠️ Erro ao carregar .env de {abs_path}: {e}")
                continue
    
    # Verificar se variáveis já estão no ambiente
    if os.getenv('SANTANDER_PAYMENTS_CLIENT_ID') or os.getenv('SANTANDER_CLIENT_ID'):
        print("✅ Variáveis de ambiente já disponíveis (provavelmente via Flask)")
    else:
        print("⚠️ Arquivo .env não encontrado ou não acessível.")
        print("   💡 Se estiver rodando via Flask, as variáveis já devem estar carregadas.")
        print("   💡 Se estiver rodando diretamente, configure as variáveis no .env ou exporte no terminal.")

# Carregar .env antes de importar serviços
load_env_from_file()

# ✅ DIAGNÓSTICO: Verificar se variáveis estão carregadas
print("🔍 Diagnóstico de Variáveis de Ambiente:")
print("-" * 60)
santander_payments_client_id = os.getenv('SANTANDER_PAYMENTS_CLIENT_ID') or os.getenv('SANTANDER_CLIENT_ID')
santander_payments_client_secret = os.getenv('SANTANDER_PAYMENTS_CLIENT_SECRET') or os.getenv('SANTANDER_CLIENT_SECRET')
santander_workspace_id = os.getenv('SANTANDER_WORKSPACE_ID')
santander_payments_cert = os.getenv('SANTANDER_PAYMENTS_CERT_FILE') or os.getenv('SANTANDER_PAYMENTS_CERT_PATH') or os.getenv('SANTANDER_CERT_FILE') or os.getenv('SANTANDER_CERT_PATH')

print(f"   SANTANDER_PAYMENTS_CLIENT_ID: {'✅ Configurado' if santander_payments_client_id else '❌ Não configurado'}")
print(f"   SANTANDER_PAYMENTS_CLIENT_SECRET: {'✅ Configurado' if santander_payments_client_secret else '❌ Não configurado'}")
print(f"   SANTANDER_WORKSPACE_ID: {'✅ Configurado' if santander_workspace_id else '❌ Não configurado'} ({santander_workspace_id or 'N/A'})")
print(f"   Certificado mTLS: {'✅ Configurado' if santander_payments_cert else '❌ Não configurado'}")
print()

try:
    import PyPDF2
except ImportError:
    print("❌ PyPDF2 não instalado. Instale com: pip install PyPDF2")
    sys.exit(1)

from services.santander_payments_service import SantanderPaymentsService
from services.santander_service import SantanderService


class BoletoParser:
    """Parser simples para extrair dados de boletos bancários."""
    
    def extrair_dados_boleto(self, pdf_path: str) -> dict:
        """
        Extrai dados do boleto do PDF.
        
        Returns:
            Dict com: codigo_barras, valor, vencimento, beneficiario, nosso_numero
        """
        print(f"📄 Processando boleto: {pdf_path}")
        
        # 1. Extrair texto do PDF
        texto = self._extrair_texto_pdf(pdf_path)
        
        if not texto:
            return {
                'sucesso': False,
                'erro': 'Não foi possível extrair texto do PDF'
            }
        
        print(f"✅ Texto extraído: {len(texto)} caracteres")
        
        # 2. Extrair código de barras
        codigo_barras = self._extrair_codigo_barras(texto)
        print(f"🔍 Código de barras: {codigo_barras}")
        
        # 3. Extrair valor
        valor = self._extrair_valor(texto)
        print(f"💰 Valor: R$ {valor:,.2f}" if valor else "💰 Valor: Não encontrado")
        
        # 4. Extrair vencimento
        vencimento = self._extrair_vencimento(texto)
        print(f"📅 Vencimento: {vencimento}")
        
        # 5. Extrair beneficiário
        beneficiario = self._extrair_beneficiario(texto)
        print(f"👤 Beneficiário: {beneficiario}")
        
        if not codigo_barras or not valor:
            return {
                'sucesso': False,
                'erro': 'Não foi possível extrair código de barras ou valor do boleto'
            }
        
        return {
            'sucesso': True,
            'codigo_barras': codigo_barras,
            'valor': valor,
            'vencimento': vencimento,
            'beneficiario': beneficiario,
            'texto_extraido': texto[:500]  # Primeiros 500 chars para debug
        }
    
    def _extrair_texto_pdf(self, pdf_path: str) -> str:
        """Extrai texto de conteúdo PDF."""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                print(f"   📄 PDF tem {len(pdf_reader.pages)} página(s)")
                
                # Verificar se PDF está criptografado
                if pdf_reader.is_encrypted:
                    print("   ⚠️ PDF está criptografado, tentando descriptografar...")
                    try:
                        pdf_reader.decrypt("")  # Tentar sem senha
                    except:
                        print("   ❌ PDF requer senha para leitura")
                        return ""
                
                texto = ""
                for i, page in enumerate(pdf_reader.pages, start=1):
                    try:
                        texto_pagina = page.extract_text()
                        if texto_pagina:
                            texto += texto_pagina + "\n"
                            print(f"   ✅ Página {i}: {len(texto_pagina)} caracteres extraídos")
                        else:
                            print(f"   ⚠️ Página {i}: Nenhum texto extraído (pode ser escaneada/imagem)")
                    except Exception as e:
                        print(f"   ⚠️ Erro ao extrair texto da página {i}: {e}")
                        continue
                
                if not texto.strip():
                    print("   ⚠️ ATENÇÃO: PDF não retornou texto. Pode ser:")
                    print("      • PDF escaneado (imagem) - requer OCR")
                    print("      • PDF com texto em imagens")
                    print("      • PDF com formatação especial")
                    print("   💡 SOLUÇÃO: Use dados manuais para teste (veja opção abaixo)")
                
                return texto.strip()
                
        except FileNotFoundError:
            print(f"   ❌ Arquivo não encontrado: {pdf_path}")
            return ""
        except PermissionError:
            print(f"   ❌ Sem permissão para ler arquivo: {pdf_path}")
            return ""
        except Exception as e:
            print(f"   ❌ Erro ao ler PDF: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def _extrair_codigo_barras(self, texto: str) -> str:
        """Extrai código de barras do texto."""
        # Padrão 1: Código com pontos e espaços (formato legível)
        # Ex: 34191.09321 64129.922932 80145.580009 3 13510000090000
        padrao1 = r'(\d{5}\.?\d{5}\s?\d{5}\.?\d{6}\s?\d{5}\.?\d{6}\s?\d\s?\d{14})'
        match = re.search(padrao1, texto)
        if match:
            codigo = match.group(1)
            # Limpar pontos e espaços
            codigo_limpo = re.sub(r'[.\s]', '', codigo)
            # Validar tamanho (44 ou 47 dígitos)
            if len(codigo_limpo) in [44, 47]:
                return codigo_limpo
        
        # Padrão 2: Código sem formatação (44 ou 47 dígitos consecutivos)
        padrao2 = r'(\d{44,47})'
        match = re.search(padrao2, texto)
        if match:
            codigo = match.group(1)
            if len(codigo) in [44, 47]:
                return codigo
        
        # Padrão 3: Linha de código de barras (Autenticação Mecânica)
        padrao3 = r'Autenticação\s+Mecânica.*?(\d{5}\.?\d{5}\s?\d{5}\.?\d{6}\s?\d{5}\.?\d{6}\s?\d\s?\d{14})'
        match = re.search(padrao3, texto, re.IGNORECASE | re.DOTALL)
        if match:
            codigo = match.group(1)
            codigo_limpo = re.sub(r'[.\s]', '', codigo)
            if len(codigo_limpo) in [44, 47]:
                return codigo_limpo
        
        return None
    
    def _extrair_valor(self, texto: str) -> float:
        """Extrai valor do boleto."""
        # Padrão 1: "Valor do documento" ou "Valor" seguido de número
        padroes = [
            r'Valor\s+(?:do\s+)?documento\s*:?\s*R?\$?\s*([\d.,]+)',
            r'Valor\s*:?\s*R?\$?\s*([\d.,]+)',
            r'\(=\).*?Valor\s*:?\s*R?\$?\s*([\d.,]+)',
        ]
        
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                valor_str = match.group(1).replace('.', '').replace(',', '.')
                try:
                    return float(valor_str)
                except:
                    continue
        
        return None
    
    def _extrair_vencimento(self, texto: str) -> str:
        """Extrai data de vencimento."""
        # Padrão: DD/MM/YYYY
        padroes = [
            r'Vencimento\s*:?\s*(\d{2}/\d{2}/\d{4})',
            r'Venc\.\s*:?\s*(\d{2}/\d{2}/\d{4})',
        ]
        
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                data_str = match.group(1)
                # Converter para YYYY-MM-DD
                try:
                    dt = datetime.strptime(data_str, '%d/%m/%Y')
                    return dt.strftime('%Y-%m-%d')
                except:
                    continue
        
        return None
    
    def _extrair_beneficiario(self, texto: str) -> str:
        """Extrai nome do beneficiário."""
        # Padrão: "Cedente" seguido de nome
        padroes = [
            r'Cedente\s+(.+?)(?:\n|Agência|CNPJ|Código)',
            r'Cedente\s+(.+?)(?:\n\n|$)',
        ]
        
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
            if match:
                beneficiario = match.group(1).strip()
                # Limpar quebras de linha
                beneficiario = re.sub(r'\s+', ' ', beneficiario)
                if len(beneficiario) > 5:  # Nome válido
                    return beneficiario
        
        return None


def main():
    """Função principal."""
    if len(sys.argv) < 2:
        print("❌ Uso: python3 scripts/teste_pagamento_boleto_sandbox.py <caminho_do_boleto.pdf>")
        print("\nExemplo:")
        print("  python3 scripts/teste_pagamento_boleto_sandbox.py downloads/60608-Cobranca.pdf")
        sys.exit(1)
    
    # Modo dados diretos (para teste rápido)
    if sys.argv[1] == '--dados':
        if len(sys.argv) < 4:
            print("❌ Uso: python3 scripts/teste_pagamento_boleto_sandbox.py --dados <codigo_barras> <valor> [vencimento]")
            print("\nExemplo:")
            print("  python3 scripts/teste_pagamento_boleto_sandbox.py --dados 34191093216412992293280145580009313510000090000 900.00 2026-02-08")
            sys.exit(1)
        
        codigo_barras = sys.argv[2]
        try:
            valor = float(sys.argv[3])
        except:
            print("❌ Valor inválido")
            sys.exit(1)
        
        vencimento = sys.argv[4] if len(sys.argv) > 4 else None
        
        dados_boleto = {
            'sucesso': True,
            'codigo_barras': codigo_barras,
            'valor': valor,
            'vencimento': vencimento,
            'beneficiario': None
        }
        
        print("=" * 60)
        print("🧪 TESTE DE PAGAMENTO DE BOLETO - SANDBOX SANTANDER (DADOS MANUAIS)")
        print("=" * 60)
        print()
        print("📋 FASE 1: Dados do Boleto (Fornecidos Manualmente)")
        print("-" * 60)
        print(f"✅ Código de barras: {codigo_barras}")
        print(f"✅ Valor: R$ {valor:,.2f}")
        print(f"✅ Vencimento: {vencimento or 'N/A'}")
        print()
        
        return _processar_pagamento(dados_boleto)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("🧪 TESTE DE PAGAMENTO DE BOLETO - SANDBOX SANTANDER")
    print("=" * 60)
    print()
    
    # 1. Extrair dados do boleto
    print("📋 FASE 1: Extração de Dados do Boleto")
    print("-" * 60)
    parser = BoletoParser()
    dados_boleto = parser.extrair_dados_boleto(pdf_path)
    
    if not dados_boleto.get('sucesso'):
        print(f"❌ Erro ao processar boleto: {dados_boleto.get('erro')}")
        print()
        print("=" * 60)
        print("💡 SOLUÇÃO ALTERNATIVA: Teste com Dados Manuais")
        print("=" * 60)
        print()
        print("Se o PDF não puder ser processado, você pode testar com dados manuais:")
        print()
        print("Do boleto fornecido, use:")
        print("  • Código de barras: 34191093216412992293280145580009313510000090000")
        print("  • Valor: 900.00")
        print("  • Vencimento: 2026-02-08")
        print()
        print("Comando:")
        print("  python3 scripts/teste_pagamento_boleto_sandbox.py --dados 34191093216412992293280145580009313510000090000 900.00 2026-02-08")
        print()
        sys.exit(1)
    
    print("✅ Dados extraídos com sucesso!")
    return _processar_pagamento(dados_boleto)


def _processar_pagamento(dados_boleto: dict):
    """Processa o pagamento com os dados do boleto."""
    print()
    
    # 2. Consultar saldo
    print("💰 FASE 2: Consulta de Saldo")
    print("-" * 60)
    try:
        santander_service = SantanderService()
        saldo_result = santander_service.consultar_saldo()
        
        if not saldo_result.get('sucesso'):
            print(f"⚠️ Aviso: Não foi possível consultar saldo: {saldo_result.get('erro')}")
            print("   Continuando com o teste mesmo assim...")
            saldo_disponivel = None
        else:
            saldo_disponivel = saldo_result.get('dados', {}).get('disponivel', 0)
            print(f"✅ Saldo disponível: R$ {saldo_disponivel:,.2f}")
            
            # Validar saldo
            valor_boleto = dados_boleto.get('valor', 0)
            if saldo_disponivel < valor_boleto:
                print(f"⚠️ Aviso: Saldo insuficiente!")
                print(f"   Disponível: R$ {saldo_disponivel:,.2f}")
                print(f"   Necessário: R$ {valor_boleto:,.2f}")
                print("   Continuando com o teste mesmo assim (sandbox)...")
            else:
                saldo_apos = saldo_disponivel - valor_boleto
                print(f"✅ Saldo após pagamento: R$ {saldo_apos:,.2f}")
    except Exception as e:
        print(f"⚠️ Erro ao consultar saldo: {e}")
        print("   Continuando com o teste mesmo assim...")
        saldo_disponivel = None
    
    print()
    
    # 3. Iniciar pagamento
    print("🚀 FASE 3: Iniciar Pagamento no Sandbox")
    print("-" * 60)
    try:
        payments_service = SantanderPaymentsService()
        
        # Gerar payment_id único
        payment_id = str(uuid.uuid4())
        print(f"📝 Payment ID gerado: {payment_id}")
        
        # Data de pagamento (sempre hoje no sandbox - API não permite datas futuras)
        vencimento = dados_boleto.get('vencimento')
        hoje = datetime.now().strftime('%Y-%m-%d')
        
        # Validar se vencimento é futuro
        if vencimento:
            try:
                vencimento_dt = datetime.strptime(vencimento, '%Y-%m-%d')
                hoje_dt = datetime.now()
                if vencimento_dt > hoje_dt:
                    print(f"⚠️ Vencimento ({vencimento}) é futuro. Usando data de hoje para sandbox.")
                    payment_date = hoje
                else:
                    payment_date = vencimento
            except:
                # Se não conseguir parsear, usar hoje
                payment_date = hoje
        else:
            payment_date = hoje
        
        print(f"📅 Data de pagamento: {payment_date}")
        if vencimento and vencimento != payment_date:
            print(f"   (Vencimento original: {vencimento})")
        
        # Iniciar pagamento
        resultado_iniciar = payments_service.iniciar_bank_slip_payment(
            payment_id=payment_id,
            code=dados_boleto.get('codigo_barras'),
            payment_date=payment_date
        )
        
        if not resultado_iniciar.get('sucesso'):
            print(f"❌ Erro ao iniciar pagamento: {resultado_iniciar.get('erro')}")
            print(f"   Resposta: {resultado_iniciar.get('resposta')}")
            sys.exit(1)
        
        print("✅ Pagamento iniciado com sucesso!")
        print(f"   Status: {resultado_iniciar.get('dados', {}).get('status', 'N/A')}")
        print()
        
        # 4. Efetivar pagamento
        print("✅ FASE 4: Efetivar Pagamento no Sandbox")
        print("-" * 60)
        
        resultado_efetivar = payments_service.efetivar_bank_slip_payment(
            payment_id=payment_id,
            payment_value=dados_boleto.get('valor')
        )
        
        if not resultado_efetivar.get('sucesso'):
            print(f"❌ Erro ao efetivar pagamento: {resultado_efetivar.get('erro')}")
            print(f"   Resposta: {resultado_efetivar.get('resposta')}")
            sys.exit(1)
        
        print("✅ Pagamento efetivado com sucesso!")
        print(f"   Status: {resultado_efetivar.get('dados', {}).get('status', 'N/A')}")
        print()
        
        # 5. Consultar pagamento
        print("🔍 FASE 5: Consultar Status do Pagamento")
        print("-" * 60)
        
        resultado_consultar = payments_service.consultar_bank_slip_payment(
            payment_id=payment_id
        )
        
        if resultado_consultar.get('sucesso'):
            print("✅ Status do pagamento consultado!")
            print(f"   Resposta: {resultado_consultar.get('resposta')}")
        else:
            print(f"⚠️ Aviso: Não foi possível consultar status: {resultado_consultar.get('erro')}")
        
        print()
        print("=" * 60)
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 60)
        print()
        print("📊 Resumo:")
        print(f"   • Código de barras: {dados_boleto.get('codigo_barras')}")
        print(f"   • Valor: R$ {dados_boleto.get('valor'):,.2f}")
        print(f"   • Vencimento: {dados_boleto.get('vencimento') or 'N/A'}")
        print(f"   • Beneficiário: {dados_boleto.get('beneficiario') or 'N/A'}")
        print(f"   • Payment ID: {payment_id}")
        print(f"   • Status final: {resultado_efetivar.get('dados', {}).get('status', 'N/A')}")
        print()
        print("⚠️ LEMBRE-SE: Este é um teste no SANDBOX - nenhum dinheiro foi movimentado!")
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
