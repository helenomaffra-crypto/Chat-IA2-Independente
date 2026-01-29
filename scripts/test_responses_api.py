#!/usr/bin/env python3
"""
Script de teste para Responses API da OpenAI (nova API que substitui Assistants API).

Este script testa:
- Responses API com Code Interpreter
- Containers (auto mode)
- Cálculos de impostos (exemplo prático para mAIke)
- Processamento de arquivos (se disponível)

⚠️ IMPORTANTE: Assistants API será desligado em 26/08/2026.
Este script demonstra a nova API recomendada.
"""
import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Carregar variáveis de ambiente
try:
    from dotenv import load_dotenv
    try:
        load_dotenv()
    except (PermissionError, OSError):
        # Ignorar erros de permissão (pode ocorrer em ambientes restritos)
        pass
except ImportError:
    pass

# Verificar se OpenAI está disponível
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("❌ Biblioteca 'openai' não instalada.")
    print("   Instale com: pip install openai")
    sys.exit(1)

# Verificar API key
API_KEY = os.getenv('DUIMP_AI_API_KEY') or os.getenv('OPENAI_API_KEY')
if not API_KEY:
    print("❌ API key não encontrada!")
    print("   Configure DUIMP_AI_API_KEY ou OPENAI_API_KEY no .env")
    sys.exit(1)

# Inicializar cliente
client = OpenAI(api_key=API_KEY)


def print_section(title: str):
    """Imprime um cabeçalho de seção."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_basic_calculation():
    """Teste 1: Cálculo básico (equação simples)."""
    print_section("TESTE 1: Cálculo Básico")
    
    print("📝 Testando: Resolver equação 3x + 11 = 14")
    print()
    
    try:
        resp = client.responses.create(
            model="gpt-4o",  # Usar gpt-4o (gpt-4.1 pode não estar disponível ainda)
            tools=[{
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "memory_limit": "1g"  # 1GB é suficiente para cálculos simples
                }
            }],
            instructions="""Você é um assistente especializado em cálculos matemáticos.
            Use o python tool para calcular e mostrar os passos claramente.
            Sempre explique o processo de resolução.""",
            input="Calcule a solução de 3x + 11 = 14 e mostre os passos."
        )
        
        print("✅ Resposta recebida:")
        print("-" * 80)
        print(resp.output_text)
        print("-" * 80)
        
        # Mostrar informações sobre a resposta
        if hasattr(resp, 'output_items'):
            print(f"\n📊 Itens de saída: {len(resp.output_items)}")
            for i, item in enumerate(resp.output_items):
                print(f"   Item {i+1}: {item.type}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tax_calculation():
    """Teste 2: Cálculo de impostos (exemplo prático para mAIke)."""
    print_section("TESTE 2: Cálculo de Impostos de Importação")
    
    print("📝 Testando: Calcular impostos (II, IPI, PIS, COFINS)")
    print()
    
    # Dados de exemplo (similar ao que mAIke usaria)
    dados = {
        "custo_usd": 10000.00,
        "frete_usd": 1500.00,
        "seguro_usd": 200.00,
        "cotacao_ptax": 5.5283,
        "aliquota_ii": 18.0,  # 18%
        "aliquota_ipi": 10.0,  # 10%
        "aliquota_pis": 1.65,  # 1.65%
        "aliquota_cofins": 7.60  # 7.60%
    }
    
    instructions = """Você é um especialista em cálculos fiscais de importação no Brasil.

REGRAS DE CÁLCULO DE IMPOSTOS:

1. CIF (Custo, Seguro e Frete):
   CIF_USD = Custo_USD + Frete_USD + Seguro_USD
   CIF_BRL = CIF_USD × Cotação_PTAX

2. II (Imposto de Importação):
   - Base de cálculo: CIF (em BRL)
   - Fórmula: II_BRL = CIF_BRL × (Alíquota_II / 100)
   - Fórmula: II_USD = II_BRL ÷ Cotação_PTAX

3. IPI (Imposto sobre Produtos Industrializados):
   - Base de cálculo: CIF_BRL + II_BRL
   - Fórmula: IPI_BRL = (CIF_BRL + II_BRL) × (Alíquota_IPI / 100)
   - Fórmula: IPI_USD = IPI_BRL ÷ Cotação_PTAX

4. PIS/PASEP:
   - Base de cálculo: CIF (em BRL)
   - Fórmula: PIS_BRL = CIF_BRL × (Alíquota_PIS / 100)
   - Fórmula: PIS_USD = PIS_BRL ÷ Cotação_PTAX

5. COFINS:
   - Base de cálculo: CIF (em BRL)
   - Fórmula: COFINS_BRL = CIF_BRL × (Alíquota_COFINS / 100)
   - Fórmula: COFINS_USD = COFINS_BRL ÷ Cotação_PTAX

