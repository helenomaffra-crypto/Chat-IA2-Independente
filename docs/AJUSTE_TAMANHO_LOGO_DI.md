# 📏 Ajuste do Tamanho do Logo da Receita Federal

**Data:** 26/01/2026  
**Problema:** Logo estava aparecendo gigante no PDF gerado  
**Solução:** Extrair tamanho real do PDF original e ajustar CSS

---

## 🔍 Análise do PDF Original

**PDF analisado:** `BND-0101-25-DI.pdf`

### **Tamanho Real do Logo no PDF:**
- **Pontos:** 63.00 x 50.00 pt
- **Centímetros:** 2.22 x 1.76 cm
- **Pixels (72 DPI):** 63 x 50 px
- **Pixels (96 DPI):** 84 x 67 px
- **Pixels (300 DPI):** 262 x 208 px

### **Posição no PDF:**
- **x0:** 30.00 pontos (margem esquerda)
- **y0:** 762.00 pontos (do topo)

---

## ✅ Correção Aplicada

### **Antes (Tamanho Errado):**
```css
.header-logo {
  max-width: 120px;
  max-height: 60px;
  /* ❌ Muito pequeno e não mantinha proporção */
}
```

### **Depois (Tamanho Correto):**
```css
.header-logo {
  width: 63pt;   /* ✅ Tamanho real do PDF original */
  height: 50pt;  /* ✅ Tamanho real do PDF original */
  margin-bottom: 8px;
  display: block;
  margin-left: auto;
  margin-right: auto;
}
```

---

## 📋 Por Que Usar `pt` (Pontos)?

1. **Unidade Nativa de PDF:** PDFs usam pontos como unidade base (1 ponto = 1/72 polegada)
2. **Compatibilidade:** xhtml2pdf e WeasyPrint entendem `pt` corretamente
3. **Precisão:** Garante que o logo tenha exatamente o mesmo tamanho do PDF original

---

## 🧪 Como Verificar

1. **Gerar PDF:**
   ```bash
   python3 teste_extrato_di_pagina1.py BND.0101/25
   ```

2. **Comparar tamanhos:**
   - Abrir PDF gerado
   - Abrir PDF original (`BND-0101-25-DI.pdf`)
   - Comparar tamanho do logo (deve ser idêntico)

---

## 📐 Conversão de Unidades

| Unidade | Valor | Uso |
|---------|-------|-----|
| **pt (pontos)** | 63 x 50 | ✅ **Recomendado para PDF** |
| **cm** | 2.22 x 1.76 | Alternativa |
| **px (72 DPI)** | 63 x 50 | Equivalente a pt |
| **px (96 DPI)** | 84 x 67 | Tela padrão |
| **px (300 DPI)** | 262 x 208 | Alta resolução |

---

## ⚠️ Observações

1. **Proporção:** Logo mantém proporção original (63:50 ≈ 1.26:1)
2. **Centralização:** Logo continua centralizado no cabeçalho
3. **Compatibilidade:** Funciona com xhtml2pdf e WeasyPrint

---

**Status:** ✅ Tamanho do logo ajustado para tamanho real do PDF original
