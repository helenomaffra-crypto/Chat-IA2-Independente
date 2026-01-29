# 📋 Resumo: Catálogo de Despesas Padrão

## ✅ O que foi criado

**3 novas tabelas + atualização de 1 tabela existente:**

1. **`TIPO_DESPESA`** - Catálogo com 23 despesas padrão pré-cadastradas
2. **`LANCAMENTO_TIPO_DESPESA`** - Relação N:N (lançamento ↔ tipo despesa ↔ processo)
3. **`PLANO_CONTAS`** - Preparada para futuro (contabilidade)
4. **`MOVIMENTACAO_BANCARIA_PROCESSO`** - Atualizada com referência a tipo de despesa

---

## 🎯 Benefícios principais

✅ **Um lançamento pode ter múltiplas despesas de múltiplos processos**
- Exemplo: Um lançamento de R$ 10.000 pode conter:
  - R$ 5.000 - Frete Internacional (DMD.0083/25)
  - R$ 3.000 - AFRMM (DMD.0083/25)
  - R$ 2.000 - Frete Internacional (ALH.0005/25)

✅ **Classificação manual ou automática**
- Classificação manual pelo usuário
- Classificação automática via IA/detecção de palavras-chave
- Níveis de confiança para validação

✅ **Preparado para plano de contas**
- Campo `plano_contas_codigo` em `TIPO_DESPESA`
- Tabela `PLANO_CONTAS` pronta para uso futuro

---

## 📊 Despesas Padrão Cadastradas (23)

**Frete e Logística:**
- Frete Internacional
- Frete DTA
- Seguro

**Impostos e Taxas:**
- AFRMM
- Multas
- Tx Siscomex (D.I.)
- Tx Siscomex (D.A.)
- GRU / Tx LI
- Antidumping
- Tarifas Bancárias

**Serviços:**
- Liberação B/L
- Inspeção de Mercadoria
- Armazenagem DTA
- Armazenagem
- Despachante
- SDA
- Carreto
- Escolta
- Lavagem CTNR

**Outros:**
- Outros Custos Internac.
- Demurrage
- Contrato de Câmbio
- Outros

---

## 🚀 Como criar

**Opção 1: Via SQL (recomendado)**
```bash
sqlcmd -S servidor -d mAIke_assistente -i scripts/criar_catalogo_despesas.sql
```

**Opção 2: Via Python**
```bash
python3 scripts/criar_catalogo_despesas_via_python.py
```

---

## 📈 Próximos Passos

**Fase 2: Interface de Classificação**
- [ ] Tela para classificar lançamentos
- [ ] Seleção múltipla de tipos de despesa
- [ ] Distribuição de valores
- [ ] Vinculação a processos

**Fase 3: Classificação Automática**
- [ ] Detecção de palavras-chave
- [ ] Integração com IA
- [ ] Sugestões com nível de confiança

**Fase 4: Integração com Plano de Contas**
- [ ] Importar plano de contas
- [ ] Vincular tipos de despesa a códigos contábeis
- [ ] Geração de relatórios contábeis

---

## 📝 Exemplo de Uso

**Consulta de lançamentos classificados:**
```sql
SELECT 
    mb.data_movimentacao,
    mb.valor_movimentacao,
    td.nome_despesa,
    ltd.valor_despesa,
    ltd.processo_referencia
FROM MOVIMENTACAO_BANCARIA mb
JOIN LANCAMENTO_TIPO_DESPESA ltd ON mb.id_movimentacao = ltd.id_movimentacao_bancaria
JOIN TIPO_DESPESA td ON ltd.id_tipo_despesa = td.id_tipo_despesa
WHERE mb.banco_origem = 'BB'
ORDER BY mb.data_movimentacao DESC
```

---

**Documentação completa:** `docs/CATALOGO_DESPESAS_PADRAO.md`

