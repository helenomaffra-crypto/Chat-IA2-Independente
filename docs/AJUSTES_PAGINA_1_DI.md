# 📄 Ajustes na Página 1 do Extrato DI

**Data:** 26/01/2026  
**Objetivo:** Ajustar template da página 1 para ficar exatamente igual ao PDF oficial da Receita Federal

---

## ✅ Ajustes Aplicados

### **1. Numeração no Topo**
**PDF Oficial:**
```
Declaração: 26/0153278-4 Data do Registro: 26/01/2026 1
```

**Implementado:**
- Adicionado no topo do template
- Formata data de registro (ISO → DD/MM/YYYY)
- Mostra número da DI e data

---

### **2. CNPJ e Nome na Mesma Linha**

**PDF Oficial:**
```
CNPJ: 22.849.492/0002-08 MASSY DO BRASIL COMERCIO EXTERIOR LTDA
```

**Ajustado:**
- ✅ Importador: CNPJ + Nome na mesma linha
- ✅ Adquirente: CNPJ + Nome na mesma linha
- ✅ Representante Legal: CPF + Nome na mesma linha

---

### **3. Embalagem e Quantidade na Mesma Linha**

**PDF Oficial:**
```
Embalagem: PACOTE Quantidade: 72
```

**Ajustado:**
- ✅ Embalagem e Quantidade na mesma linha
- ✅ Soma quantidade de todas as embalagens

---

### **4. Peso Bruto e Peso Líquido na Mesma Linha**

**PDF Oficial:**
```
Peso Bruto: 224.720,00000 Kg Peso Líquido: 216.080,00000 Kg
```

**Ajustado:**
- ✅ Peso Bruto e Peso Líquido na mesma linha
- ✅ Formatação com 5 casas decimais

---

### **5. Tabela de Valores com Cabeçalho "Moeda Valor"**

**PDF Oficial:**
```
Valores
Moeda Valor
Frete: DOLAR DOS EUA 9.600,00
Seguro: DOLAR DOS EUA 187,83
VMLE: DOLAR DOS ESTADOS UNIDOS 146.923,52
VMLD: DOLAR DOS ESTADOS UNIDOS 156.711,35
```

**Ajustado:**
- ✅ Cabeçalho "Moeda | Valor"
- ✅ Formato: "Frete: DOLAR DOS EUA" na primeira coluna
- ✅ Valor formatado (ponto para milhar, vírgula para decimal) na segunda coluna
- ✅ Novo filtro `format_currency_usd` para valores em dólar
- ✅ Novo filtro `get_moeda_nome` para nome da moeda

---

### **6. Numeração no Rodapé**

**PDF Oficial:**
```
-- 1 of 5 --
```

**Ajustado:**
- ✅ Adicionado no rodapé da página 1
- ✅ `page-break-after: always` para forçar quebra de página

---

## 🔧 Novos Filtros Criados

### **`format_currency_usd`**
Formata valores em dólar com ponto para milhar e vírgula para decimal:
- `9600.00` → `9.600,00`
- `146923.52` → `146.923,52`

### **`get_moeda_nome`**
Retorna nome da moeda baseado no código:
- `220` → `DOLAR DOS EUA` / `DOLAR DOS ESTADOS UNIDOS`
- `978` → `EURO`
- `986` → `REAL`

---

## 📋 Estrutura da Página 1 (Ajustada)

```
Declaração: 26/0153278-4 Data do Registro: 26/01/2026 1

SECRETARIA DA RECEITA FEDERAL DO BRASIL - RFB
PORTO DO RIO DE JANEIRO
EXTRATO DA DECLARAÇÃO DE IMPORTAÇÃO
CONSUMO

Modalidade do Despacho: NORMAL
Quantidade de Adições: 1

Importador
CNPJ: 22.849.492/0002-08 MASSY DO BRASIL COMERCIO EXTERIOR LTDA

Adquirente da Mercadoria
CNPJ: 08.641.586/0002-66 BANDMAR IMPORTACAO E EXPORTACAO LTDA

Representante Legal
CPF: 079.697.977-41 MARCIO FERREIRA BERIZ MATOS

Carga
Tipo do Manifesto: MANIFESTO DE CARGA
Número do Manifesto: 1326500057328
Recinto Aduaneiro: INST.PORT.MAR.ALF.USO PUBL.CONS.MULT RIO-T.II-PORTO RJ
Armazém: MULTIRIO
Embalagem: PACOTE Quantidade: 72
Peso Bruto: 224.720,00000 Kg Peso Líquido: 216.080,00000 Kg

Valores
Moeda | Valor
Frete: DOLAR DOS EUA | 9.600,00
Seguro: DOLAR DOS EUA | 187,83
VMLE: DOLAR DOS ESTADOS UNIDOS | 146.923,52
VMLD: DOLAR DOS ESTADOS UNIDOS | 156.711,35

Tributos
Suspenso | Recolhido
I.I.: 0,00 | 59.664,52
I.P.I.: 0,00 | 0,00
Pis/Pasep: 0,00 | 17.402,15
Cofins: 0,00 | 79.967,04
Direitos Antidumping: 0,00 | 0,00

Data da Emissão: __/__/____ ________________________________________
Assinatura do Representante

-- 1 of 5 --
```

---

## ⚠️ Observações

1. **Moeda:** Por padrão assume USD (código 220) se não encontrar código de moeda nos dados
2. **Formatação de valores:** Valores em dólar usam ponto para milhar e vírgula para decimal
3. **Numeração:** Página 1 sempre mostra "1", total de páginas pode ser calculado dinamicamente se necessário

---

## 🚀 Próximos Passos (Opcional)

1. **Calcular total de páginas dinamicamente** (se necessário)
2. **Adicionar logo/brasão da Receita Federal** (se disponível)
3. **Ajustar espaçamentos** para ficar mais próximo do original
4. **Testar com WeasyPrint** (melhor renderização que xhtml2pdf)

---

**Status:** ✅ Ajustes aplicados na página 1
