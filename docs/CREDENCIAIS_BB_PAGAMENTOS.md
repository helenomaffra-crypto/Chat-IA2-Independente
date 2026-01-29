# Credenciais para API de Pagamentos em Lote - Banco do Brasil

## ⚠️ IMPORTANTE

**Cada API do Banco do Brasil tem credenciais SEPARADAS (não há fallback):**
- **API de Extratos**: Usa `BB_CLIENT_ID`, `BB_CLIENT_SECRET`, `BB_DEV_APP_KEY`
- **API de Pagamentos em Lote**: Usa `BB_PAYMENTS_CLIENT_ID`, `BB_PAYMENTS_CLIENT_SECRET`, `BB_PAYMENTS_DEV_APP_KEY`

## Configuração no .env

### Credenciais Obrigatórias para Pagamentos

```env
# API de Pagamentos em Lote (OBRIGATÓRIO - credenciais separadas)
BB_PAYMENTS_CLIENT_ID=eyJpZCI6IjVmYWYwM2MtMzFkNC00IiwiY29kaWdvUHVibGljYWRvciI6MCwiY29kaWdvU29mdHdhcmUiOjE2ODEyMCwic2VxdWVuY2lhbEluc3RhbGFjYW8iOjF9
BB_PAYMENTS_CLIENT_SECRET=eyJpZCI6IjhmNDQ3NGEtZDA0NC00YSIsImNvZGlnb1B1YmxpY2Fkb3IiOjAsImNvZGlnb1NvZnR3YXJlIjoxNjgxMjAsInNlcXVlbmNpYWxJbnN0YWxhY2FvIjoxLCJzZXF1ZW5jaWFsQ3JlZGVuY2lhbCI6MSwiYW1iaWVudGUiOiJob21vbG9nYWNhbyIsImlhdCI6MTc2ODMxNjY3MTkyNn0
BB_PAYMENTS_DEV_APP_KEY=1f8386d110934639a2790912c5bba906
BB_PAYMENTS_BASIC_AUTH=ZXlKcFpDSTZJalZtWVdZd00yTXRNekZrTkMwMElpd2lZMjlrYVdkdlVIVmliR2xqWVdSdmNpSTZNQ3dpWTI5a2FXZHZVMjltZEhkaGNtVWlPakUyT0RFeU1Dd2ljMlZ4ZFdWdVkybGhiRWx1YzNSaGJHRmpZVzhpT2pGOTpleUpwWkNJNklqaG1ORFEzTkdFdFpEQTBOQzAwWVNJc0ltTnZaR2xuYjFCMVlteHBZMkZrYjNJaU9qQXNJbU52WkdsbmIxTnZablIzWVhKbElqb3hOamd4TWpBc0luTmxjWFZsYm1OcFlXeEpibk4wWVd4aFkyRnZJam94TENKelpYRjFaVzVqYVdGc1EzSmxaR1Z1WTJsaGJDSTZNU3dpWVcxaWFXVnVkR1VpT2lKb2IyMXZiRzluWVdOaGJ5SXNJbWxoZENJNk1UYzJPRE14TmpZM01Ua3lObjA=  # Opcional (do arquivo "basic=")
```

### Credenciais para Extratos (separadas)

```env
# API de Extratos (separadas)
BB_CLIENT_ID=seu_client_id_extratos
BB_CLIENT_SECRET=seu_client_secret_extratos
BB_DEV_APP_KEY=sua_app_key_extratos
BB_BASIC_AUTH=seu_basic_auth_extratos_base64  # Opcional
```

## Mapeamento do Arquivo de Credenciais

Do arquivo `.secure/certificados_bb/credenciais-apl246367.txt`:

