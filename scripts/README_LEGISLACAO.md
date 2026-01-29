# 📚 Scripts de Legislação

## Script Interativo de Importação

### Como Usar

```bash
python scripts/importar_legislacao.py
```

### O que o Script Faz

1. **Pede informações básicas:**
   - Tipo do ato (IN, Lei, Decreto, etc.)
   - Número do ato
   - Ano
   - Sigla do órgão (opcional)
   - Título (opcional)

2. **Tenta importação automática:**
   - Pede a URL da legislação
   - Tenta baixar e importar automaticamente
   - Se funcionar: pronto! ✅

3. **Se falhar, pede para colar:**
   - Instruções claras de como copiar
   - Você cola o texto
   - Sistema importa

### Exemplo de Uso

```bash
$ python scripts/importar_legislacao.py

======================================================================
📚 IMPORTADOR DE LEGISLAÇÃO - mAIke
======================================================================

🔧 Inicializando banco de dados...
✅ Banco inicializado

📋 Informações da Legislação
----------------------------------------------------------------------
Tipo do ato (IN, Lei, Decreto, Portaria, etc.): IN
Número do ato (ex: 680, 12345): 680
Ano do ato (ex: 2006): 2006
Sigla do órgão (ex: RFB, MF, MDIC) [opcional]: RFB
Título ou ementa [opcional]: IN RFB 680/06

======================================================================
🚀 Tentando importação automática por URL...
======================================================================

URL da legislação (deixe vazio para pular): https://...

[Se funcionar: ✅ Importação concluída!]
[Se falhar: ⚠️ Vamos para importação manual...]

======================================================================
✋ IMPORTAÇÃO MANUAL - Copiar e Colar
======================================================================

📝 Instruções:
   1. Abra o site oficial da legislação no navegador
   2. Selecione todo o texto (Ctrl+A / Cmd+A)
   3. Copie o texto (Ctrl+C / Cmd+C)
   4. Cole aqui abaixo (Ctrl+V / Cmd+V)
   5. Pressione Enter duas vezes para finalizar

Cole o texto da legislação aqui:
----------------------------------------------------------------------
[Você cola o texto aqui]

✅ Importação concluída!
```

### Vantagens

- ✅ **Interativo**: Guia você passo a passo
- ✅ **Inteligente**: Tenta URL primeiro, se falhar pede para colar
- ✅ **Simples**: Não precisa escrever código Python
- ✅ **Claro**: Instruções em cada passo




