#!/usr/bin/env python3
"""
Script para importar o Decreto 6.759/2009 (Regulamento Aduaneiro) no SQLite.

Este script tenta baixar automaticamente da URL do Planalto.
Se não conseguir, você pode copiar/colar o texto manualmente.
"""
import sys
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.legislacao_service import LegislacaoService
from db_manager import init_db

def importar_decreto_6759():
    """Importa o Decreto 6.759/2009."""
    
    print("=" * 70)
    print("📚 IMPORTANDO DECRETO 6.759/2009 - REGULAMENTO ADUANEIRO")
    print("=" * 70)
    print()
    
    # Inicializar banco
    print("🔧 Inicializando banco de dados...")
    init_db()
    print("✅ Banco inicializado")
    print()
    
    # Criar serviço
    service = LegislacaoService()
    
    # Dados do decreto
    url = "https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2009/decreto/d6759.htm"
    tipo_ato = "Decreto"
    numero = "6759"
    ano = 2009
    sigla_orgao = "PR"  # Presidência da República
    titulo_oficial = "Decreto 6.759/2009 - Regulamento Aduaneiro"
    
    print("📋 Dados do Decreto:")
    print(f"   Tipo: {tipo_ato}")
    print(f"   Número: {numero}")
    print(f"   Ano: {ano}")
    print(f"   Órgão: {sigla_orgao}")
    print(f"   URL: {url}")
    print()
    
    # Tentar importar por URL
    print("=" * 70)
    print("🚀 Tentando importar por URL...")
    print("=" * 70)
    print()
    
    resultado = service.importar_ato_por_url(
        tipo_ato=tipo_ato,
        numero=numero,
        ano=ano,
        sigla_orgao=sigla_orgao,
        url=url,
        titulo_oficial=titulo_oficial
    )
    
    if resultado.get('sucesso'):
        print("=" * 70)
        print("✅✅✅ SUCESSO! Decreto importado com sucesso!")
        print("=" * 70)
        print(f"   📊 ID do ato: {resultado.get('legislacao_id')}")
        print(f"   📄 Trechos importados: {resultado.get('trechos_importados')}")
        print()
        print("🎉 O Regulamento Aduaneiro foi importado e está disponível para consulta!")
        print()
        print("💡 Agora você pode consultar no chat:")
        print("   - 'o que diz o Decreto 6759?'")
        print("   - 'o que o Decreto 6759 fala sobre despacho aduaneiro?'")
        print("   - 'busque no Decreto 6759 trechos sobre importação'")
    else:
        erro = resultado.get('erro', 'Erro desconhecido')
        print("=" * 70)
        print("❌ Erro ao importar por URL")
        print("=" * 70)
        print(f"   ⚠️ Motivo: {erro}")
        print()
        print("💡 Isso é normal! Vamos importar manualmente (copiar/colar).")
        print()
        print("=" * 70)
        print("✋ IMPORTAÇÃO MANUAL - COPIE E COLE O TEXTO")
        print("=" * 70)
        print()
        print("📋 Passo a passo:")
        print()
        print("   1. Abra esta URL no seu navegador:")
        print(f"      {url}")
        print()
        print("   2. Selecione TODO o texto da página (Ctrl+A / Cmd+A)")
        print()
        print("   3. Copie o texto (Ctrl+C / Cmd+C)")
        print()
        print("   4. Volte aqui e cole o texto abaixo")
        print()
        print("   5. Depois de colar, pressione Enter duas vezes para finalizar")
        print()
        print("💡 DICA: Não precisa formatar perfeitamente.")
        print("   O sistema identifica artigos automaticamente.")
        print()
        print("-" * 70)
        print("📋 Cole o texto do Decreto 6.759/2009 aqui:")
        print("-" * 70)
        
        # Ler texto colado (múltiplas linhas até linha vazia dupla)
        linhas = []
        linhas_vazias_consecutivas = 0
        
        try:
            while True:
                linha = input()
                if not linha.strip():
                    linhas_vazias_consecutivas += 1
                    if linhas_vazias_consecutivas >= 2:
                        break
                else:
                    linhas_vazias_consecutivas = 0
                linhas.append(linha)
        except EOFError:
            pass
        
        texto_bruto = '\n'.join(linhas).strip()
        
        if not texto_bruto:
            print("\n❌ Nenhum texto foi colado. Importação cancelada.")
            return
        
        print()
        print("=" * 70)
        print("📥 Processando texto colado...")
        print("=" * 70)
        print("⏳ Isso pode levar alguns segundos...")
        print()
        
        try:
            resultado = service.importar_ato_de_texto(
                tipo_ato=tipo_ato,
                numero=numero,
                ano=ano,
                sigla_orgao=sigla_orgao,
                texto_bruto=texto_bruto,
                titulo_oficial=titulo_oficial
            )
            
            if resultado.get('sucesso'):
                print("=" * 70)
                print("✅✅✅ SUCESSO! Decreto importado com sucesso!")
                print("=" * 70)
                print(f"   📊 ID do ato: {resultado.get('legislacao_id')}")
                print(f"   📄 Trechos importados: {resultado.get('trechos_importados')}")
                print()
                print("🎉 O Regulamento Aduaneiro foi importado e está disponível para consulta!")
                print()
                print("💡 Agora você pode consultar no chat:")
                print("   - 'o que diz o Decreto 6759?'")
                print("   - 'o que o Decreto 6759 fala sobre despacho aduaneiro?'")
                print("   - 'busque no Decreto 6759 trechos sobre importação'")
            else:
                erro = resultado.get('erro', 'Erro desconhecido')
                print("=" * 70)
                print("❌ Erro ao importar texto")
                print("=" * 70)
                print(f"   ⚠️ Motivo: {erro}")
                print()
                print("💡 Dicas para resolver:")
                print("   - Verifique se o texto foi colado corretamente")
                print("   - Certifique-se de que há artigos no formato 'Art. Xº'")
                print("   - Tente novamente com o texto completo")
                
        except Exception as e:
            print()
            print("=" * 70)
            print("❌ ERRO INESPERADO durante o processamento")
            print("=" * 70)
            print(f"   ⚠️ Erro: {str(e)}")
            print()
            import traceback
            print("📋 Detalhes técnicos:")
            traceback.print_exc()

if __name__ == '__main__':
    try:
        importar_decreto_6759()
    except KeyboardInterrupt:
        print("\n\n⚠️ Importação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()