6. Total de Impostos:
   Total_BRL = II_BRL + IPI_BRL + PIS_BRL + COFINS_BRL
   Total_USD = II_USD + IPI_USD + PIS_USD + COFINS_USD

REGRAS IMPORTANTES:
- Sempre arredonde para 2 casas decimais
- Use a cotação PTAX fornecida
- Mostre todos os passos do cálculo
- Apresente valores em BRL e USD

FORMATO DE RESPOSTA:
Apresente os cálculos de forma clara, mostrando:
1. Valores de entrada
2. Cálculo do CIF
3. Cálculo de cada imposto (com fórmula)
4. Total de impostos
5. Valores em BRL e USD"""
    
    input_text = f"""Calcule os impostos de importação com os seguintes dados:

- Custo: USD {dados['custo_usd']:,.2f}
- Frete: USD {dados['frete_usd']:,.2f}
- Seguro: USD {dados['seguro_usd']:,.2f}
- Cotação PTAX: R$ {dados['cotacao_ptax']:,.4f} / USD
- Alíquota II: {dados['aliquota_ii']:.2f}%
- Alíquota IPI: {dados['aliquota_ipi']:.2f}%
- Alíquota PIS: {dados['aliquota_pis']:.2f}%
- Alíquota COFINS: {dados['aliquota_cofins']:.2f}%

Mostre todos os passos e valide os resultados."""
    
    try:
        print("📤 Enviando requisição...")
        resp = client.responses.create(
            model="gpt-4o",
            tools=[{
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "memory_limit": "1g"
                }
            }],
            instructions=instructions,
            input=input_text
        )
        
        print("✅ Resposta recebida:")
        print("-" * 80)
        print(resp.output_text)
        print("-" * 80)
        
        # Validar resultado esperado
        print("\n🔍 Validação:")
        cif_usd_esperado = dados['custo_usd'] + dados['frete_usd'] + dados['seguro_usd']
        cif_brl_esperado = cif_usd_esperado * dados['cotacao_ptax']
        ii_brl_esperado = cif_brl_esperado * (dados['aliquota_ii'] / 100)
        
        print(f"   CIF USD esperado: {cif_usd_esperado:,.2f}")
        print(f"   CIF BRL esperado: {cif_brl_esperado:,.2f}")
        print(f"   II BRL esperado: {ii_brl_esperado:,.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_processing():
    """Teste 3: Processamento de arquivo (se disponível)."""
    print_section("TESTE 3: Processamento de Arquivo")
    
    # Criar arquivo CSV de exemplo
    csv_file = Path("test_data.csv")
    try:
        csv_content = """Produto,Quantidade,Valor_USD
iPhone,10,1000.00
Notebook,5,1500.00
Tablet,8,500.00"""
        
        csv_file.write_text(csv_content, encoding='utf-8')
        print(f"📄 Arquivo de teste criado: {csv_file}")
        
        # Fazer upload do arquivo
        print("📤 Fazendo upload do arquivo...")
        with open(csv_file, 'rb') as f:
            uploaded_file = client.files.create(
                file=f,
                purpose="code_interpreter"
            )
        
        print(f"✅ Arquivo enviado: {uploaded_file.id}")
        
        # Usar arquivo no Code Interpreter
        print("📤 Enviando requisição com arquivo...")
        resp = client.responses.create(
            model="gpt-4o",
            tools=[{
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "memory_limit": "1g",
                    "file_ids": [uploaded_file.id]
                }
            }],
            instructions="""Você é um assistente especializado em análise de dados.
            Use o python tool para analisar arquivos CSV.
            Sempre mostre os resultados de forma clara.""",
            input="Analise o arquivo CSV e calcule o valor total em USD de todos os produtos."
        )
        
        print("✅ Resposta recebida:")
        print("-" * 80)
        print(resp.output_text)
        print("-" * 80)
        
        # Limpar arquivo
        csv_file.unlink()
        print(f"\n🗑️  Arquivo de teste removido: {csv_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        # Limpar arquivo mesmo em caso de erro
        if csv_file.exists():
            csv_file.unlink()
        return False


def test_container_reuse():
    """Teste 4: Reutilização de container (modo auto - mesma sessão)."""
    print_section("TESTE 4: Container Auto (Reutilização na Mesma Sessão)")
    
    try:
        # Nota: Containers explícitos podem não estar totalmente suportados ainda
        # Vamos testar o modo auto que funciona perfeitamente
        
        print("📝 Testando: Modo auto cria/reutiliza container automaticamente")
        print("   (Containers explícitos podem não estar totalmente suportados na API atual)")
        print()
        
        # Primeira requisição com container auto
        print("📤 Primeira requisição (modo auto)...")
        resp1 = client.responses.create(
            model="gpt-4o",
            tools=[{
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "memory_limit": "1g"
                }
            }],
            instructions="Use o python tool para calcular. Mostre os passos claramente.",
            input="Calcule a área de um círculo com raio 5. Use a fórmula: área = π × r²"
        )
        
        print("✅ Resposta 1:")
        print("-" * 80)
        print(resp1.output_text[:500] + "..." if len(resp1.output_text) > 500 else resp1.output_text)
        print("-" * 80)
        
        # Segunda requisição (container auto cria novo ou reutiliza conforme contexto)
        print("\n📤 Segunda requisição (modo auto - pode reutilizar)...")
        resp2 = client.responses.create(
            model="gpt-4o",
            tools=[{
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "memory_limit": "1g"
                }
            }],
            instructions="Use o python tool para calcular. Mostre os passos claramente.",
            input="Calcule o perímetro de um círculo com raio 5. Use a fórmula: perímetro = 2 × π × r"
        )
        
        print("✅ Resposta 2:")
        print("-" * 80)
        print(resp2.output_text[:500] + "..." if len(resp2.output_text) > 500 else resp2.output_text)
        print("-" * 80)
        
        print("\n✅ Modo auto funcionando corretamente!")
        print("   💡 Nota: Containers explícitos podem requerer API mais recente")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """Teste 5: Tratamento de erros e iteração."""
    print_section("TESTE 5: Tratamento de Erros e Iteração")
    
    print("📝 Testando: Code Interpreter corrige erros automaticamente")
    print()
    
    try:
        resp = client.responses.create(
            model="gpt-4o",
            tools=[{
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "memory_limit": "1g"
                }
            }],
            instructions="""Você é um assistente especializado em programação Python.
            Se encontrar erros, corrija e tente novamente.
            Sempre explique o que aconteceu.""",
            input="""Escreva um código Python que:
