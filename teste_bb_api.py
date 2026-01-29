#!/usr/bin/env python3
"""
Script de teste para API de Extratos do Banco do Brasil
"""
import os
import sys
import json

# Tentar importar datetime de forma mais segura
try:
    from datetime import datetime, timedelta
except ImportError:
    print("⚠️ Aviso: datetime não disponível, usando alternativas")
    datetime = None
    timedelta = None

from utils.banco_brasil_api import BancoBrasilConfig, BancoBrasilExtratoAPI

def main():
    print("=" * 60)
    print("🧪 TESTE DA API DE EXTRATOS DO BANCO DO BRASIL")
    print("=" * 60)
    
    # Carregar variáveis de ambiente
    from dotenv import load_dotenv
    load_dotenv()
    
    # Verificar credenciais
    client_id = os.getenv("BB_CLIENT_ID")
    client_secret = os.getenv("BB_CLIENT_SECRET")
    gw_dev_app_key = os.getenv("BB_DEV_APP_KEY")
    # ⚠️ IMPORTANTE: Verifique no portal do BB qual ambiente está configurado
    # Se o coletor está em "Produção" no portal → use "production"
    # Se o coletor está em "Homologação" no portal → use "sandbox"
    # Por padrão, vamos tentar production primeiro (conforme tela mostrada)
    # Mas se BB_ENVIRONMENT estiver definido no .env, usa o valor do .env
    environment = os.getenv("BB_ENVIRONMENT", "production")
    
    # Aviso se estiver usando sandbox mas a aplicação está em produção
    if environment == "sandbox":
        print("⚠️ AVISO: Usando ambiente SANDBOX")
        print("   Se sua aplicação está em PRODUÇÃO no portal, configure BB_ENVIRONMENT=production no .env")
    
    print(f"\n📋 Configuração:")
    print(f"   Ambiente: {environment}")
    print(f"   Client ID: {client_id[:20] + '...' if client_id and len(client_id) > 20 else 'NÃO CONFIGURADO'}")
    print(f"   Client Secret: {'✅ Configurado' if client_secret else '❌ NÃO CONFIGURADO'}")
    print(f"   gw-dev-app-key: {gw_dev_app_key[:20] + '...' if gw_dev_app_key and len(gw_dev_app_key) > 20 else 'NÃO CONFIGURADO'}")
    
    if not client_id or not client_secret or not gw_dev_app_key:
        print("\n❌ ERRO: Credenciais não configuradas no .env")
        print("   Configure BB_CLIENT_ID, BB_CLIENT_SECRET e BB_DEV_APP_KEY")
        return 1
    
    # Criar configuração
    config = BancoBrasilConfig(
        client_id=client_id,
        client_secret=client_secret,
        gw_dev_app_key=gw_dev_app_key,
        environment=environment
    )
    
    print(f"\n🌐 Endpoint base: {config.base_url}")
    print(f"🔑 Token URL: {config.token_url}")
    
    # Criar cliente API
    api = BancoBrasilExtratoAPI(config, debug=True)
    
    # Teste 1: Obter token OAuth
    print("\n" + "=" * 60)
    print("TESTE 1: Obter Token OAuth")
    print("=" * 60)
    try:
        token = api._obter_token()  # Método correto: _obter_token()
        print(f"✅ Token obtido com sucesso!")
        print(f"   Token (primeiros 30 chars): {token[:30]}...")
    except Exception as e:
        print(f"❌ Erro ao obter token: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Teste 2: Consultar extrato (últimos 30 dias - sem datas)
    print("\n" + "=" * 60)
    print("TESTE 2: Consultar Extrato (últimos 30 dias)")
    print("=" * 60)
    
    # Tentar diferentes contas de teste (conforme disponibilidade no Sandbox)
    contas_teste = [
        ("1505", "1348"),  # Conta original
        # Adicione outras contas aqui se necessário
    ]
    
    # Permitir que o usuário informe conta via variável de ambiente
    # Agência 1251-3 → usar 1251 (sem dígito verificador)
    # Conta 50483-1 → usar 504831 (com dígito verificador)
    agencia_teste = os.getenv("BB_TEST_AGENCIA", "1251")
    conta_teste = os.getenv("BB_TEST_CONTA", "50483")
    
    print(f"   Agência: {agencia_teste}")
    print(f"   Conta: {conta_teste}")
    print(f"   Período: últimos 30 dias (padrão)")
    print(f"\n💡 Dica: Configure BB_TEST_AGENCIA e BB_TEST_CONTA no .env para testar outras contas")
    
    try:
        # Habilitar debug para ver a resposta completa
        api.debug = True
        
        extrato = api.consultar_extrato(
            agencia=agencia_teste,
            conta=conta_teste,
            pagina=1,
            registros_por_pagina=50  # Menor para teste rápido
        )
        
        print(f"\n✅ Extrato obtido com sucesso!")
        print(f"   Página atual: {extrato.get('numeroPaginaAtual', 'N/A')}")
        print(f"   Registros nesta página: {extrato.get('quantidadeRegistroPaginaAtual', 'N/A')}")
        print(f"   Total de registros: {extrato.get('quantidadeTotalRegistro', 'N/A')}")
        print(f"   Total de páginas: {extrato.get('quantidadeTotalPagina', 'N/A')}")
        
        # Mostrar alguns lançamentos
        listaLancamento = extrato.get('listaLancamento', {})
        if isinstance(listaLancamento, dict):
            # Se for objeto, tentar encontrar array dentro
            for key in listaLancamento.keys():
                if isinstance(listaLancamento[key], list):
                    lancamentos = listaLancamento[key]
                    break
            else:
                lancamentos = []
        else:
            lancamentos = listaLancamento if isinstance(listaLancamento, list) else []
        
        if lancamentos:
            print(f"\n📋 Primeiros {min(3, len(lancamentos))} lançamentos:")
            for i, lanc in enumerate(lancamentos[:3], 1):
                data = str(lanc.get('dataLancamento', 'N/A'))
                valor = lanc.get('valorLancamento', 0)
                sinal = lanc.get('indicadorSinalLancamento', 'N/A')
                descricao = lanc.get('textoDescricaoHistorico', 'N/A')
                print(f"   {i}. {data} | {sinal} R$ {valor:.2f} | {descricao}")
        else:
            print("\n⚠️ Nenhum lançamento encontrado no período")
            print(f"   Estrutura recebida: {type(listaLancamento)}")
            if isinstance(listaLancamento, dict):
                print(f"   Chaves: {list(listaLancamento.keys())[:5]}")
        
    except ValueError as e:
        print(f"❌ Erro de validação: {e}")
        return 1
    except PermissionError as e:
        print(f"❌ Erro de autorização: {e}")
        print(f"\n💡 Dica: O erro 403 geralmente significa que:")
        print(f"   - A conta/agência não está cadastrada no Sandbox do BB")
        print(f"   - É necessário cadastrar dados de teste no Sandbox Admin")
        print(f"   - Verifique no portal do BB (https://developers.bb.com.br) se precisa configurar contas de teste")
        return 1
    except RuntimeError as e:
        error_msg = str(e)
        print(f"❌ Erro: {e}")
        
        if "mTLS" in error_msg or "certificado" in error_msg.lower():
            print(f"\n💡 ERRO DE CERTIFICADO mTLS:")
            print(f"   - A API de Extratos em PRODUÇÃO requer certificado mTLS")
            print(f"   - Você precisa:")
            print(f"     1. Obter certificado ICP-Brasil tipo A1 (e-CNPJ)")
            print(f"     2. Enviar ao BB via Portal Developers (menu Certificados)")
            print(f"     3. Aguardar aprovação (até 3 dias úteis)")
            print(f"     4. Configurar no .env: BB_CERT_PATH=/caminho/certificado.pem")
            print(f"\n   📖 Veja CONFIGURACAO_PRODUCAO_BB.md para mais detalhes")
        else:
            print(f"\n💡 Dica: O erro 500 geralmente significa que:")
            print(f"   - A requisição foi autorizada (progresso!)")
            print(f"   - Mas houve um erro interno no servidor do BB")
            print(f"   - Pode ser temporário - tente novamente em alguns instantes")
            print(f"   - Ou a conta pode não ter dados configurados no Sandbox")
        return 1
    except Exception as e:
        print(f"❌ Erro ao consultar extrato: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Teste 3: Consultar extrato com período específico
    if datetime and timedelta:
        print("\n" + "=" * 60)
        print("TESTE 3: Consultar Extrato (período específico)")
        print("=" * 60)
        
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(days=7)  # Últimos 7 dias
        
        print(f"   Agência: {agencia_teste}")
        print(f"   Conta: {conta_teste}")
        print(f"   Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
        
        try:
            extrato = api.consultar_extrato(
                agencia=agencia_teste,
                conta=conta_teste,
                data_inicio=data_inicio,
                data_fim=data_fim,
                pagina=1,
                registros_por_pagina=50
            )
            
            print(f"\n✅ Extrato obtido com sucesso!")
            print(f"   Total de registros: {extrato.get('quantidadeTotalRegistro', 'N/A')}")
            
        except ValueError as e:
            print(f"❌ Erro de validação: {e}")
            return 1
        except PermissionError as e:
            print(f"❌ Erro de autorização: {e}")
            return 1
        except Exception as e:
            print(f"❌ Erro ao consultar extrato: {e}")
            import traceback
            traceback.print_exc()
            return 1
    else:
        print("\n⚠️ Teste 3 pulado (datetime não disponível)")
    
    print("\n" + "=" * 60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())

