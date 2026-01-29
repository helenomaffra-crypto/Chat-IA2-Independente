# 🧪 Como Testar a Página 1 do Extrato DI

**Data:** 26/01/2026  
**Objetivo:** Verificar se os ajustes na página 1 estão funcionando corretamente

---

## ✅ Opção 1: Testar pelo Chat (Mais Simples)

1. **Abra o chat** no sistema
2. **Digite:**
   ```
   extrato di BND.0101/25
   ```
   (ou qualquer processo/DI que você tenha)

3. **O sistema vai:**
   - Buscar a DI
   - Gerar o PDF
   - Disponibilizar para download

4. **Abra o PDF gerado** e verifique se a página 1 está igual ao PDF oficial:
   - ✅ Numeração no topo: `Declaração: 26/0153278-4 Data do Registro: 26/01/2026 1`
   - ✅ CNPJ e Nome na mesma linha (Importador, Adquirente, Representante)
   - ✅ Embalagem e Quantidade na mesma linha
   - ✅ Peso Bruto e Peso Líquido na mesma linha
   - ✅ Tabela de Valores com cabeçalho `Moeda | Valor`
   - ✅ Valores formatados: `9.600,00` (ponto para milhar, vírgula para decimal)
   - ✅ Numeração no rodapé: `-- 1 of 5 --`

---

## ✅ Opção 2: Testar com Script (Mais Rápido)

### **Passo 1: Executar o script**

```bash
# Testar com processo
python3 teste_extrato_di_pagina1.py BND.0101/25

# Ou testar com DI direta
python3 teste_extrato_di_pagina1.py 26/0153278-4
```

### **Passo 2: Verificar o PDF gerado**

O script vai gerar o PDF em `downloads/Extrato-DI-XXXXX.pdf`

Abra o PDF e compare com o PDF oficial (`BND-0101-25-DI.pdf`).

---

## 📋 Checklist de Verificação

### **1. Numeração no Topo**
- [ ] Aparece: `Declaração: 26/0153278-4 Data do Registro: 26/01/2026 1`
- [ ] Alinhado à direita
- [ ] Fonte pequena (8pt)

### **2. CNPJ e Nome na Mesma Linha**
- [ ] Importador: `CNPJ: 22.849.492/0002-08 MASSY DO BRASIL...`
- [ ] Adquirente: `CNPJ: 08.641.586/0002-66 BANDMAR...`
- [ ] Representante Legal: `CPF: 079.697.977-41 MARCIO...`

### **3. Embalagem e Quantidade**
- [ ] `Embalagem: PACOTE Quantidade: 72` (na mesma linha)

### **4. Peso Bruto e Peso Líquido**
- [ ] `Peso Bruto: 224.720,00000 Kg Peso Líquido: 216.080,00000 Kg` (na mesma linha)

### **5. Tabela de Valores**
- [ ] Cabeçalho: `Moeda | Valor`
- [ ] Formato: `Frete: DOLAR DOS EUA | 9.600,00`
- [ ] Valores com ponto para milhar e vírgula para decimal

### **6. Numeração no Rodapé**
- [ ] `-- 1 of 5 --` (centralizado)
- [ ] Quebra de página após

---

## 🔧 Se Algo Estiver Errado

### **Problema: Valores não aparecem**
- Verificar se os dados da DI têm `frete`, `seguro`, `valorMercadoriaEmbarque`, `valorMercadoriaDescarga`
- Verificar logs do script

### **Problema: Formatação errada**
- Verificar se os filtros `format_currency_usd` e `get_moeda_nome` estão funcionando
- Testar: `python3 -c "from app import app; print(app.jinja_env.filters.get('format_currency_usd')(9600.00))"`

### **Problema: Numeração não aparece**
- Verificar se `dataHoraRegistro` está nos dados da DI
- Verificar se o template está renderizando corretamente

---

## 📝 Exemplo de Comando Completo

```bash
# 1. Testar geração
python3 teste_extrato_di_pagina1.py BND.0101/25

# 2. Abrir PDF gerado
open downloads/Extrato-DI-*.pdf

# 3. Comparar com PDF oficial
open /Users/helenomaffra/Downloads/BND-0101-25-DI.pdf
```

---

**Status:** ✅ Script de teste criado
