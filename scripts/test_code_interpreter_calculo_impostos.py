#!/usr/bin/env python3
"""
Script de teste para demonstrar cálculo de impostos usando Code Interpreter.

Compara:
1. Método atual (Python local)
2. Método com Code Interpreter (Responses API)
"""

import sys
import os
from pathlib import Path

# Adicionar raiz do projeto ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Carregar variáveis de ambiente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv não instalado. Continuando sem .env...")
except (PermissionError, OSError) as e:
    print(f"⚠️ Não foi possível carregar .env: {e}")

import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_calculo_python_local():
    """Testa cálculo usando Python local (método atual)."""
    print("\n" + "="*80)
    print("TESTE 1: CÁLCULO COM PYTHON LOCAL (Método Atual)")
    print("="*80)
    
    from services.calculo_impostos_service import CalculoImpostosService
    
    # Dados de teste
    custo_usd = 10000.00
    frete_usd = 1500.00
    seguro_usd = 200.00
    cotacao_ptax = 5.5283
    aliquotas = {
        'ii': 18.0,
        'ipi': 10.0,
        'pis': 1.65,
        'cofins': 7.6
    }
    
    print(f"\n📊 Valores de Entrada:")
    print(f"  • Custo: USD {custo_usd:,.2f}")
    print(f"  • Frete: USD {frete_usd:,.2f}")
    print(f"  • Seguro: USD {seguro_usd:,.2f}")
    print(f"  • Cotação PTAX: R$ {cotacao_ptax:,.4f} / USD")
    print(f"  • Alíquotas: II={aliquotas['ii']}%, IPI={aliquotas['ipi']}%, PIS={aliquotas['pis']}%, COFINS={aliquotas['cofins']}%")
    
    # Calcular
    service = CalculoImpostosService()
    resultado = service.calcular_impostos(
        custo_usd=custo_usd,
        frete_usd=frete_usd,
        seguro_usd=seguro_usd,
        cotacao_ptax=cotacao_ptax,
        aliquotas=aliquotas
    )
    
    if resultado.get('sucesso'):
        print(f"\n✅ Resultado (Python Local):")
        print(f"  • CIF: R$ {resultado['cif']['brl']:,.2f} (USD {resultado['cif']['usd']:,.2f})")
        print(f"  • II: R$ {resultado['impostos']['ii']['brl']:,.2f} (USD {resultado['impostos']['ii']['usd']:,.2f})")
        print(f"  • IPI: R$ {resultado['impostos']['ipi']['brl']:,.2f} (USD {resultado['impostos']['ipi']['usd']:,.2f})")
        print(f"  • PIS: R$ {resultado['impostos']['pis']['brl']:,.2f} (USD {resultado['impostos']['pis']['usd']:,.2f})")
        print(f"  • COFINS: R$ {resultado['impostos']['cofins']['brl']:,.2f} (USD {resultado['impostos']['cofins']['usd']:,.2f})")
        print(f"  • Total: R$ {resultado['total_impostos']['brl']:,.2f} (USD {resultado['total_impostos']['usd']:,.2f})")
        
        # Formatar resposta completa
        resposta_formatada = service.formatar_resposta_calculo(resultado, incluir_explicacao=True)
        print(f"\n📝 Resposta Formatada:")
        print("-" * 80)
        print(resposta_formatada)
        print("-" * 80)
        
        return resultado
    else:
        print(f"\n❌ Erro: {resultado.get('erro')}")
        return None