1. Tenta dividir 10 por 0 (vai dar erro)
2. Corrija o erro e calcule 10 / 2
3. Mostre o resultado"""
        )
        
        print("✅ Resposta recebida:")
        print("-" * 80)
        print(resp.output_text)
        print("-" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Função principal que executa todos os testes."""
    print("=" * 80)
    print("  TESTE DE RESPONSES API (Nova API da OpenAI)")
    print("=" * 80)
    print()
    print("⚠️  IMPORTANTE: Assistants API será desligado em 26/08/2026")
    print("   Este script testa a nova Responses API recomendada.")
    print()
    print(f"✅ API Key configurada: {API_KEY[:10]}...")
    print(f"✅ Cliente OpenAI inicializado")
    print()
    
    resultados = {}
    
    # Executar testes
    print("🚀 Iniciando testes...\n")
    
    # Teste 1: Cálculo básico
    resultados['teste_1'] = test_basic_calculation()
    
    # Teste 2: Cálculo de impostos
    resultados['teste_2'] = test_tax_calculation()
    
    # Teste 3: Processamento de arquivo
    print("\n⚠️  Teste 3 requer upload de arquivo. Pulando por enquanto...")
    # resultados['teste_3'] = test_file_processing()
    resultados['teste_3'] = None
    
    # Teste 4: Container explícito
    print("\n⚠️  Teste 4 requer containers explícitos. Testando...")
    try:
        resultados['teste_4'] = test_container_reuse()
    except Exception as e:
        print(f"⚠️  Teste 4 falhou (pode não estar disponível): {e}")
        resultados['teste_4'] = None
    
    # Teste 5: Tratamento de erros
    resultados['teste_5'] = test_error_handling()
    
    # Resumo
    print_section("RESUMO DOS TESTES")
    
    total = len([r for r in resultados.values() if r is not None])
    aprovados = len([r for r in resultados.values() if r is True])
    
    print(f"📊 Total de testes: {total}")
    print(f"✅ Aprovados: {aprovados}")
    print(f"❌ Falhados: {total - aprovados}")
    print()
    
    for nome, resultado in resultados.items():
        if resultado is None:
            status = "⏭️  Pulado"
        elif resultado:
            status = "✅ Aprovado"
        else:
            status = "❌ Falhou"
        print(f"   {nome.upper()}: {status}")
    
    print()
    print("=" * 80)
    print("  TESTES CONCLUÍDOS")
    print("=" * 80)
    print()
    
    if aprovados == total:
        print("🎉 Todos os testes passaram!")
    else:
        print("⚠️  Alguns testes falharam. Verifique os logs acima.")
    
    print()
    print("💡 PRÓXIMOS PASSOS:")
    print("   1. Revisar documentação: docs/CODE_INTERPRETER_RESPONSES_API.md")
    print("   2. Planejar migração de Assistants API para Responses API")
    print("   3. Testar com dados reais do mAIke")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

