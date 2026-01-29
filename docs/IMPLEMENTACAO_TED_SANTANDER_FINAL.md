# 🏦 Implementação TED Santander - Documentação Completa

**Data:** 12/01/2026  
**Status:** ✅ **COMPLETA E TESTADA**

---

## 📋 Resumo Executivo

Implementação completa de transferências TED via API de Pagamentos do Santander, totalmente isolada da API de Extratos existente. A implementação foi testada com sucesso no ambiente sandbox.

**Funcionalidades Implementadas:**
- ✅ Criação e listagem de workspaces
- ✅ Iniciar transferências TED
- ✅ Efetivar transferências TED
- ✅ Consultar status de TEDs
- ✅ Listar TEDs realizadas
- ✅ Suporte a certificados .pfx para mTLS
- ✅ Validações completas (CPF/CNPJ, descrição, workspace)

---

## 🎯 Arquitetura

### Isolamento Completo

A implementação está **100% isolada** da API de Extratos:

**APIs Separadas:**
- `SantanderExtratoAPI` (`utils/santander_api.py`) - Extratos e saldos
- `SantanderPaymentsAPI` (`utils/santander_payments_api.py`) - TED, PIX, Boleto

**Configurações Separadas:**
- Extratos: `SANTANDER_CLIENT_ID`, `SANTANDER_CLIENT_SECRET`, `SANTANDER_CERT_FILE`, `SANTANDER_KEY_FILE`
- Pagamentos: `SANTANDER_PAYMENTS_CLIENT_ID`, `SANTANDER_PAYMENTS_CLIENT_SECRET`, `SANTANDER_PAYMENTS_CERT_FILE`, `SANTANDER_PAYMENTS_KEY_FILE`

**Tokens Separados:**
- Cada API mantém seu próprio token OAuth2
- Tokens não interferem entre si

### Estrutura de Arquivos

```
utils/
├── santander_api.py              # API de Extratos (existente)
└── santander_payments_api.py     # API de Pagamentos (NOVO)

services/
├── santander_service.py          # Serviço de Extratos (existente)
└── santander_payments_service.py # Serviço de Pagamentos (NOVO)

services/agents/
└── santander_agent.py            # Agent unificado (atualizado)
```

---

## 🐛 Erros Encontrados e Soluções

### 1. ❌ Erro: Descrição do Workspace > 30 caracteres

**Problema:**
```
400 Bad Request
"_message": "A Descrição deve ter no máximo 30 caracteres"
```

**Causa:**
- Descrição padrão `"Workspace PAYMENTS criado via mAIke"` tinha 36 caracteres
- API do Santander limita descrição a 30 caracteres

**Solução:**
```python
# Limitar descrição a 30 caracteres
descricao_final = description or f"Workspace {tipo}"
if len(descricao_final) > 30:
    descricao_final = descricao_final[:30]
```

**Arquivo:** `services/santander_payments_service.py` (linha ~218)

---

### 2. ❌ Erro: CPF Inválido

**Problema:**
```
400 Bad Request
"_message": "Número de documento do recebedor inválido"
```

**Causa:**
- CPF de teste `12345678901` não passa na validação da API
- API valida formato e dígitos verificadores

**Solução:**
```python
# Validar formato básico de CPF
if len(cpf_cnpj_limpo) == 11:
    doc_type = "CPF"
    # Não pode ser todos iguais
    if len(set(cpf_cnpj_limpo)) == 1:
        return erro("CPF inválido")
```

**Arquivo:** `services/santander_payments_service.py` (linha ~403)

**CPF válido para teste:** `00993804713` ✅

---

### 3. ❌ Erro: Workspace Errado Sendo Usado

**Problema:**
- Workspace criado: `1f625459-b4d1-4a1f-9e61-2ff5a75eb665` (PAYMENTS)
- Workspace usado: `d8bb7199-aaba-49ac-bb59-3f8bd5582ad0` (DIGITAL_CORBAN)

**Causa:**
- `_verificar_workspace()` pegava o primeiro workspace da lista
- Não priorizava workspaces PAYMENTS

**Solução:**
```python
# Priorizar workspace PAYMENTS com bankTransferPaymentsActive=true
for ws in workspaces['_content']:
    ws_type = ws.get('type', '')
    bank_transfer_active = ws.get('bankTransferPaymentsActive', False)
    if ws_type == 'PAYMENTS' and bank_transfer_active:
        return ws.get('id')
```

**Arquivo:** `services/santander_payments_service.py` (linha ~82)

**Recomendação:** Configure `SANTANDER_WORKSPACE_ID` no `.env` para garantir uso do workspace correto.

---

### 4. ❌ Erro: Certificados mTLS Não Configurados

**Problema:**
```
403 Forbidden
SSL: CERTIFICATE_VERIFY_FAILED
```

**Causa:**
- Certificados não encontrados nos caminhos configurados
- Fallback para certificados genéricos não funcionando

**Solução:**
- Adicionado suporte a arquivos `.pfx` (igual ao Banco do Brasil)
- Fallback automático: `SANTANDER_PAYMENTS_CERT_FILE` → `SANTANDER_CERT_FILE`

