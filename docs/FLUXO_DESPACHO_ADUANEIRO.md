# 📦 Fluxo do Despacho Aduaneiro na Importação

## 🎯 Contexto

Este documento descreve o **fluxo completo do despacho aduaneiro** na importação de cargas, desde o carregamento no exterior até a entrega ao cliente final no Brasil. Este contexto é essencial para entender o significado de cada data e situação no sistema.

---

## 🔄 Fluxo Completo do Despacho Aduaneiro

### **Etapa 1: Carregamento no Exterior** 🚢
- **O que acontece**: Carga é carregada no navio/aeronave no país de origem
- **Situação CE**: `CARREGADA` ou `EMBARCADA`
- **Data relevante**: `dataEmbarque` (quando foi carregada)
- **Status**: Carga ainda não chegou ao Brasil

### **Etapa 2: Trânsito Internacional** 🌊
- **O que acontece**: Navio/aeronave em viagem do exterior para o Brasil
- **Situação CE**: `EM_TRANSITO` ou `EMBARCADA`
- **Data relevante**: `dataPrevisaoChegada` (ETA - **apenas previsão**, não confirmada)
- **Status**: Carga ainda não chegou ao Brasil

### **Etapa 3: Chegada ao Porto/Aeroporto de Destino** ⚓
- **O que acontece**: Navio/aeronave chega ao porto/aeroporto brasileiro
- **Situação CE**: `MANIFESTADA` (navio chegou, mas carga ainda não foi descarregada)
- **Data relevante**: `dataAtracamento` (navio atracou, mas carga pode não ter sido descarregada ainda)
- **Status**: Navio chegou, mas carga ainda não foi descarregada

### **Etapa 4: Descarregamento** 📥
- **O que acontece**: Carga é descarregada do navio/aeronave
- **Situação CE**: `DESCARREGADA`
- **⚠️ IMPORTANTE**: `DESCARREGADA` **NÃO significa chegada ao destino final**!
  - Pode ser porto intermediário (transbordo)
  - Carga pode continuar viagem para outro porto
  - **NÃO usar esta situação para determinar chegada**
- **Status**: Carga foi descarregada, mas pode não estar no destino final

### **Etapa 5: Chegada ao Destino Final** ✅
- **O que acontece**: Carga chegou ao porto/aeroporto de destino final (onde será nacionalizada)
- **Situação CE**: Pode estar `DESCARREGADA`, mas **isso sozinho não confirma chegada**
- **Data relevante**: `dataDestinoFinal` ⭐ **ÚNICA FONTE CONFIÁVEL DE CHEGADA**
  - Esta é a data que indica que a carga **realmente chegou** ao destino final
  - Vem da API do CE (fonte oficial)
  - **Esta é a data usada para determinar se a carga chegou**
- **Status**: Carga chegou ao destino final

### **Etapa 6: Armazenamento** 📦
- **O que acontece**: Carga foi armazenada no terminal/armazém alfandegário
- **Situação CE**: `ARMAZENADA`
- **Data relevante**: `dataArmazenamento` ⭐ **CONFIRMA CHEGADA E ARMAZENAMENTO**
  - Indica que a carga foi armazenada e está disponível para registro de DI/DUIMP
  - Também confirma que a carga chegou ao destino final
- **Status**: Carga armazenada e pronta para despacho

### **Etapa 7: Registro de DI/DUIMP** 📋
- **O que acontece**: Despachante registra a Declaração de Importação (DI) ou DUIMP
- **Situação CE**: `VINCULADA_A_DOCUMENTO_DE_DESPACHO` ou `VINCULADA`
- **Data relevante**: `dataHoraRegistro` (quando DI/DUIMP foi registrada)
- **Status**: Documento de importação registrado

### **Etapa 8: Desembaraço Aduaneiro** ✅
- **O que acontece**: Receita Federal libera a carga após análise da DI/DUIMP
- **Situação DI**: `DESEMBARACADA`
- **Data relevante**: `dataDesembaraco` (quando foi liberada pela Receita)
- **Status**: Carga liberada pela Receita Federal

### **Etapa 9: Entrega ao Cliente** 🚚
- **O que acontece**: Carga é entregue ao cliente final (importador)
- **Situação CE**: `ENTREGUE`
- **Data relevante**: `dataEntrega` ⚠️ **NÃO é data de chegada ao porto!**
  - Esta é a data de entrega ao cliente final
  - **NÃO usar para determinar se a carga chegou ao porto**
- **Status**: Carga entregue ao cliente

---

## 📅 Significado de Cada Data no Sistema

### **Datas de Chegada (Prioridade para determinar se chegou)**