| Campo do Arquivo | Variável .env | Obrigatório | Descrição |
|------------------|---------------|-------------|-----------|
| `appKey` | `BB_PAYMENTS_DEV_APP_KEY` | ✅ Sim | Chave da aplicação (gw-dev-app-key) |
| `clientID` | `BB_PAYMENTS_CLIENT_ID` | ✅ Sim | Client ID OAuth2 |
| `clientSecret` | `BB_PAYMENTS_CLIENT_SECRET` | ✅ Sim | Client Secret OAuth2 |
| `basic` | `BB_PAYMENTS_BASIC_AUTH` | ⚠️ Opcional | Basic Auth pré-codificado (acelera autenticação) |
| `registrationAccessToken` | ❌ Não usado | ❌ Não | Usado apenas no registro inicial da aplicação |

## Sobre registrationAccessToken

O `registrationAccessToken` **NÃO é necessário** para autenticação OAuth2 nas chamadas da API. Ele é usado apenas durante o registro inicial da aplicação no portal do BB. Para uso normal da API, você precisa apenas de:

- ✅ `clientID` → `BB_PAYMENTS_CLIENT_ID`
- ✅ `clientSecret` → `BB_PAYMENTS_CLIENT_SECRET`
- ✅ `appKey` → `BB_PAYMENTS_DEV_APP_KEY`
- ⚠️ `basic` → `BB_PAYMENTS_BASIC_AUTH` (opcional, mas recomendado - acelera autenticação)

## Variáveis de Ambiente

### Para API de Pagamentos (OBRIGATÓRIO)

- `BB_PAYMENTS_CLIENT_ID`: Client ID específico para pagamentos (obrigatório)
- `BB_PAYMENTS_CLIENT_SECRET`: Client Secret específico para pagamentos (obrigatório)
- `BB_PAYMENTS_DEV_APP_KEY`: App Key específica para pagamentos (obrigatório)
- `BB_PAYMENTS_BASIC_AUTH`: Basic Auth pré-codificado (opcional - do arquivo "basic=")

### Para API de Extratos (separadas)

- `BB_CLIENT_ID`: Client ID para extratos (separado)
- `BB_CLIENT_SECRET`: Client Secret para extratos (separado)
- `BB_DEV_APP_KEY`: App Key para extratos (separado)
- `BB_BASIC_AUTH`: Basic Auth para extratos (opcional)

## Ambiente

- `BB_PAYMENTS_ENVIRONMENT`: `sandbox` (padrão) ou `production` - **Específico para API de Pagamentos**
- `BB_ENVIRONMENT`: `sandbox` ou `production` - **Fallback genérico** (usado pela API de Extratos)

**⚠️ IMPORTANTE:** 
- Se `BB_PAYMENTS_ENVIRONMENT` estiver configurado, será usado para Pagamentos
- Se não estiver, usa `BB_ENVIRONMENT` como fallback
- Isso permite ter Extratos em produção e Pagamentos em sandbox simultaneamente

## URLs

As URLs são configuradas automaticamente baseadas no ambiente:

- **Sandbox**: 
  - Token: `https://oauth.hm.bb.com.br/oauth/token` ✅ (conforme documentação oficial OAuth 2.0 do BB)
  - API: `https://homologa-api-ip.bb.com.br:7144/pagamentos-lote/v1` ✅ (conforme documentação oficial)
  - Variáveis opcionais para sobrescrever:
    - `BB_PAYMENTS_TOKEN_URL`: URL do token (opcional)
    - `BB_PAYMENTS_BASE_URL`: URL base da API (opcional)
- **Produção**:
  - Token: `https://oauth.bb.com.br/oauth/token`
  - API: `https://api.bb.com.br/pagamentos-lote/v1`

## Exemplo de Configuração Completa