**Arquivo:** `utils/santander_payments_api.py` (método `_extrair_pfx_para_pem`)

**Configuração:**
```env
# Opção 1: Certificados separados
SANTANDER_PAYMENTS_CERT_FILE=/path/to/cert.pem
SANTANDER_PAYMENTS_KEY_FILE=/path/to/key.pem

# Opção 2: Arquivo .pfx (RECOMENDADO)
SANTANDER_PAYMENTS_CERT_PATH=/path/to/certificado.pfx
SANTANDER_PFX_PASSWORD=senha001

# Opção 3: Usar certificados do Extrato (fallback)
# Deixe vazio e use SANTANDER_CERT_FILE/SANTANDER_KEY_FILE
```

---

### 5. ❌ Erro: Logs Insuficientes para Debug

**Problema:**
- Erros 400/403 sem detalhes da resposta da API
- Difícil identificar o problema

**Solução:**
```python
# Log da resposta ANTES de raise_for_status
if response.status_code >= 400:
    logger.error(f"❌ Erro HTTP {response.status_code}")
    logger.error(f"📥 Resposta completa (texto): {response.text[:1000]}")
    try:
        error_json = response.json()
        logger.error(f"📥 Resposta completa (JSON): {json.dumps(error_json, indent=2)}")
    except:
        pass
```

**Arquivo:** `utils/santander_payments_api.py` (métodos `criar_workspace` e `iniciar_ted`)

---

## 📝 Lições Aprendidas

### ✅ O Que Fazer

1. **Sempre validar limites da API antes de enviar**
   - Descrição: 30 caracteres
   - CPF: formato válido
   - Campos obrigatórios

2. **Logs detalhados são essenciais**
   - Logar body antes de enviar
   - Logar resposta completa em caso de erro
   - Logar status codes intermediários

3. **Testar com dados válidos**
   - CPF válido para teste: `00993804713`
   - Workspace correto configurado no `.env`
   - Certificados existentes e válidos

4. **Priorizar workspaces corretos**
   - PAYMENTS com `bankTransferPaymentsActive=true`
   - Configurar `SANTANDER_WORKSPACE_ID` no `.env`

5. **Suporte a múltiplos formatos de certificado**
   - `.pfx` (mais comum)
   - `.pem` + `.key` separados
   - Fallback para certificados genéricos

### ❌ O Que NÃO Fazer

1. **Não assumir formatos sem validar**
   - Descrição pode ter limite de caracteres
   - CPF precisa ser válido, não apenas 11 dígitos
   - Workspace precisa ter TED ativado

2. **Não usar primeiro workspace da lista**
   - Pode não ter TED ativado
   - Pode ser de tipo diferente (DIGITAL_CORBAN vs PAYMENTS)

3. **Não confiar apenas em mensagens de erro genéricas**
   - Sempre logar resposta completa da API
   - Verificar `_errors` array na resposta JSON

4. **Não esquecer de validar dados antes de enviar**
   - CPF/CNPJ: formato e validação básica
   - Descrição: limite de caracteres
   - Workspace: tipo e configurações

---

## 🚀 Passos para Produção

### 1. Credenciais de Produção

**No Portal de Desenvolvedor do Santander:**
1. Acesse: https://developer.santander.com.br
2. Crie uma nova aplicação para **Pagamentos** (separada da de Extratos)
3. Obtenha:
   - `Client ID` de produção
   - `Client Secret` de produção

**Configure no `.env`:**
```env
# ==========================================
# SANTANDER - PAGAMENTOS (PRODUÇÃO)
# ==========================================
SANTANDER_PAYMENTS_BASE_URL=https://trust-open.api.santander.com.br
SANTANDER_PAYMENTS_TOKEN_URL=https://trust-open.api.santander.com.br/auth/oauth/v2/token

# Credenciais de PRODUÇÃO
SANTANDER_PAYMENTS_CLIENT_ID=seu_client_id_producao
SANTANDER_PAYMENTS_CLIENT_SECRET=seu_client_secret_producao

# Certificados de PRODUÇÃO (mTLS obrigatório)
SANTANDER_PAYMENTS_CERT_PATH=/path/to/certificado_producao.pfx
SANTANDER_PFX_PASSWORD=senha_do_certificado

# Workspace de PRODUÇÃO
SANTANDER_WORKSPACE_ID=workspace_id_producao
```

---

### 2. Certificados mTLS de Produção

**Requisitos:**
- Certificado ICP-Brasil tipo A1
- Válido e não expirado
- Com chave privada

**Opções:**
1. **Arquivo .pfx** (RECOMENDADO):
   ```env
   SANTANDER_PAYMENTS_CERT_PATH=/path/to/certificado.pfx
   SANTANDER_PFX_PASSWORD=senha
   ```

2. **Certificado e chave separados**:
   ```env
   SANTANDER_PAYMENTS_CERT_FILE=/path/to/cert.pem
   SANTANDER_PAYMENTS_KEY_FILE=/path/to/key.pem
   ```

