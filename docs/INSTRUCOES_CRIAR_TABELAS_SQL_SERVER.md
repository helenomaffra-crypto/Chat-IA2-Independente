# 📋 Instruções: Criar Tabelas no SQL Server

**Data:** 08/01/2026  
**Problema:** Tabelas do banco `mAIke_assistente` ainda não foram criadas  
**Solução:** Executar script SQL

---

## 🎯 Situação Atual

**Tabelas que NÃO existem:**
- ❌ `DOCUMENTO_ADUANEIRO`
- ❌ `PROCESSO_IMPORTACAO`
- ❌ `HISTORICO_DOCUMENTO_ADUANEIRO`
- ❌ `IMPOSTO_IMPORTACAO` (ainda não implementado)
- ❌ `VALOR_MERCADORIA` (ainda não implementado)

**Tabelas que JÁ existem:**
- ✅ `LANCAMENTO_TIPO_DESPESA` (despesas conciliadas)
- ✅ `MOVIMENTACAO_BANCARIA`
- ✅ `TIPO_DESPESA`

---

## 📝 Script SQL Disponível

**Arquivo:** `scripts/criar_banco_maike_completo.sql`

**Conteúdo:**
- ✅ Criação do banco `mAIke_assistente` (se não existir)
- ✅ Criação de schemas (comunicacao, ia, legislacao, auditoria)
- ✅ Criação de todas as tabelas principais
- ✅ Criação de índices
- ✅ Tabela `DOCUMENTO_ADUANEIRO` (linha 626)
- ✅ Tabela `PROCESSO_IMPORTACAO` (linha 244)
- ✅ Tabela `HISTORICO_DOCUMENTO_ADUANEIRO` (deve estar no script)

---

## 🚀 Como Executar

### **Opção 1: SQL Server Management Studio (SSMS)**

1. Abrir SQL Server Management Studio
2. Conectar ao servidor: `172.16.10.241\SQLEXPRESS` (ou seu servidor)
3. Abrir o arquivo: `scripts/criar_banco_maike_completo.sql`
4. Executar o script (F5 ou botão Execute)
5. Verificar se todas as tabelas foram criadas

### **Opção 2: Via Python (Script Automático)**

Criar script Python que executa o SQL automaticamente:

```python
# scripts/executar_criar_banco.py
from utils.sql_server_adapter import get_sql_adapter

sql_adapter = get_sql_adapter()

# Ler arquivo SQL
with open('scripts/criar_banco_maike_completo.sql', 'r', encoding='utf-8') as f:
    sql_script = f.read()

# Executar script (dividir por GO se necessário)
# Nota: execute_query pode não suportar múltiplos comandos
# Pode precisar dividir o script em partes menores
```

### **Opção 3: Via Linha de Comando (sqlcmd)**

```bash
sqlcmd -S 172.16.10.241\SQLEXPRESS -d mAIke_assistente -i scripts/criar_banco_maike_completo.sql
```

---

## ✅ Verificação Após Executar

Execute o script de verificação:

```bash
python3 testes/verificar_documentos_bgr_0070.py
```

**Esperado:**
```
✅ Tabela DOCUMENTO_ADUANEIRO existe
✅ Encontrados 2 documento(s) para BGR.0070/25
```

---

## 📋 Tabelas que Serão Criadas

### **Tabelas Principais:**
1. ✅ `PROCESSO_IMPORTACAO` - Processos de importação
2. ✅ `DOCUMENTO_ADUANEIRO` - CE, DI, DUIMP, CCT
3. ✅ `HISTORICO_DOCUMENTO_ADUANEIRO` - Histórico de mudanças
4. ✅ `FORNECEDOR_CLIENTE` - Fornecedores e clientes
5. ✅ `MOVIMENTACAO_BANCARIA` - Lançamentos bancários
6. ✅ `LANCAMENTO_TIPO_DESPESA` - Despesas conciliadas (já existe)
7. ✅ `TIPO_DESPESA` - Catálogo de tipos de despesa (já existe)

### **Tabelas de Integração:**
8. ✅ `SHIPSGO_TRACKING` - Tracking de navios
9. ✅ `TIMELINE_PROCESSO` - Timeline de eventos

### **Tabelas de Comunicação:**
10. ✅ `EMAIL_ENVIADO` (schema comunicacao)
11. ✅ `EMAIL_AGENDADO` (schema comunicacao)

### **Tabelas de IA:**
12. ✅ `CONVERSA_CHAT` (schema ia)
13. ✅ `REGRA_APRENDIDA` (schema ia)

### **Tabelas de Auditoria:**
14. ✅ `LOG_SINCRONIZACAO` (schema auditoria)
15. ✅ `LOG_CONSULTA_API` (schema auditoria)

---

## ⚠️ Tabelas que AINDA NÃO estão no Script

Estas tabelas precisam ser adicionadas ao script:

1. ⚠️ `IMPOSTO_IMPORTACAO` - Impostos pagos (II, IPI, PIS, COFINS)
2. ⚠️ `VALOR_MERCADORIA` - Valores da mercadoria (Descarga, Embarque)

**Ver:** `docs/ESTRATEGIA_POPULACAO_BANCO_MAIKE.md` - Estrutura proposta

---

## 🎯 Próximos Passos

1. ✅ **Executar script SQL** para criar tabelas
2. ✅ **Verificar** se tabelas foram criadas
3. ⚠️ **Adicionar tabelas faltantes** (IMPOSTO_IMPORTACAO, VALOR_MERCADORIA)
4. ⚠️ **Implementar gravação** de processos no SQL Server
5. ⚠️ **Implementar gravação** de documentos quando usa cache

---

**Última atualização:** 08/01/2026


