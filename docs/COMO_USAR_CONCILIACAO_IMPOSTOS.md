# 📖 Como Usar a Conciliação de Impostos de Importação

**Data:** 08/01/2026  
**Objetivo:** Explicar passo a passo como usar a funcionalidade de conciliação de impostos de importação

---

## 🎯 O Que Fazer Quando Aparece "Importação siscomex"

Quando você vê um lançamento bancário com a descrição **"Importação siscomex"** na tela de **Conciliar/Classificar Lançamentos**, siga estes passos:

### Passo 1: Clique no Lançamento

Clique no lançamento que contém "Importação siscomex" para abrir o modal de classificação.

### Passo 2: Verifique o Aviso

Se o sistema detectar que pode ser imposto de importação, você verá um aviso amarelo:

```
⚠️ Este lançamento pode ser de impostos de importação

Se este lançamento contém impostos de importação (II, IPI, PIS, COFINS), 
você pode distribuir o valor entre os tipos de imposto.

[ ] Confirmar que são impostos de importação
```

### Passo 3: Marque a Confirmação

**Se este lançamento É de impostos de importação:**
1. Marque o checkbox **"Confirmar que são impostos de importação"**
2. Uma interface especial aparecerá abaixo

**Se este lançamento NÃO É de impostos de importação:**
- Deixe o checkbox desmarcado
- Continue normalmente com a classificação de despesas

### Passo 4: Distribuir os Impostos (Se Confirmou)

Quando você marca o checkbox, aparece uma interface verde com campos para distribuir o valor:

```
💰 Distribuir Impostos de Importação

Distribua o valor total entre os tipos de imposto. 
Os valores sugeridos vêm da DI do processo.

II (Imposto de Importação):     [R$ 10.000,00] BRL
IPI:                             [R$ 5.000,00] BRL
PIS:                             [R$ 3.000,00] BRL
COFINS:                          [R$ 5.094,63] BRL
Taxa SISCOMEX:                   [R$ 0,00] BRL
Antidumping:                     [R$ 0,00] BRL

Total distribuído: R$ 23.094,63 / R$ 23.094,63
✅ Total distribuído corretamente!
```

**O que fazer:**
1. Os valores sugeridos vêm automaticamente da DI do processo (se houver processo vinculado)
2. Ajuste os valores manualmente se necessário
3. Certifique-se de que a soma dos impostos = valor total do lançamento
4. O sistema mostra se está correto (✅) ou se falta/excede valor (⚠️/❌)

### Passo 5: Classificar a Despesa

Ainda é necessário classificar o lançamento como uma despesa:

1. Selecione o **Tipo de Despesa** (ex: "Impostos de Importação")
2. Informe o **Processo** (ex: BGR.0070/25)
3. O **Valor** pode ficar vazio (será o valor total automaticamente)

### Passo 6: Salvar

Clique em **"💾 Salvar Classificações"**.

**O que acontece:**
- ✅ A despesa é gravada em `LANCAMENTO_TIPO_DESPESA`
- ✅ Os impostos individuais são gravados em `IMPOSTO_IMPORTACAO`
- ✅ Cada imposto fica vinculado ao processo

---

## 🔍 Exemplos Práticos

### Exemplo 1: Lançamento "Importação siscomex" com Processo

**Lançamento:**
- Valor: R$ 23.094,63
- Descrição: "Importação siscomex"
- Processo: BGR.0070/25

**Passos:**
1. ✅ Sistema detecta: "Pode ser imposto de importação"
2. ✅ Você marca: "Confirmar que são impostos de importação"
3. ✅ Sistema busca valores da DI do BGR.0070/25 e preenche automaticamente
4. ✅ Você ajusta se necessário
5. ✅ Seleciona tipo de despesa: "Impostos de Importação"
6. ✅ Informa processo: BGR.0070/25
7. ✅ Salva

**Resultado:**
- 1 registro em `LANCAMENTO_TIPO_DESPESA` (despesa geral)
- 4 registros em `IMPOSTO_IMPORTACAO` (II, IPI, PIS, COFINS)

### Exemplo 2: Lançamento "Impostos" (Genérico)

**Lançamento:**
- Valor: R$ 3.350,01
- Descrição: "Impostos"
- Processo: (nenhum)

**Passos:**
1. ❌ Sistema NÃO detecta como imposto de importação (é genérico)
2. ✅ Você classifica normalmente como despesa (ex: "ICMS", "ISS", etc.)
3. ✅ Salva

**Resultado:**
- 1 registro em `LANCAMENTO_TIPO_DESPESA` (despesa geral)
- Nenhum registro em `IMPOSTO_IMPORTACAO` (não é imposto de importação)

### Exemplo 3: Lançamento "Impostos" com Processo Vinculado

**Lançamento:**
- Valor: R$ 15.000,00
- Descrição: "Impostos"
- Processo: DMD.0083/25 (já vinculado)

**Passos:**
1. ✅ Sistema detecta: "Pode ser imposto de importação" (porque tem processo)
2. ✅ Você marca: "Confirmar que são impostos de importação"
3. ✅ Sistema busca valores da DI do DMD.0083/25
4. ✅ Você distribui e salva

**Resultado:**
- 1 registro em `LANCAMENTO_TIPO_DESPESA`
- Vários registros em `IMPOSTO_IMPORTACAO`

---

## ⚠️ Importante

1. **Nem todo "Impostos" é de importação**: Pode ser ICMS, ISS, IRPF, etc.
2. **Sempre confirme**: Só marque o checkbox se tiver CERTEZA que são impostos de importação
3. **Valores devem bater**: A soma dos impostos deve igualar o valor total do lançamento
4. **Processo é importante**: Se houver processo vinculado, os valores sugeridos vêm da DI automaticamente

---

## 🆘 Dúvidas Frequentes

**P: O que fazer se não aparecer o aviso de impostos?**
R: Significa que o sistema não detectou como possível imposto de importação. Classifique normalmente como despesa.

**P: Posso distribuir impostos sem processo vinculado?**
R: Sim, mas você terá que preencher os valores manualmente (não terá valores sugeridos da DI).

**P: O que acontece se a soma dos impostos não bater com o valor total?**
R: O sistema mostra um aviso (⚠️ ou ❌), mas ainda permite salvar. Ajuste os valores até bater.

**P: Posso usar a distribuição de impostos E o split de despesas?**
R: Sim! Você pode distribuir os impostos E também fazer split do lançamento em múltiplas despesas.

---

**Última atualização:** 08/01/2026


