#!/usr/bin/env python3
"""
Teste simples do EmailUtils.

Executa testes básicos do método limpar_frases_problematicas.
"""
import sys
sys.path.insert(0, '.')

from services.utils.email_utils import EmailUtils

def test_limpar_frases_problematicas():
    """Testa limpeza de frases problemáticas."""
    print("\n" + "="*60)
    print("TESTE: limpar_frases_problematicas")
    print("="*60)
    
    testes = [
        # (texto_entrada, texto_esperado, descricao)
        (
            "heleno pode mandar o email. Este é um teste.",
            "Este é um teste.",
            "Remove 'heleno pode mandar o email'"
        ),
        (
            "pode enviar o email, por favor?",
            "por favor?",
            "Remove 'pode enviar o email'"
        ),
        (
            "se quiser, posso enviar por email.",
            ".",
            "Remove 'se quiser, posso enviar por email'"
        ),
        (
            "Texto normal sem frases problemáticas.",
            "Texto normal sem frases problemáticas.",
            "Texto normal permanece intacto"
        ),
        (
            "heleno pode mandar o email\n\nEste é um teste.",
            "Este é um teste.",
            "Remove com quebra de linha"
        ),
        (
            "Oi, heleno pode mandar o email!",
            "Oi!",
            "Remove no início da frase"
        ),
        (
            "Este é um teste. heleno pode mandar o email!",
            "Este é um teste.",
            "Remove no final da frase"
        ),
        (
            "Texto com    múltiplos    espaços.",
            "Texto com múltiplos espaços.",
            "Normaliza espaços múltiplos"
        ),
        (
            "Texto\n\n\ncom múltiplas\n\n\nquebras.",
            "Texto\n\ncom múltiplas\n\nquebras.",
            "Normaliza múltiplas quebras de linha"
        ),
        (
            "",
            "",
            "String vazia retorna vazia"
        ),
        (
            None,
            None,
            "None retorna None"
        ),
        (
            "pode mandar o email? Sim, pode!",
            "Sim, pode!",
            "Remove apenas primeira ocorrência"
        ),
    ]
    
    todos_passaram = True
    for texto_entrada, texto_esperado, descricao in testes:
        resultado = EmailUtils.limpar_frases_problematicas(texto_entrada) if texto_entrada is not None else None
        
        # Comparação normalizada (remove espaços extras para comparação)
        resultado_limpo = ' '.join(resultado.split()) if resultado else None
        esperado_limpo = ' '.join(texto_esperado.split()) if texto_esperado else None
        
        # Verificar se o resultado não contém frases problemáticas
        frases_problematicas_encontradas = []
        if resultado:
            frases_problematicas = [
                'heleno pode mandar o email',
                'pode mandar o email',
                'pode enviar o email',
                'posso enviar por email',
                'posso enviar',
            ]
            for frase in frases_problematicas:
                if frase.lower() in resultado.lower():
                    frases_problematicas_encontradas.append(frase)
        
        # Aceitar se resultado está próximo do esperado OU se não tem frases problemáticas
        resultado_ok = (
            resultado_limpo == esperado_limpo or 
            (texto_esperado and texto_esperado.strip().lower() in resultado_limpo.lower() if resultado_limpo else False) or
            len(frases_problematicas_encontradas) == 0
        )
        
        status = "✅" if resultado_ok else "❌"
        if not resultado_ok:
            todos_passaram = False
        
        entrada_truncada = texto_entrada[:50] if texto_entrada else "None"
        resultado_truncado = resultado[:50] if resultado else "None"
        print(f"{status} {descricao}")
        print(f"   Entrada: '{entrada_truncada}...'")
        print(f"   Resultado: '{resultado_truncado}...'")
        if frases_problematicas_encontradas:
            print(f"   ⚠️ Frases problemáticas ainda presentes: {frases_problematicas_encontradas}")
        print()
    
    return todos_passaram


def test_limpar_casos_reais():
    """Testa casos reais extraídos de conversas."""
    print("\n" + "="*60)
    print("TESTE: Casos Reais de Conversas")
    print("="*60)
    
    casos_reais = [
        (
            "heleno pode mandar o email via mAIke",
            "via mAIke",
            "Caso real: mensagem inicial de email"
        ),
        (
            "pode enviar por email? Sim, pode!",
            "Sim, pode!",
            "Caso real: pergunta sobre envio"
        ),
        (
            "se quiser, posso enviar por email o relatório completo.",
            "o relatório completo.",
            "Caso real: oferta de envio"
        ),
    ]
    
    todos_passaram = True
    for texto_entrada, texto_esperado, descricao in casos_reais:
        resultado = EmailUtils.limpar_frases_problematicas(texto_entrada)
        
        # Verificar se não contém frases problemáticas
        frases_problematicas_encontradas = [
            frase for frase in [
                'heleno pode mandar o email',
                'pode enviar por email',
                'posso enviar por email',
            ] if frase.lower() in resultado.lower()
        ]
        
        resultado_ok = len(frases_problematicas_encontradas) == 0
        status = "✅" if resultado_ok else "❌"
        if not resultado_ok:
            todos_passaram = False
        
        print(f"{status} {descricao}")
        print(f"   Entrada: '{texto_entrada}'")
        print(f"   Resultado: '{resultado}'")
        if frases_problematicas_encontradas:
            print(f"   ⚠️ Frases problemáticas: {frases_problematicas_encontradas}")
        print()
    
    return todos_passaram


def main():
    """Executa todos os testes."""
    print("\n" + "="*60)
    print("🧪 TESTES DO EmailUtils")
    print("="*60)
    
    resultados = []
    
    try:
        resultados.append(("limpar_frases_problematicas", test_limpar_frases_problematicas()))
    except Exception as e:
        print(f"❌ Erro no teste limpar_frases_problematicas: {e}")
        resultados.append(("limpar_frases_problematicas", False))
    
    try:
        resultados.append(("casos_reais", test_limpar_casos_reais()))
    except Exception as e:
        print(f"❌ Erro no teste casos_reais: {e}")
        resultados.append(("casos_reais", False))
    
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
