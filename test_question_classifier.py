#!/usr/bin/env python3
"""
Teste simples do QuestionClassifier.

Executa testes básicos dos métodos de classificação de perguntas.
"""
import sys
sys.path.insert(0, '.')

from services.utils.question_classifier import QuestionClassifier

def test_eh_pergunta_analitica():
    """Testa detecção de perguntas analíticas."""
    print("\n" + "="*60)
    print("TESTE: eh_pergunta_analitica")
    print("="*60)
    
    testes = [
        # (mensagem, esperado, descricao)
        ("top 10 clientes por valor CIF", True, "Ranking de top 10"),
        ("ranking de fornecedores", True, "Ranking"),
        ("total de processos por mês", True, "Agregação temporal"),
        ("média de valores importados", True, "Estatística"),
        ("distribuição de cargas", True, "Distribuição"),
        ("como está o vdm.003?", False, "Consulta específica"),
        ("qual a ncm de iphone?", False, "Pergunta de NCM"),
    ]
    
    todos_passaram = True
    for mensagem, esperado, descricao in testes:
        resultado = QuestionClassifier.eh_pergunta_analitica(mensagem)
        status = "✅" if resultado == esperado else "❌"
        if resultado != esperado:
            todos_passaram = False
        print(f"{status} {descricao}: '{mensagem}' → {resultado} (esperado: {esperado})")
    
    return todos_passaram


def test_eh_pergunta_conhecimento_geral():
    """Testa detecção de perguntas de conhecimento geral."""
    print("\n" + "="*60)
    print("TESTE: eh_pergunta_conhecimento_geral")
    print("="*60)
    
    testes = [
        # (mensagem, esperado, descricao)
        ("qual a cotação de frete de container?", True, "Cotação de mercado"),
        ("o que é uma DI?", True, "Conceito"),
        ("como funciona o processo de importação?", True, "Processo conceitual"),
        ("qual a diferença entre DI e DUIMP?", True, "Comparação conceitual"),
        ("qual o preço de container?", True, "Preço de mercado"),
        ("situacao do gym.0047/25", False, "Processo específico"),
        ("qual a ncm de iphone", False, "Pergunta de NCM (usa tool)"),
        ("como estão os mv5?", False, "Consulta de processos (usa tool)"),
        ("qual a explicação para classificação de carro de golfe", False, "Classificação fiscal (usa NESH)"),
    ]
    
    todos_passaram = True
    for mensagem, esperado, descricao in testes:
        resultado = QuestionClassifier.eh_pergunta_conhecimento_geral(mensagem)
        status = "✅" if resultado == esperado else "❌"
        if resultado != esperado:
            todos_passaram = False
        print(f"{status} {descricao}: '{mensagem}' → {resultado} (esperado: {esperado})")
    
    return todos_passaram


def test_eh_pergunta_generica():
    """Testa detecção de perguntas genéricas."""
    print("\n" + "="*60)
    print("TESTE: eh_pergunta_generica")
    print("="*60)
    
    # Simulação simples de extração de categoria
    def extrair_categoria_simples(mensagem: str):
        """Extrai categoria simples para teste."""
        import re
        categorias = ['vdm', 'alh', 'mv5', 'dmd', 'mss', 'bnd']
        mensagem_lower = mensagem.lower()
        for cat in categorias:
            if cat in mensagem_lower:
                return cat.upper()
        return None
    
    testes = [
        # (mensagem, esperado, descricao)
        ("quais processos têm pendência?", True, "Pergunta genérica sem categoria"),
        ("quais processos estão bloqueados?", True, "Pergunta genérica sem categoria"),
        ("mostre todos os processos", True, "Pergunta genérica"),
        ("como estão os vdm?", False, "Tem categoria específica"),
        ("quais estão bloqueados?", False, "Sem mencionar 'processos' (específica)"),
    ]
    
    todos_passaram = True
    for mensagem, esperado, descricao in testes:
        resultado = QuestionClassifier.eh_pergunta_generica(
            mensagem, 
            extrair_categoria_callback=extrair_categoria_simples
        )
        status = "✅" if resultado == esperado else "❌"
        if resultado != esperado:
            todos_passaram = False
        print(f"{status} {descricao}: '{mensagem}' → {resultado} (esperado: {esperado})")
    
    return todos_passaram


def test_identificar_se_precisa_contexto():
    """Testa detecção de necessidade de contexto."""
    print("\n" + "="*60)
    print("TESTE: identificar_se_precisa_contexto")
    print("="*60)
    
    # Simulação simples de extração de processo
    def extrair_processo_simples(mensagem: str):
        """Extrai processo simples para teste."""
        import re
        match = re.search(r'([a-z]{2,4}\.\d{1,4}/\d{2})', mensagem.lower())
        return match.group(1).upper() if match else None
    
    testes = [
        # (mensagem, esperado, descricao)
        ("tem bloqueio?", True, "Pergunta específica sem processo"),
        ("qual o frete?", True, "Pergunta específica sem processo"),
        ("qual a situação?", True, "Pergunta específica sem processo"),
        ("consulte o CE do processo MSS.0018/25", False, "Já tem processo"),
        ("qual processo tem bloqueio?", False, "Pergunta geral"),
        ("tem bloqueio no VDM.003/25?", False, "Já tem processo"),
    ]
    
    todos_passaram = True
    for mensagem, esperado, descricao in testes:
        resultado = QuestionClassifier.identificar_se_precisa_contexto(
            mensagem,
            extrair_processo_callback=extrair_processo_simples
        )
        status = "✅" if resultado == esperado else "❌"
        if resultado != esperado:
            todos_passaram = False
        print(f"{status} {descricao}: '{mensagem}' → {resultado} (esperado: {esperado})")
    
    return todos_passaram


def main():
    """Executa todos os testes."""
    print("\n" + "="*60)
    print("🧪 TESTES DO QuestionClassifier")
    print("="*60)
    
    resultados = []
    
    resultados.append(("eh_pergunta_analitica", test_eh_pergunta_analitica()))
    resultados.append(("eh_pergunta_conhecimento_geral", test_eh_pergunta_conhecimento_geral()))
    resultados.append(("eh_pergunta_generica", test_eh_pergunta_generica()))
    resultados.append(("identificar_se_precisa_contexto", test_identificar_se_precisa_contexto()))
    
    # Resumo
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    
    todos_passaram = True
    for nome, passou in resultados:
        status = "✅ PASSOU" if passou else "❌ FALHOU"
        print(f"{status}: {nome}")
        if not passou:
            todos_passaram = False
    
    print("\n" + "="*60)
    if todos_passaram:
        print("🎉 TODOS OS TESTES PASSARAM!")
    else:
        print("⚠️  ALGUNS TESTES FALHARAM")
    print("="*60 + "\n")
    
    return 0 if todos_passaram else 1


if __name__ == "__main__":
    sys.exit(main())