#### 1. `dataDestinoFinal` ⭐ **PRIORIDADE 1 - ÚNICA FONTE CONFIÁVEL**
- **O que é**: Data em que a carga chegou ao **destino final** (porto/aeroporto onde será nacionalizada)
- **Fonte**: API do CE (fonte oficial)
- **Quando usar**: **SEMPRE usar esta data para determinar se a carga chegou**
- **Regra**: Se `dataDestinoFinal <= hoje` → Carga chegou ✅
- **Exemplo**: `2025-12-08` → Carga chegou em 08/12/2025

#### 2. `dataArmazenamento` ⭐ **PRIORIDADE 2 - CONFIRMA CHEGADA**
- **O que é**: Data em que a carga foi armazenada no terminal/armazém
- **Fonte**: API do CE
- **Quando usar**: Se não tiver `dataDestinoFinal`, usar esta (também confirma chegada)
- **Regra**: Se `dataArmazenamento <= hoje` → Carga chegou e foi armazenada ✅
- **Exemplo**: `2025-12-08` → Carga foi armazenada em 08/12/2025

### **Datas que NÃO indicam chegada ao destino final**

#### 3. `dataAtracamento` ❌ **NÃO USAR PARA CHEGADA**
- **O que é**: Data em que o navio atracou no porto
- **Problema**: Navio pode atracar, mas a carga pode não ter sido descarregada ainda
- **Quando usar**: Apenas para informação, não para determinar chegada
- **Exemplo**: Navio atracou, mas carga ainda está a bordo

#### 4. `dataSituacaoCargaCe` ❌ **NÃO USAR PARA CHEGADA**
- **O que é**: Data em que a situação do CE mudou (ex: MANIFESTADA → ARMAZENADA)
- **Problema**: É data de mudança de status, não data de chegada
- **Quando usar**: Apenas para informação de quando o status mudou
- **Exemplo**: `2025-12-08` → Status mudou em 08/12/2025, mas não indica quando chegou

#### 5. `dataPrevisaoChegada` (ETA) ❌ **NÃO USAR PARA CHEGADA**
- **O que é**: Previsão de chegada (ETA - Estimated Time of Arrival)
- **Problema**: É apenas uma **previsão**, não confirmação
- **Quando usar**: Apenas para informação de quando **deve** chegar
- **Exemplo**: `2025-12-15` → Previsão de chegada em 15/12/2025 (pode mudar)

#### 6. `dataEntrega` ❌ **NÃO USAR PARA CHEGADA**
- **O que é**: Data de entrega ao cliente final
- **Problema**: Esta é a **última etapa** do processo, não a chegada ao porto
- **Quando usar**: Apenas para saber quando foi entregue ao cliente
- **Exemplo**: `2025-12-20` → Entregue ao cliente em 20/12/2025

---

## 🎯 Regra para Determinar se Carga Chegou

### **Regra Simples:**
```
SE dataDestinoFinal <= hoje E sem DI/DUIMP
ENTÃO carga chegou e precisa de registro ✅
```

### **Implementação:**
```python
# Buscar dataDestinoFinal do JSON
data_destino_final = json_data.get('dataDestinoFinal')

# Se não tem dataDestinoFinal, não chegou
if not data_destino_final:
    return None  # Não chegou

# Parsear data
data_chegada = parse_date(data_destino_final)

# Se data <= hoje, chegou
if data_chegada <= hoje:
    return data_chegada  # ✅ Chegou
else:
    return None  # Ainda não chegou (data futura)
```

---

## ⚠️ Situações do CE e seu Significado

### **Situações que NÃO indicam chegada ao destino final:**

| Situação | Significado | Chegou? |
|----------|-------------|---------|
| `CARREGADA` | Carga foi carregada no navio | ❌ Não (ainda no exterior) |
| `EMBARCADA` | Carga embarcada | ❌ Não (ainda no exterior) |
| `EM_TRANSITO` | Carga em trânsito | ❌ Não (ainda em viagem) |
| `MANIFESTADA` | Navio chegou, mas carga não descarregada | ❌ Não (navio chegou, carga não) |
| `DESCARREGADA` | Carga descarregada | ⚠️ Pode ser porto intermediário |
| `VINCULADA` | Documento vinculado | ❌ Não (pode não ter chegado) |

### **Situações que indicam chegada (mas só com data confirmada):**

| Situação | Significado | Chegou? |
|----------|-------------|---------|
| `ARMAZENADA` | Carga armazenada | ✅ Sim (se tiver `dataDestinoFinal` ou `dataArmazenamento`) |
| `ENTREGUE` | Carga entregue ao cliente | ✅ Sim (mas já passou do escopo de chegada) |

### **⚠️ IMPORTANTE:**
- **NUNCA usar apenas a situação** para determinar chegada
- **SEMPRE verificar `dataDestinoFinal`** primeiro
- Situação `DESCARREGADA` sozinha **NÃO confirma chegada** (pode ser transbordo)

---

## 📊 Exemplo Prático

