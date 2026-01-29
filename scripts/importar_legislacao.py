#!/usr/bin/env python3
"""
Script interativo para importar legislação (IN, Lei, Decreto, etc.).

Tenta importar por URL primeiro. Se falhar, pede para você colar o texto.
"""
import sys
import logging
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.legislacao_service import LegislacaoService
from db_manager import init_db

# Configurar logging básico
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def importar_legislacao_interativo():
    """Script interativo para importar legislação."""
    
    print("=" * 70)
    print("📚 IMPORTADOR DE LEGISLAÇÃO - mAIke")
    print("=" * 70)
    print()
    
    # Inicializar banco
    print("🔧 Inicializando banco de dados...")
    init_db()
    print("✅ Banco inicializado\n")
    
    # Criar serviço
    service = LegislacaoService()
    
    # Coletar informações básicas
    print("📋 Informações da Legislação")
    print("-" * 70)
    
    tipo_ato = input("Tipo do ato (IN, Lei, Decreto, Portaria, etc.): ").strip()
    if not tipo_ato:
        print("❌ Tipo do ato é obrigatório!")
        return
    
    numero = input("Número do ato (ex: 680, 12345): ").strip()
    if not numero:
        print("❌ Número é obrigatório!")
        return
    
    ano_str = input("Ano do ato (ex: 2006): ").strip()
    try:
        ano = int(ano_str)
    except ValueError:
        print("❌ Ano inválido!")
        return
    
    sigla_orgao = input("Sigla do órgão (ex: RFB, MF, MDIC) [opcional]: ").strip()
    if not sigla_orgao:
        sigla_orgao = None
    
    titulo_oficial = input("Título ou ementa [opcional]: ").strip()
    if not titulo_oficial:
        titulo_oficial = None
    
    print()
    print("=" * 70)
    print("🤖 OPÇÃO 0: Busca Automática com IA (NOVO!)")
    print("=" * 70)
    print()
    print("💡 A IA pode tentar encontrar a URL automaticamente!")
    print("   Você não precisa procurar a URL manualmente.")
    print()
    print("⏳ Tentando buscar URL com IA...")
    print("-" * 70)
    
    # Tentar buscar URL com IA primeiro
    url_encontrada = None
    try:
        url_encontrada = service.buscar_url_com_ia(
            tipo_ato=tipo_ato,
            numero=numero,
            ano=ano,
            sigla_orgao=sigla_orgao or ''
        )
    except Exception as e:
        logger.warning(f"Erro ao buscar URL com IA: {e}")
        url_encontrada = None
    
    if url_encontrada:
        print(f"✅ URL encontrada pela IA: {url_encontrada}")
        print()
        usar_url_ia = input("🤔 Usar esta URL? (S/n): ").strip().lower()
        if usar_url_ia in ['', 's', 'sim', 'y', 'yes']:
            url = url_encontrada
        else:
            url = None
            print("⏭️ URL da IA descartada. Vamos para opção manual...")
            print()
    else:
        print("❌ IA não conseguiu encontrar a URL automaticamente.")
        print("   Não se preocupe! Você pode fornecer a URL manualmente ou copiar/colar.")
        print()
        url = None
    
    # Se não usou URL da IA, oferecer opção manual de URL
    if not url:
        print("=" * 70)
        print("🚀 OPÇÃO 1: Importação por URL Manual")
        print("=" * 70)
        print()
        print("💡 Se você tem a URL, pode colar aqui.")
        print("   Se não tiver, pode pular e ir direto para copiar/colar.")
        print()
        print("📋 EXEMPLO DE URL:")
        print("   https://www.gov.br/receitafederal/pt-br/legislacao/in-rfb-680-2006")
        print("   https://www.in.gov.br/web/dou/-/instrucao-normativa-rfb-n-680...")
        print()
        print("⚠️ IMPORTANTE:")
        print("   - URL pode funcionar se o site permitir acesso direto")
        print("   - Pode NÃO funcionar se exigir login ou tiver proteções")
        print("   - Se não funcionar, você pode copiar/colar depois (sempre funciona!)")
        print()
        print("-" * 70)
        
        # Tentar URL manual
        url = input("📎 Cole a URL aqui (ou deixe vazio para pular e copiar/colar): ").strip()
    
    if url:
        print(f"\n📥 Tentando baixar de: {url}")
        print("⏳ Processando... (pode levar alguns segundos)")
        print("-" * 70)
        print("🔍 Verificando:")
        print("   1. Conectando ao site...")
        
        try:
            resultado = service.importar_ato_por_url(
                tipo_ato=tipo_ato,
                numero=numero,
                ano=ano,
                sigla_orgao=sigla_orgao or '',
                url=url,
                titulo_oficial=titulo_oficial
            )
            
            # Verificar resultado
            if resultado.get('sucesso'):
                print("   2. ✅ Texto extraído com sucesso")
                print("   3. ✅ Artigos e parágrafos identificados")
                print("   4. ✅ Dados salvos no banco")
                print()
                print("=" * 70)
                print("✅✅✅ SUCESSO! Importação automática funcionou!")
                print("=" * 70)
                print(f"   📊 ID do ato: {resultado.get('legislacao_id')}")
                print(f"   📄 Trechos importados: {resultado.get('trechos_importados')}")
                print()
                print("🎉 Pronto! A legislação foi importada com sucesso.")
                print()
                print("💡 Agora você pode consultar:")
                print(f"   from services.legislacao_service import LegislacaoService")
                print(f"   service = LegislacaoService()")
                print(f"   trechos = service.buscar_trechos_por_palavra_chave(")
                print(f"       '{tipo_ato}', '{numero}', termos=['canal'])")
                return
            else:
                # Falhou - mostrar erro e ir para opção manual
                erro = resultado.get('erro', 'Erro desconhecido')
                print("   ❌ Erro durante o processo")
                print()
                print("=" * 70)
                print("❌ Importação automática NÃO funcionou")
                print("=" * 70)
                print(f"   ⚠️ Motivo: {erro}")
                print()
                print("💡 Isso é normal! Alguns sites têm:")
                print("   - Proteções anti-bot")
                print("   - Estrutura HTML/PDF complexa")
                print("   - Exigência de login")
                print()
                print("✅ Não se preocupe! Vamos usar a opção manual (copiar/colar)")
                print("   que sempre funciona!")
                print()
        except Exception as e:
            print("   ❌ Erro ao conectar")
            print()
            print("=" * 70)
            print(f"❌ Erro ao tentar baixar da URL")
            print("=" * 70)
            print(f"   ⚠️ Detalhes: {str(e)}")
            print()
            print("✅ Vamos usar a opção manual (copiar/colar) que sempre funciona!")
            print()
    else:
        print("⏭️ URL não fornecida. Vamos para importação manual (copiar/colar)...")
        print("   Isso sempre funciona! ✅")
        print()
    
    # Importação manual (copiar/colar)
    print("=" * 70)
    print("✋ OPÇÃO 2: Importação Manual (Copiar e Colar)")
    print("=" * 70)
    print()
    print("✅ Esta opção SEMPRE funciona! (Recomendada se URL não funcionar)")
    print()
    print("💡 VANTAGEM: Você NÃO precisa ter a URL exata!")
    print("   Só precisa abrir o site e copiar o texto.")
    print()
    print("📋 Passo a passo:")
    print()
    print("   1. Abra o site oficial da legislação no seu navegador")
    print("      (Exemplo: https://www.gov.br/receitafederal/... ou DOU)")
    print("      Você NÃO precisa copiar a URL, só abrir o site!")
    print()
    print("   2. Selecione TODO o texto da legislação (Ctrl+A / Cmd+A)")
    print()
    print("   3. Copie o texto (Ctrl+C / Cmd+C)")
    print()
    print("   4. Volte aqui e cole o texto (Ctrl+V / Cmd+V)")
    print()
    print("   5. Depois de colar, pressione Enter duas vezes para finalizar")
    print()
    print("💡 DICA: Não precisa formatar perfeitamente. O sistema")
    print("   identifica artigos automaticamente mesmo com formatação imperfeita.")
    print()
    print("   1. Abra o site oficial da legislação no seu navegador")
    print("      Exemplo: https://www.gov.br/receitafederal/...")
    print()
    print("   2. Selecione TODO o texto da legislação:")
    print("      - Windows/Linux: Pressione Ctrl+A")
    print("      - Mac: Pressione Cmd+A")
    print()
    print("   3. Copie o texto selecionado:")
    print("      - Windows/Linux: Pressione Ctrl+C")
    print("      - Mac: Pressione Cmd+C")
    print()
    print("   4. Volte aqui e cole o texto (Ctrl+V / Cmd+V)")
    print()
    print("   5. Depois de colar, pressione Enter duas vezes para finalizar")
    print()
    print("💡 DICA: Não precisa formatar perfeitamente. O sistema")
    print("   identifica artigos automaticamente mesmo com formatação imperfeita.")
    print()
    print("-" * 70)
    print("📋 Cole o texto da legislação aqui (Ctrl+V / Cmd+V):")
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
    print("🔍 Verificando:")
    print("   1. Analisando texto...", flush=True)
    
    try:
        # Mostrar progresso
        import sys
        sys.stdout.flush()
        
        resultado = service.importar_ato_de_texto(
            tipo_ato=tipo_ato,
            numero=numero,
            ano=ano,
            sigla_orgao=sigla_orgao or '',
            texto_bruto=texto_bruto,
            titulo_oficial=titulo_oficial
        )
        
        sys.stdout.flush()
        
        if resultado.get('sucesso'):
            print("   2. ✅ Artigos e parágrafos identificados", flush=True)
            print("   3. ✅ Dados salvos no banco", flush=True)
            print()
            print("=" * 70)
            print("✅✅✅ SUCESSO! Importação concluída!")
            print("=" * 70)
            print(f"   📊 ID do ato: {resultado.get('legislacao_id')}")
            print(f"   📄 Trechos importados: {resultado.get('trechos_importados')}")
            print()
            print("🎉 Pronto! A legislação foi importada com sucesso.")
            print()
            print("💡 Agora você pode consultar:")
            print(f"   from services.legislacao_service import LegislacaoService")
            print(f"   service = LegislacaoService()")
            print(f"   trechos = service.buscar_trechos_por_palavra_chave(")
            print(f"       '{tipo_ato}', '{numero}', termos=['canal'])")
            print()
            print("=" * 70)
            print("✅ Importação finalizada com sucesso!")
            print("=" * 70)
        else:
            erro = resultado.get('erro', 'Erro desconhecido')
            print("   2. ❌ Erro ao processar", flush=True)
            print()
            print("=" * 70)
            print("❌ Erro na importação")
            print("=" * 70)
            print(f"   ⚠️ Motivo: {erro}")
            print()
            print("💡 Dicas para resolver:")
            print("   - Verifique se o texto foi colado corretamente")
            print("   - Certifique-se de que há artigos no formato 'Art. Xº'")
            print("   - Tente novamente com o texto completo")
            print("   - O texto pode ter formatação estranha - tente limpar antes de colar")
            print()
            print("=" * 70)
            print("❌ Importação não foi concluída")
            print("=" * 70)
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
        print()
        print("💡 Tente novamente ou verifique se os dados foram salvos:")
        print(f"   python3 scripts/verificar_legislacao.py {tipo_ato} {numero} {ano} {sigla_orgao or ''}")
        print()
        print("=" * 70)

if __name__ == '__main__':
    try:
        importar_legislacao_interativo()
    except KeyboardInterrupt:
        print("\n\n⚠️ Importação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()