**⚠️ IMPORTANTE:**
- Certificados de produção são diferentes dos de sandbox
- Mantenha certificados seguros (não commitar no git)
- Configure permissões adequadas (chmod 600)

---

### 3. Criar Workspace de Produção

**Via Chat:**
```
"criar workspace santander agencia 0001 conta 130392838 tipo PAYMENTS"
```

**Ou via API diretamente:**
- Use o Postman collection de produção
- Ou configure manualmente no portal

**⚠️ IMPORTANTE:**
- Workspace de produção é diferente do sandbox
- Configure `bankTransferPaymentsActive=true` para TED
- Anote o `workspace_id` retornado

**Configure no `.env`:**
```env
SANTANDER_WORKSPACE_ID=workspace_id_producao
```

---

### 4. Testar em Produção (Cuidado!)

**⚠️ ATENÇÃO: Em produção, TEDs movimentam dinheiro real!**

**Recomendações:**
1. **Teste com valores mínimos primeiro**
   - Ex: R$ 0,01 ou R$ 1,00
   - Para conta de teste própria

2. **Valide todos os dados antes**
   - CPF/CNPJ válidos
   - Conta destino correta
   - Valor correto

3. **Use em horário comercial**
   - TEDs podem ter horário de processamento
   - Verifique horários da API

4. **Monitore logs cuidadosamente**
   - Verifique status de cada TED
   - Confirme com extrato bancário

---

### 5. Checklist de Produção

**Antes de ativar em produção:**

- [ ] Credenciais de produção configuradas no `.env`
- [ ] Certificados mTLS de produção configurados e válidos
- [ ] Workspace de produção criado e configurado
- [ ] `SANTANDER_WORKSPACE_ID` configurado no `.env`
- [ ] Testado com valor mínimo (R$ 0,01)
- [ ] Validado extrato bancário após teste
- [ ] Logs configurados e monitorados
- [ ] Backup de certificados e credenciais
- [ ] Documentação atualizada
- [ ] Equipe treinada no uso

---

## 📚 Referências

**Documentação Oficial:**
- https://developer.santander.com.br/api/user-guide/ted-transfers
- https://developer.santander.com.br/api/user-guide/workspaces

**Arquivos do Projeto:**
- `utils/santander_payments_api.py` - Cliente da API
- `services/santander_payments_service.py` - Serviço de negócio
- `services/agents/santander_agent.py` - Agent unificado
- `services/tool_definitions.py` - Definições de tools
- `services/tool_router.py` - Roteamento de tools

**Documentação Relacionada:**
- `docs/EXPLICACAO_WORKSPACE_E_AUTENTICACAO.md` - Workspaces e autenticação
- `docs/TESTES_SEGUROS_TED_SANTANDER.md` - Testes no sandbox
- `docs/UX_TED_SANTANDER.md` - Experiência do usuário

---

## 🔧 Troubleshooting

### Problema: 403 Forbidden

**Possíveis causas:**
1. Certificados mTLS não configurados
2. Certificados inválidos ou expirados
3. Credenciais (Client ID/Secret) incorretas
4. Token OAuth2 inválido

**Solução:**
1. Verifique certificados: `ls -la /path/to/certificado.pfx`
2. Verifique credenciais no `.env`
3. Verifique logs para detalhes do erro
4. Teste conexão com certificados

### Problema: 400 Bad Request

**Possíveis causas:**
1. Descrição > 30 caracteres
2. CPF/CNPJ inválido
3. Campos obrigatórios faltando
4. Formato de dados incorreto

**Solução:**
1. Verifique logs para detalhes do erro
2. Valide CPF/CNPJ antes de enviar
3. Verifique formato de agência/conta (strings)
4. Verifique workspace tem TED ativado

### Problema: Workspace Errado

**Possíveis causas:**
1. `SANTANDER_WORKSPACE_ID` não configurado
2. Workspace não tem `bankTransferPaymentsActive=true`
3. Workspace de tipo errado (DIGITAL_CORBAN vs PAYMENTS)

**Solução:**
1. Configure `SANTANDER_WORKSPACE_ID` no `.env`
2. Liste workspaces: `"listar workspaces do santander"`
3. Verifique tipo e configurações do workspace
4. Crie novo workspace se necessário

---

## 📊 Status da Implementação

**✅ Completo:**
- [x] API de Pagamentos isolada
- [x] Suporte a certificados .pfx
- [x] Criação de workspaces
- [x] Iniciar TED
- [x] Efetivar TED
- [x] Consultar TED
- [x] Listar TEDs
- [x] Validações completas
- [x] Logs detalhados
- [x] Mensagens de erro claras
- [x] Testes no sandbox

**🔄 Próximos Passos (Opcional):**
- [ ] Integração com conciliação bancária
- [ ] Histórico de TEDs no SQL Server
- [ ] Notificações de status de TED
- [ ] Relatórios de transferências

---

**Última atualização:** 12/01/2026  
**Versão:** 1.0.0
