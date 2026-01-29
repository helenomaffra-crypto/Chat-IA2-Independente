# 📋 Migração de Documentos 2025 para DOCUMENTO_ADUANEIRO

**Data:** 19/01/2026  
**Status:** ✅ **IMPLEMENTADO**  
**Objetivo:** Popular `mAIke_assistente.dbo.DOCUMENTO_ADUANEIRO` com todos os DI/DUIMP de 2025 (e anos anteriores) a partir das fontes históricas

---

## 🎯 Problema Identificado

O sistema atual só popula `DOCUMENTO_ADUANEIRO` quando:
1. ✅ Consulta documento via API diretamente
2. ✅ Sincroniza processo do Kanban (extrai documentos do JSON)

**Problema:** Processos antigos de 2025 que não estão no Kanban atual não têm seus documentos gravados em `DOCUMENTO_ADUANEIRO`, causando:
- Queries "o que registramos" retornando resultados incompletos
- Dependência de queries híbridas (Serpro/Duimp DB) que são mais lentas
- Inconsistência entre dados recentes (em `DOCUMENTO_ADUANEIRO`) e históricos (apenas em Serpro/Duimp DB)

---

## ✅ Solução: Script de Migração

**Arquivo:** `scripts/migrar_documentos_2025_para_documento_aduaneiro.py`

### Funcionalidades

1. **Busca DI de 2025 do Serpro.dbo**
   - Query em `Serpro.dbo.Hi_Historico_Di` + `Di_Dados_Gerais` + `Di_Dados_Despacho`
   - Filtra por `YEAR(dataHoraRegistro) = 2025` (ou `dataHoraSituacaoDi` se registro não existir)
   - Extrai: número DI, processo, situação, canal, datas

2. **Busca DUIMP de 2025 do Duimp.dbo**
   - Query em `Duimp.dbo.duimp` + `duimp_resultado_analise_risco`
   - Filtra por `YEAR(data_registro) = 2025`
   - Extrai: número DUIMP, processo, situação, canal, versão, datas

3. **Gravação via DocumentoHistoricoService**
   - Usa o mesmo serviço que o sistema usa normalmente
   - Garante consistência de dados
   - Evita duplicatas (verifica se já existe antes de gravar)
   - Detecta mudanças e grava histórico

4. **Idempotência**
   - Verifica se documento já existe antes de gravar
   - Pode ser executado múltiplas vezes sem duplicar dados
   - Suporta `--dry-run` para testar antes de executar

---

## 🚀 Como Usar

### Migração Completa de 2025

```bash
python3 scripts/migrar_documentos_2025_para_documento_aduaneiro.py
```

### Migração de Outro Ano

```bash
python3 scripts/migrar_documentos_2025_para_documento_aduaneiro.py --ano 2024
```

### Teste (Dry-Run)

```bash
python3 scripts/migrar_documentos_2025_para_documento_aduaneiro.py --dry-run
```

### Limitar Quantidade (para testes)

```bash
python3 scripts/migrar_documentos_2025_para_documento_aduaneiro.py --limit 100
```

### Migrar Apenas DI ou DUIMP

```bash
# Apenas DI
python3 scripts/migrar_documentos_2025_para_documento_aduaneiro.py --tipo DI

# Apenas DUIMP
python3 scripts/migrar_documentos_2025_para_documento_aduaneiro.py --tipo DUIMP
```

---

## 📊 Estratégia de Dados

### Fonte de Dados

**DI:**
- **Fonte:** `Serpro.dbo` (tabelas históricas)
- **Query:** `PROCESSO_IMPORTACAO` → `Hi_Historico_Di` → `Di_Root_Declaracao_Importacao` → `Di_Dados_Gerais` + `Di_Dados_Despacho`
- **Campos extraídos:**
  - `numeroDi` (número do documento)
  - `situacaoDi` (situação)
  - `canalSelecaoParametrizada` (canal)
  - `dataHoraRegistro` (data de registro)
  - `dataHoraDesembaraco` (data de desembaraço)
  - `dataHoraSituacaoDi` (data da situação)

**DUIMP:**
- **Fonte:** `Duimp.dbo` (tabela `duimp`)
- **Query:** `duimp` + `duimp_resultado_analise_risco`
- **Campos extraídos:**
  - `numero` (número do documento)
  - `ultima_situacao` (situação)
  - `canal_consolidado` (canal)
  - `data_registro` (data de registro)
  - `versao` (versão do documento)

### Payload Mínimo

O script constrói um payload mínimo compatível com `DocumentoHistoricoService`:

