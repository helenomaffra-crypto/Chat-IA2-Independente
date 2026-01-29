# 🏛️ Adicionar Logo da Receita Federal no Extrato DI

**Data:** 26/01/2026  
**Objetivo:** Adicionar logo oficial da Receita Federal no cabeçalho do extrato DI

---

## ✅ Implementação

### **1. Logo Copiado para `static/`**
- ✅ Logo salvo em: `static/logo-receita-federal.png`
- ✅ Convertido para base64 no momento da renderização

### **2. Modificações no `DiPdfService`**
- ✅ Carrega logo em base64 antes de renderizar template
- ✅ Passa `logo_receita_federal` como variável para o template
- ✅ Tratamento de erro se logo não existir (não quebra o PDF)

### **3. Modificações no Template `extrato_di.html`**
- ✅ Adicionado CSS para `.header-logo`:
  - `max-width: 120px`
  - `max-height: 60px`
  - Centralizado
- ✅ Logo inserido no cabeçalho (antes do título)
- ✅ Usa base64 inline (`data:image/png;base64,...`) para compatibilidade com xhtml2pdf

---

## 📋 Estrutura do Cabeçalho (Atualizada)

```
Declaração: 26/0153278-4 Data do Registro: 26/01/2026 1

[LOGO RECEITA FEDERAL] ← NOVO
SECRETARIA DA RECEITA FEDERAL DO BRASIL - RFB
PORTO DO RIO DE JANEIRO
EXTRATO DA DECLARAÇÃO DE IMPORTAÇÃO
CONSUMO
```

---

## 🔧 Como Funciona

1. **Carregamento do Logo:**
   ```python
   logo_path = Path(__file__).parent.parent / 'static' / 'logo-receita-federal.png'
   if logo_path.exists():
       with open(logo_path, 'rb') as f:
           logo_data = base64.b64encode(f.read()).decode('utf-8')
           logo_base64 = f'data:image/png;base64,{logo_data}'
   ```

2. **Renderização no Template:**
   ```html
   {% if logo_receita_federal %}
   <img src="{{ logo_receita_federal }}" alt="Receita Federal" class="header-logo" />
   {% endif %}
   ```

3. **CSS:**
   ```css
   .header-logo {
     max-width: 120px;
     max-height: 60px;
     margin-bottom: 8px;
     display: block;
     margin-left: auto;
     margin-right: auto;
   }
   ```

---

## ⚠️ Observações

1. **Base64 Inline:** Usa base64 inline para garantir que funcione com xhtml2pdf (não precisa de arquivo externo)
2. **Fallback:** Se logo não existir, o PDF ainda é gerado (sem logo)
3. **Tamanho:** Logo limitado a 120px de largura e 60px de altura para não ocupar muito espaço

---

## 🚀 Próximos Passos (Opcional)

1. **Ajustar tamanho do logo** se necessário (atualmente 120x60px)
2. **Testar com WeasyPrint** (melhor renderização de imagens que xhtml2pdf)
3. **Adicionar logo em outras páginas** se necessário

---

## 🧪 Como Testar

```bash
# Testar geração de PDF com logo
python3 teste_extrato_di_pagina1.py BND.0101/25

# Verificar se logo aparece no PDF gerado
open downloads/Extrato-DI-*.pdf
```

---

**Status:** ✅ Logo adicionado no cabeçalho