### **Cenário 1: Carga que Chegou**
```json
{
  "numeroPedido": "ALH.0176/25",
  "dataDestinoFinal": "2025-11-25",
  "dataArmazenamento": "2025-11-26",
  "situacaoCargaCe": "ARMAZENADA",
  "numeroDi": null,
  "numeroDuimp": null
}
```
**Análise:**
- ✅ `dataDestinoFinal = 2025-11-25` (<= hoje) → **Chegou**
- ✅ Sem DI/DUIMP → **Precisa de registro**
- **Resultado**: Aparece na lista "quais processos chegaram?"

### **Cenário 2: Carga Descarregada em Porto Intermediário**
```json
{
  "numeroPedido": "UPI.0002/25",
  "dataDestinoFinal": null,  // ⚠️ Não tem!
  "situacaoCargaCe": "DESCARREGADA",
  "dataAtracamento": "2025-12-08"
}
```
**Análise:**
- ❌ `dataDestinoFinal = null` → **Não chegou ao destino final**
- ⚠️ `DESCARREGADA` → Pode ser porto intermediário (transbordo)
- **Resultado**: **NÃO aparece** na lista (não chegou ao destino final)

### **Cenário 3: Carga com ETA (Previsão)**
```json
{
  "numeroPedido": "VDM.0001/25",
  "dataDestinoFinal": null,
  "dataPrevisaoChegada": "2025-12-15",  // ETA
  "situacaoCargaCe": "EM_TRANSITO"
}
```
**Análise:**
- ❌ `dataDestinoFinal = null` → **Não chegou**
- ⚠️ `dataPrevisaoChegada` → Apenas previsão, não confirmação
- **Resultado**: **NÃO aparece** na lista (ainda não chegou)

---

## 🔍 Como o Sistema Usa Essas Informações

### **Função: `listar_processos_liberados_registro()`**
Esta função lista processos que:
1. ✅ Chegaram ao destino final (`dataDestinoFinal <= hoje`)
2. ✅ Não têm DI nem DUIMP registrada

**Regra implementada:**
```python
# 1. Verificar se tem DI/DUIMP
if numero_di or numero_duimp:
    continue  # Já tem documento, não precisa

# 2. Verificar se tem dataDestinoFinal
data_destino_final = json_data.get('dataDestinoFinal')
if not data_destino_final:
    continue  # Não chegou ao destino final

# 3. Verificar se data <= hoje
data_chegada = parse_date(data_destino_final)
if data_chegada > hoje:
    continue  # Ainda não chegou (data futura)

# 4. Se passou todas as validações, incluir na lista
resultados.append(processo)
```

---

## 📝 Resumo para Consulta Rápida

### **Para determinar se carga chegou:**
1. ✅ **SEMPRE usar `dataDestinoFinal`** (única fonte confiável)
2. ✅ Se não tiver `dataDestinoFinal`, usar `dataArmazenamento` (também confirma)
3. ❌ **NUNCA usar** `dataAtracamento`, `dataSituacaoCargaCe`, `dataPrevisaoChegada`, `dataEntrega`

### **Regra de negócio:**
```
Carga chegou = dataDestinoFinal <= hoje
```

### **Para listar processos que chegaram sem despacho:**
```
dataDestinoFinal <= hoje AND (sem DI AND sem DUIMP)
```

---

## 🔄 Fluxo Visual

```
EXTERIOR
   │
   ├─► [1] CARREGADA (dataEmbarque)
   │
   ├─► [2] EM_TRANSITO (dataPrevisaoChegada - ETA)
   │
   ├─► [3] MANIFESTADA (dataAtracamento - navio chegou)
   │
   ├─► [4] DESCARREGADA (pode ser porto intermediário!)
   │
   └─► [5] ⭐ CHEGADA AO DESTINO FINAL (dataDestinoFinal) ✅
       │
       ├─► [6] ARMAZENADA (dataArmazenamento)
       │
       ├─► [7] Registro DI/DUIMP
       │
       ├─► [8] DESEMBARACADA (dataDesembaraco)
       │
       └─► [9] ENTREGUE (dataEntrega - ao cliente)
```

---

## 💡 Notas Importantes

1. **`dataDestinoFinal` é a única fonte confiável** de chegada ao destino final
2. **Situação `DESCARREGADA` sozinha não confirma chegada** (pode ser transbordo)
3. **ETA (`dataPrevisaoChegada`) é apenas previsão**, não confirmação
4. **`dataEntrega` é entrega ao cliente**, não chegada ao porto
5. **Sempre verificar `dataDestinoFinal` primeiro** antes de usar outras datas

---

## 📚 Referências

- API do CE (Conhecimento de Embarque)
- API do CCT (Conhecimento de Carga Aérea)
- Portal Único (DUIMP)
- Sistema de Despacho Aduaneiro

---

**Última atualização**: 09/12/2025
**Autor**: Sistema de IA (baseado em contexto de despacho aduaneiro)