**DI:**
```python
{
    "numero": "2504026314",
    "numeroDi": "2504026314",
    "situacaoDi": "DI_DESEMBARACADA",
    "canalSelecaoParametrizada": "VERDE",
    "dataHoraRegistro": "2025-02-19T10:30:00",
    "dataHoraDesembaraco": "2025-02-20T14:00:00",
    "_fonte": "SERPRO_MIGRACAO"
}
```

**DUIMP:**
```python
{
    "numero": "25BR00002284997",
    "situacao": "DUIMP_DESEMBARACADA",
    "ultimaSituacao": "DUIMP_DESEMBARACADA",
    "dataRegistro": "2025-02-19T10:30:00",
    "versaoDocumento": "1",
    "numeroProcesso": "VDM.0003/25",
    "_fonte": "DUIMP_DB_MIGRACAO"
}
```

---

## ✅ Validação

### Verificar Documentos Migrados

```sql
-- Contar DI de 2025 em DOCUMENTO_ADUANEIRO
SELECT COUNT(*) 
FROM mAIke_assistente.dbo.DOCUMENTO_ADUANEIRO
WHERE tipo_documento = 'DI'
  AND YEAR(data_registro) = 2025

-- Contar DUIMP de 2025 em DOCUMENTO_ADUANEIRO
SELECT COUNT(*) 
FROM mAIke_assistente.dbo.DOCUMENTO_ADUANEIRO
WHERE tipo_documento = 'DUIMP'
  AND YEAR(data_registro) = 2025
```

### Comparar com Fonte Original

```sql
-- DI no Serpro (fonte original)
SELECT COUNT(DISTINCT ddg.numeroDi)
FROM Serpro.dbo.Hi_Historico_Di diH
INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot
    ON diH.diId = diRoot.dadosDiId
INNER JOIN Serpro.dbo.Di_Dados_Gerais ddg
    ON diRoot.dadosGeraisId = ddg.dadosGeraisId
LEFT JOIN Serpro.dbo.Di_Dados_Despacho diDesp
    ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
WHERE (
    (diDesp.dataHoraRegistro IS NOT NULL AND YEAR(diDesp.dataHoraRegistro) = 2025)
    OR
    (diDesp.dataHoraRegistro IS NULL AND ddg.dataHoraSituacaoDi IS NOT NULL AND YEAR(ddg.dataHoraSituacaoDi) = 2025)
)

-- DUIMP no Duimp.dbo (fonte original)
SELECT COUNT(*)
FROM Duimp.dbo.duimp
WHERE YEAR(data_registro) = 2025
```

---

## 🔄 Próximos Passos

### 1. Executar Migração Inicial

```bash
# Teste primeiro
python3 scripts/migrar_documentos_2025_para_documento_aduaneiro.py --dry-run --limit 100

# Se OK, executar completo
python3 scripts/migrar_documentos_2025_para_documento_aduaneiro.py
```

### 2. Validar Resultados

- Verificar contagens (comparar com fonte original)
- Testar query "o que registramos junho 25" novamente
- Verificar se resultados estão completos

### 3. Migrar Outros Anos (se necessário)

```bash
# 2024
python3 scripts/migrar_documentos_2025_para_documento_aduaneiro.py --ano 2024

# 2023
python3 scripts/migrar_documentos_2025_para_documento_aduaneiro.py --ano 2023
```

### 4. Monitorar Sincronização Futura

- ✅ Sistema já popula automaticamente para processos novos (via Kanban)
- ✅ Sistema já popula quando consulta documento via API
- ⚠️ Processos antigos que não estão no Kanban precisam ser migrados manualmente (este script)

---

## 📝 Notas Importantes

1. **Idempotência:** O script pode ser executado múltiplas vezes sem duplicar dados (verifica se já existe antes de gravar)

2. **Performance:** Para grandes volumes, considere usar `--limit` e executar em lotes

3. **Dry-Run:** Sempre teste com `--dry-run` antes de executar em produção

4. **Fonte da Verdade:** O script usa `DocumentoHistoricoService`, garantindo consistência com o sistema normal

5. **Duplicatas:** O script verifica se documento já existe antes de gravar, mas pode haver casos edge (ex: versões diferentes do mesmo documento)

---

## 🐛 Troubleshooting

### Erro: "SQL Server adapter não disponível"

- Verificar variáveis de ambiente (`.env`)
- Verificar conexão com SQL Server
- Verificar se `get_sql_adapter()` retorna adapter válido

### Documentos não aparecem após migração

- Verificar se `data_registro` está preenchido (necessário para queries "o que registramos")
- Verificar se `processo_referencia` está preenchido (necessário para vincular ao processo)
- Verificar logs do script para erros específicos

### Performance lenta

- Usar `--limit` para processar em lotes
- Executar em horário de menor uso do banco
- Considerar executar por categoria (modificar script se necessário)

---

**Última atualização:** 19/01/2026