```env
# ========== API DE EXTRATOS ==========
BB_CLIENT_ID=eyJpZCI6IjVmYWYwM2MtMzFkNC00Ii...
BB_CLIENT_SECRET=eyJpZCI6IjhmNDQ3NGEtZDA0NC00YS...
BB_DEV_APP_KEY=1f8386d110934639a2790912c5bba906
BB_BASIC_AUTH=ZXlKcFpDSTZJalZtWVdZd00yTXRNekZrTkMwMElpd2lZMjlrYVdkdlVIVmliR2xqWVdSdmNpSTZNQ3dpWTI5a2FXZHZVMjltZEhkaGNtVWlPakUyT0RFeU1Dd2ljMlZ4ZFdWdVkybGhiRWx1YzNSaGJHRmpZVzhpT2pGOTpleUpwWkNJNklqaG1ORFEzTkdFdFpEQTBOQzAwWVNJc0ltTnZaR2xuYjFCMVlteHBZMkZrYjNJaU9qQXNJbU52WkdsbmIxTnZablIzWVhKbElqb3hOamd4TWpBc0luTmxjWFZsYm1OcFlXeEpibk4wWVd4aFkyRnZJam94TENKelpYRjFaVzVqYVdGc1EzSmxaR1Z1WTJsaGJDSTZNU3dpWVcxaWFXVnVkR1VpT2lKb2IyMXZiRzluWVdOaGJ5SXNJbWxoZENJNk1UYzJPRE14TmpZM01Ua3lObjA=

# ========== API DE PAGAMENTOS EM LOTE ==========
BB_PAYMENTS_CLIENT_ID=eyJpZCI6IjVmYWYwM2MtMzFkNC00Ii...  # Credenciais SEPARADAS
BB_PAYMENTS_CLIENT_SECRET=eyJpZCI6IjhmNDQ3NGEtZDA0NC00YS...  # Credenciais SEPARADAS
BB_PAYMENTS_DEV_APP_KEY=1f8386d110934639a2790912c5bba906  # App Key SEPARADA
BB_PAYMENTS_BASIC_AUTH=ZXlKcFpDSTZJalZtWVdZd00yTXRNekZrTkMwMElpd2lZMjlrYVdkdlVIVmliR2xqWVdSdmNpSTZNQ3dpWTI5a2FXZHZVMjltZEhkaGNtVWlPakUyT0RFeU1Dd2ljMlZ4ZFdWdVkybGhiRWx1YzNSaGJHRmpZVzhpT2pGOTpleUpwWkNJNklqaG1ORFEzTkdFdFpEQTBOQzAwWVNJc0ltTnZaR2xuYjFCMVlteHBZMkZrYjNJaU9qQXNJbU52WkdsbmIxTnZablIzWVhKbElqb3hOamd4TWpBc0luTmxjWFZsYm1OcFlXeEpibk4wWVd4aFkyRnZJam94TENKelpYRjFaVzVqYVdGc1EzSmxaR1Z1WTJsaGJDSTZNU3dpWVcxaWFXVnVkR1VpT2lKb2IyMXZiRzluWVdOaGJ5SXNJbWxoZENJNk1UYzJPRE14TmpZM01Ua3lObjA=  # Do arquivo "basic="

# Ambiente
BB_ENVIRONMENT=sandbox
```

## Notas Importantes

1. **Cada API tem credenciais SEPARADAS** - Não há fallback. Configure ambas separadamente
2. **Scopes diferentes** - A API de Extratos usa `extrato-info`, a de Pagamentos usa `pagamento-lote`
3. **App Keys diferentes** - Cada aplicação no portal tem sua própria App Key
4. **Basic Auth opcional** - Se fornecer `BB_PAYMENTS_BASIC_AUTH`, será usado diretamente (mais rápido)
5. **registrationAccessToken não é necessário** - Usado apenas no registro inicial, não nas chamadas da API

## Verificação

Para verificar se as credenciais estão configuradas corretamente:

```bash
python3 testes/test_bb_pagamento_lote.py
```

Este teste verifica:
- ✅ Importação dos módulos
- ✅ Configuração da API
- ✅ Inicialização do Serviço
- ✅ Inicialização do Agent
- ✅ Definições de Tools
- ✅ Tool Router
