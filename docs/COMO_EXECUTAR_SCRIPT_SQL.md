# 🚀 Como Executar o Script SQL - criar_banco_maike_completo.sql

**Data:** 08/01/2026  
**Arquivo:** `scripts/criar_banco_maike_completo.sql`  
**Objetivo:** Criar todas as tabelas do banco `mAIke_assistente`

---

## 📋 Pré-requisitos

1. ✅ Acesso ao SQL Server (172.16.10.241\SQLEXPRESS ou 172.16.10.8\SQLEXPRESS)
2. ✅ Permissões de DBA ou CREATE TABLE
3. ✅ SQL Server Management Studio (SSMS) ou ferramenta similar

---

## 🎯 Opção 1: SQL Server Management Studio (SSMS) - RECOMENDADO

### **Passo a Passo:**

1. **Abrir SQL Server Management Studio**
   - Windows: Iniciar → SQL Server Management Studio
   - Ou baixar: https://docs.microsoft.com/en-us/sql/ssms/download-sql-server-management-studio-ssms

2. **Conectar ao Servidor**
   - **Server name:** `172.16.10.241\SQLEXPRESS` (ou `172.16.10.8\SQLEXPRESS`)
   - **Authentication:** Windows Authentication ou SQL Server Authentication
   - Clicar em **Connect**

3. **Abrir o Script SQL**
   - Menu: **File → Open → File**
   - Navegar até: `Chat-IA-Independente/scripts/criar_banco_maike_completo.sql`
   - Clicar em **Open**

4. **Executar o Script**
   - Pressionar **F5** ou clicar no botão **Execute** (▶️)
   - Aguardar execução completa
   - Verificar mensagens no painel "Messages" (deve mostrar "✅ Tabela X criada" para cada tabela)

5. **Verificar Resultado**
   - No Object Explorer, expandir: **Databases → mAIke_assistente → Tables**
   - Verificar se as tabelas foram criadas
   - Ou executar: `python3 testes/verificar_todas_tabelas_banco_novo.py`

---

## 🎯 Opção 2: Azure Data Studio (Alternativa ao SSMS)

### **Passo a Passo:**

1. **Abrir Azure Data Studio**
   - Baixar: https://aka.ms/azuredatastudio

2. **Conectar ao Servidor**
   - Clicar em **New Connection**
   - **Server:** `172.16.10.241\SQLEXPRESS`
   - **Authentication:** Windows Authentication ou SQL Server Authentication
   - Clicar em **Connect**

3. **Abrir o Script SQL**
   - Menu: **File → Open File**
   - Navegar até: `scripts/criar_banco_maike_completo.sql`

4. **Executar o Script**
   - Selecionar todo o conteúdo (Ctrl+A)
   - Clicar em **Run** ou pressionar **F5**

---

## 🎯 Opção 3: Linha de Comando (sqlcmd)

### **Windows:**

```cmd
sqlcmd -S 172.16.10.241\SQLEXPRESS -i "C:\caminho\para\Chat-IA-Independente\scripts\criar_banco_maike_completo.sql" -o "resultado.txt"
```

### **Linux/macOS:**

```bash
sqlcmd -S 172.16.10.241\\SQLEXPRESS -i scripts/criar_banco_maike_completo.sql -o resultado.txt
```

**Nota:** Pode precisar instalar `sqlcmd` primeiro.

---

## 🎯 Opção 4: Via Python (Parcial - apenas algumas tabelas)

**⚠️ LIMITAÇÃO:** O `sql_server_adapter` pode não suportar múltiplos comandos `GO` do SQL Server.

**Solução:** Executar apenas a criação de tabelas críticas:

```python
# scripts/executar_criar_tabelas_criticas.py
from utils.sql_server_adapter import get_sql_adapter

sql_adapter = get_sql_adapter()

# Criar apenas DOCUMENTO_ADUANEIRO (tabela crítica faltante)
query = """
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[DOCUMENTO_ADUANEIRO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[DOCUMENTO_ADUANEIRO] (
        id_documento BIGINT IDENTITY(1,1) PRIMARY KEY,
        numero_documento VARCHAR(50) NOT NULL,
        tipo_documento VARCHAR(50) NOT NULL,
        processo_referencia VARCHAR(50),
        status_documento VARCHAR(100),
        canal_documento VARCHAR(20),
        data_registro DATETIME,
        data_situacao DATETIME,
        data_desembaraco DATETIME,
        fonte_dados VARCHAR(50),
        json_dados_originais NVARCHAR(MAX),
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_numero_documento ON [dbo].[DOCUMENTO_ADUANEIRO](numero_documento);
    CREATE INDEX idx_tipo_documento ON [dbo].[DOCUMENTO_ADUANEIRO](tipo_documento);
    CREATE INDEX idx_processo ON [dbo].[DOCUMENTO_ADUANEIRO](processo_referencia);
END
"""

result = sql_adapter.execute_query(query, database='mAIke_assistente')
if result.get('success'):
    print("✅ Tabela DOCUMENTO_ADUANEIRO criada!")
else:
    print(f"❌ Erro: {result.get('error')}")
```

---

## ⚠️ Problemas Comuns

### **Erro: "Cannot open database 'mAIke_assistente'"**

**Solução:** O banco não existe. O script cria automaticamente, mas se falhar:
```sql
USE master;
GO
CREATE DATABASE [mAIke_assistente];
GO
```

### **Erro: "Permission denied"**

**Solução:** Precisa de permissões de DBA. Solicitar ao administrador do SQL Server.

### **Erro: "Invalid object name"**

**Solução:** Verificar se está conectado ao servidor correto e se o banco existe.

### **Script muito grande (timeout)**

**Solução:** Executar em partes:
1. Primeiro: Criar banco e schemas
2. Depois: Criar tabelas críticas (PROCESSO_IMPORTACAO, DOCUMENTO_ADUANEIRO)
3. Por último: Criar tabelas restantes

---

## ✅ Verificação Após Executar

Execute o script de verificação:

```bash
python3 testes/verificar_todas_tabelas_banco_novo.py
```

**Esperado:**
- ✅ Tabelas existentes: 30+ (ao invés de 5)
- ✅ `DOCUMENTO_ADUANEIRO` deve aparecer como existente
- ✅ Schemas (comunicacao, ia, legislacao, auditoria) devem ter tabelas

---

## 🎯 Recomendação

**Use a Opção 1 (SQL Server Management Studio)** porque:
- ✅ Interface visual fácil
- ✅ Mostra erros claramente
- ✅ Permite executar em partes se necessário
- ✅ Pode verificar tabelas criadas no Object Explorer

---

## 📝 Checklist

- [ ] Abrir SQL Server Management Studio
- [ ] Conectar ao servidor SQL
- [ ] Abrir arquivo `scripts/criar_banco_maike_completo.sql`
- [ ] Executar script (F5)
- [ ] Verificar mensagens de sucesso
- [ ] Executar `python3 testes/verificar_todas_tabelas_banco_novo.py`
- [ ] Confirmar que `DOCUMENTO_ADUANEIRO` foi criada

---

**Última atualização:** 08/01/2026


