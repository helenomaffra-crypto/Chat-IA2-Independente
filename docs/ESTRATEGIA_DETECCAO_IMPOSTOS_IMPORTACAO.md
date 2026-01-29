# 🎯 Estratégia de Detecção de Impostos de Importação

**Data:** 08/01/2026  
**Objetivo:** Detectar lançamentos bancários que são impostos de importação (II, IPI, PIS, COFINS) de forma conservadora e segura

---

## ⚠️ Problema Identificado

Nem todos os lançamentos com "Impostos" são de importação:
- ❌ "Impostos" genérico → Pode ser ICMS, ISS, IRPF, etc.
- ✅ "Importação siscomex" → Claramente imposto de importação
- ✅ "Impostos" + vinculado a processo → Provavelmente imposto de importação

---

## 🔍 Estratégia de Detecção (Conservadora)

### 1. **Detecção Automática (Conservadora)**

A função `_eh_lancamento_impostos()` só marca como **possível imposto de importação** se:

#### ✅ Palavras-chave ESPECÍFICAS (marcam como possível):
- `IMPORTAÇÃO SISCOMEX`
- `IMPORTACAO SISCOMEX`
- `SISCOMEX`
- `IMPOSTO DE IMPORTAÇÃO`
- `IMPOSTO DE IMPORTACAO`
- `II IPI PIS COFINS` (combinação específica)
- `TRIBUTOS IMPORTAÇÃO`
- `DI ` (Declaração de Importação)
- `DUIMP` (Declaração Única de Importação)

#### ❌ Palavras de EXCLUSÃO (não marcam):
- `ICMS`
- `ISS`
- `IRPF`
- `IRPJ`
- `CSLL`
- `SIMPLES`
- `PARCELAMENTO`
- `REFIS`

### 2. **Flag `eh_possivel_imposto_importacao`**

Retorna `True` se:
1. Descrição contém palavras-chave específicas de SISCOMEX, **OU**
2. Lançamento já está vinculado a um processo (indica que pode ser de importação)

### 3. **Flag `requer_confirmacao`**

Sempre igual a `eh_possivel_imposto_importacao`. Indica que o frontend deve:
- Mostrar interface especial para distribuição de impostos
- **Mas só se o usuário confirmar** que são impostos de importação

---

## 🎨 Interface do Frontend

### Quando `eh_possivel_imposto_importacao: true`:

1. **Mostrar aviso/opção:**
   ```
   ⚠️ Este lançamento pode ser de impostos de importação.
   [ ] Confirmar que são impostos de importação (II, IPI, PIS, COFINS)
   ```

2. **Se usuário confirmar:**
   - Buscar impostos sugeridos: `GET /api/banco/impostos-processo/BGR.0070/25`
   - Mostrar interface de distribuição:
     ```
     Distribuir R$ 23.094,63 entre os impostos:
     
     [ ] II (Imposto de Importação): R$ _______
     [ ] IPI: R$ _______
     [ ] PIS: R$ _______
     [ ] COFINS: R$ _______
     [ ] Taxa SISCOMEX: R$ _______
     [ ] Antidumping: R$ _______
     
     Total: R$ 23.094,63 ✅
     ```

3. **Ao classificar:**
   - Enviar flag `impostos_importacao_confirmado: true` na classificação
   - Backend grava em `LANCAMENTO_TIPO_DESPESA` (como despesa)
   - Backend grava em `IMPOSTO_IMPORTACAO` (detalhado por tipo)

---

## 📊 Fluxo Completo

### Cenário 1: Lançamento "Importação siscomex"
```
1. Sistema detecta: eh_possivel_imposto_importacao = true
2. Frontend mostra: "Este lançamento parece ser de impostos de importação"
3. Usuário confirma: ✅
4. Frontend busca: GET /api/banco/impostos-processo/BGR.0070/25
5. Frontend mostra: Interface de distribuição com valores sugeridos
6. Usuário distribui: II: R$ 10.000, IPI: R$ 5.000, PIS: R$ 3.000, COFINS: R$ 5.094,63
7. Backend grava:
   - LANCAMENTO_TIPO_DESPESA (despesa geral)
   - IMPOSTO_IMPORTACAO (4 registros detalhados)
```

### Cenário 2: Lançamento "Impostos" (genérico)
```
1. Sistema detecta: eh_possivel_imposto_importacao = false
2. Frontend mostra: Interface normal de classificação
3. Usuário classifica normalmente (sem distribuição de impostos)
```

### Cenário 3: Lançamento "Impostos" + Processo vinculado
```
1. Sistema detecta: eh_possivel_imposto_importacao = true (porque tem processo)
2. Frontend mostra: "Este lançamento pode ser de impostos de importação"
3. Usuário confirma: ✅
4. Mesmo fluxo do Cenário 1
```

---

## 🔧 Implementação Backend

### Flags Retornadas

```json
{
  "id_movimentacao": 123,
  "descricao": "Importação siscomex",
  "eh_possivel_imposto_importacao": true,
  "requer_confirmacao": true,
  "valor": 23094.63
}
```

### Classificação com Confirmação

```json
{
  "id_movimentacao": 123,
  "classificacoes": [
    {
      "id_tipo_despesa": 5,
      "processo_referencia": "BGR.0070/25",
      "impostos_importacao_confirmado": true,  // ✅ Flag de confirmação
      "distribuicao_impostos": {
        "II": 10000.00,
        "IPI": 5000.00,
        "PIS": 3000.00,
        "COFINS": 5094.63
      }
    }
  ]
}
```

---

## ✅ Vantagens da Estratégia

1. **Conservadora**: Não assume que "Impostos" genérico é de importação
2. **Flexível**: Usuário confirma explicitamente
3. **Segura**: Evita gravar impostos errados (ICMS, ISS, etc.)
4. **Intuitiva**: Interface especial só aparece quando necessário
5. **Rastreável**: Flag `impostos_importacao_confirmado` documenta a decisão do usuário

---

## 📝 Exemplos de Descrições

| Descrição | `eh_possivel_imposto_importacao` | Motivo |
|-----------|----------------------------------|--------|
| "Importação siscomex" | ✅ `true` | Palavra-chave específica |
| "SISCOMEX" | ✅ `true` | Palavra-chave específica |
| "Impostos" | ❌ `false` | Genérico demais |
| "Impostos ICMS" | ❌ `false` | Contém palavra de exclusão |
| "Impostos" + processo vinculado | ✅ `true` | Tem processo (indica importação) |
| "II IPI PIS COFINS" | ✅ `true` | Combinação específica |

---

**Última atualização:** 08/01/2026