def test_calculo_code_interpreter():
    """Testa cálculo usando Code Interpreter (Responses API)."""
    print("\n" + "="*80)
    print("TESTE 2: CÁLCULO COM CODE INTERPRETER (Responses API)")
    print("="*80)
    
    try:
        from services.responses_service import ResponsesService
    except ImportError as e:
        print(f"❌ Erro ao importar ResponsesService: {e}")
        print("⚠️ Certifique-se de que a biblioteca 'openai' está instalada")
        return None
    
    # Verificar se está habilitado
    responses_service = ResponsesService()
    if not responses_service.enabled:
        print("❌ ResponsesService não está habilitado")
        print("⚠️ Verifique se DUIMP_AI_API_KEY está configurada no .env")
        return None
    
    # Dados de teste
    custo_usd = 10000.00
    frete_usd = 1500.00
    seguro_usd = 200.00
    cotacao_ptax = 5.5283
    aliquotas = {
        'ii': 18.0,
        'ipi': 10.0,
        'pis': 1.65,
        'cofins': 7.6
    }
    
    print(f"\n📊 Valores de Entrada:")
    print(f"  • Custo: USD {custo_usd:,.2f}")
    print(f"  • Frete: USD {frete_usd:,.2f}")
    print(f"  • Seguro: USD {seguro_usd:,.2f}")
    print(f"  • Cotação PTAX: R$ {cotacao_ptax:,.4f} / USD")
    print(f"  • Alíquotas: II={aliquotas['ii']}%, IPI={aliquotas['ipi']}%, PIS={aliquotas['pis']}%, COFINS={aliquotas['cofins']}%")
    
    # Montar prompt para Code Interpreter
    prompt = f"""
Calcule os impostos de importação para os seguintes valores:

**Valores de Entrada:**
- Custo (VMLE): USD {custo_usd:,.2f}
- Frete: USD {frete_usd:,.2f}
- Seguro: USD {seguro_usd:,.2f}
- Cotação PTAX: R$ {cotacao_ptax:,.4f} / USD

**Alíquotas:**
- II (Imposto de Importação): {aliquotas['ii']:.2f}%
- IPI (Imposto sobre Produtos Industrializados): {aliquotas['ipi']:.2f}%
- PIS/PASEP: {aliquotas['pis']:.2f}%
- COFINS: {aliquotas['cofins']:.2f}%

**Instruções:**
1. Calcule o CIF (Custo + Frete + Seguro) em USD e converta para BRL usando a cotação PTAX
2. Calcule cada imposto seguindo as regras:
   - II: Base de cálculo = CIF, Fórmula = CIF × alíquota II
   - IPI: Base de cálculo = CIF + II, Fórmula = (CIF + II) × alíquota IPI
   - PIS: Base de cálculo = CIF, Fórmula = CIF × alíquota PIS
   - COFINS: Base de cálculo = CIF, Fórmula = CIF × alíquota COFINS
3. Converta todos os valores para USD usando a cotação PTAX
4. Apresente os resultados de forma clara e organizada
5. Mostre os cálculos passo a passo com fórmulas

**Formato de Resposta:**
- Mostre cada etapa do cálculo
- Apresente valores em BRL e USD
- Inclua fórmulas e explicações detalhadas
"""
    
    print(f"\n📤 Enviando para Code Interpreter...")
    print(f"   (Isso pode levar 2-5 segundos)")
    
    # Chamar Code Interpreter
    resultado = responses_service.buscar_legislacao_com_calculo(
        pergunta=prompt,
        dados_calculo={
            'custo_usd': custo_usd,
            'frete_usd': frete_usd,
            'seguro_usd': seguro_usd,
            'cotacao_ptax': cotacao_ptax,
            'aliquotas': aliquotas
        }
    )
    
    if resultado and resultado.get('sucesso'):
        print(f"\n✅ Resultado (Code Interpreter):")
        print("-" * 80)
        print(resultado.get('resposta', 'Sem resposta'))
        print("-" * 80)
        return resultado
    else:
        print(f"\n❌ Erro: {resultado.get('erro', 'Erro desconhecido') if resultado else 'Nenhum resultado'}")
        return None


def comparar_resultados(resultado_local: Dict[str, Any], resultado_code_interpreter: Dict[str, Any]):
    """Compara resultados dos dois métodos."""
    print("\n" + "="*80)
    print("COMPARAÇÃO DOS RESULTADOS")
    print("="*80)
    
    if not resultado_local or not resultado_code_interpreter:
        print("⚠️ Não é possível comparar - um dos resultados está faltando")
        return
    
    print("\n📊 Métricas:")
    print(f"  • Python Local: Execução instantânea, sem custo")
    print(f"  • Code Interpreter: ~2-5 segundos, ~$0.01-0.03 por cálculo")
    
    print("\n💡 Vantagens de cada método:")
    print("\n  Python Local:")
    print("    ✅ Rápido")
    print("    ✅ Sem custo")
    print("    ✅ Controle total")
    print("    ❌ Não explica automaticamente")
    
    print("\n  Code Interpreter:")
    print("    ✅ Explicação automática detalhada")
    print("    ✅ Validação automática")
    print("    ✅ Flexível para novos cálculos")
    print("    ❌ Mais lento")
    print("    ❌ Tem custo por uso")


def main():
    """Executa todos os testes."""
    print("\n" + "="*80)
    print("TESTE: CÁLCULO DE IMPOSTOS - PYTHON LOCAL vs CODE INTERPRETER")
    print("="*80)
    
    # Teste 1: Python Local
    resultado_local = test_calculo_python_local()
    
    # Teste 2: Code Interpreter
    resultado_code_interpreter = test_calculo_code_interpreter()
    
    # Comparação
    comparar_resultados(resultado_local, resultado_code_interpreter)
    
    print("\n" + "="*80)
    print("TESTES CONCLUÍDOS")
    print("="*80)
    print("\n💡 Próximos passos:")
    print("  1. Analise os resultados acima")
    print("  2. Veja a documentação: docs/CODE_INTERPRETER_CALCULO_IMPOSTOS.md")
    print("  3. Decida qual método usar ou se quer uma abordagem híbrida")


if __name__ == "__main__":
    main()



