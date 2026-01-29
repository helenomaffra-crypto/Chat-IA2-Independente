# 🧪 Testes - Histórico de Documentos Aduaneiros

**Data:** 08/01/2026  
**Status:** ✅ Scripts de Teste Criados

---

## 📋 Scripts Disponíveis

### `test_historico_documentos.py`

Script completo de teste para validar a integração do `DocumentoHistoricoService`.

**Cenários testados:**
1. ✅ Documento novo (primeira consulta)
2. ✅ Mudança de status
3. ✅ Mudança de canal
4. ✅ Sem mudanças (consulta repetida)
5. ✅ Validação de dados gravados no banco

---

## 🚀 Como Executar

### Pré-requisitos

1. **Banco de dados configurado:**
   - SQL Server com tabela `HISTORICO_DOCUMENTO_ADUANEIRO` criada
   - Execute: `scripts/criar_banco_maike_completo.sql`

2. **Variáveis de ambiente:**
   - `.env` configurado com credenciais do SQL Server

### Executar Testes

```bash
# Executar todos os testes
python testes/test_historico_documentos.py

# Ou com output detalhado
python testes/test_historico_documentos.py 2>&1 | tee teste_output.log
```

---

## 📊 O que os Testes Fazem

### Teste 1: Documento Novo

**Objetivo:** Verificar que documento novo não gera mudanças (esperado)

**Passos:**
1. Cria um CE novo
2. Chama `detectar_e_gravar_mudancas()`
3. Verifica que não há mudanças (documento novo)

**Resultado esperado:** ✅ 0 mudanças

---

### Teste 2: Mudança de Status

**Objetivo:** Verificar detecção de mudança de status

**Passos:**
1. Cria uma DI com status "REGISTRADA"
2. Simula mudança para "DESEMBARACADA"
3. Chama `detectar_e_gravar_mudancas()`
4. Verifica que mudança foi detectada

**Resultado esperado:** ✅ Pelo menos 1 mudança detectada

---

### Teste 3: Mudança de Canal

**Objetivo:** Verificar detecção de mudança de canal

**Passos:**
1. Cria uma DUIMP com canal "VERDE"
2. Simula mudança para "AMARELO"
3. Chama `detectar_e_gravar_mudancas()`
4. Verifica que mudança foi detectada

**Resultado esperado:** ✅ Pelo menos 1 mudança detectada

---

### Teste 4: Sem Mudanças

**Objetivo:** Verificar que consulta repetida não gera mudanças

**Passos:**
1. Cria um CCT
2. Consulta novamente com os mesmos dados
3. Chama `detectar_e_gravar_mudancas()`
4. Verifica que não há mudanças

**Resultado esperado:** ✅ 0 mudanças

---

### Teste 5: Validação de Dados

**Objetivo:** Verificar se dados foram gravados no banco

**Passos:**
1. Verifica se tabela `HISTORICO_DOCUMENTO_ADUANEIRO` existe
2. Conta registros de teste
3. Lista últimos registros

**Resultado esperado:** ✅ Tabela existe e tem registros

---

## 📋 Interpretação dos Resultados

### ✅ Todos os Testes Passaram

```
🎉 TODOS OS TESTES PASSARAM!
```

**Significa:**
- Integração está funcionando corretamente
- Histórico está sendo gravado
- Mudanças estão sendo detectadas
- Dados estão no banco

---

### ⚠️ Alguns Testes Falharam

```
⚠️ X teste(s) falharam
```

**Possíveis causas:**
1. **Tabela não existe:**
   - Execute: `scripts/criar_banco_maike_completo.sql`

2. **SQL Server não disponível:**
   - Verifique conexão
   - Verifique credenciais no `.env`

3. **Erro no serviço:**
   - Verifique logs
   - Verifique se `DocumentoHistoricoService` está correto

---

## 🔍 Debug

### Ver Logs Detalhados

```bash
# Executar com debug
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
exec(open('testes/test_historico_documentos.py').read())
"
```

### Verificar Dados no Banco

```sql
-- Ver últimos registros de histórico
SELECT TOP 10
    numero_documento,
    tipo_documento,
    tipo_evento,
    campo_alterado,
    valor_anterior,
    valor_novo,
    data_evento,
    fonte_dados
FROM dbo.HISTORICO_DOCUMENTO_ADUANEIRO
WHERE fonte_dados = 'TESTE'
ORDER BY data_evento DESC
```

---

## 📝 Notas

- **Dados de teste:** Os testes usam `fonte_dados = 'TESTE'` para facilitar limpeza
- **Limpeza:** Você pode limpar dados de teste com:
  ```sql
  DELETE FROM dbo.HISTORICO_DOCUMENTO_ADUANEIRO WHERE fonte_dados = 'TESTE'
  ```
- **Documentos de teste:** Usam números fictícios (não consultam APIs reais)

---

**Última atualização:** 08/01/2026

