# 🏦 Integração com Banco do Brasil - API de Extratos

**Data:** 06/01/2026  
**API:** Extratos API v1.0  
**Portal:** https://developers.bb.com.br

---

## 📋 Índice

- [O que a API Exige](#-o-que-a-api-exige)
- [O que Você Precisa Solicitar](#-o-que-você-precisa-solicitar)
- [Configuração e Credenciais](#-configuração-e-credenciais)
- [Autenticação OAuth 2.0](#-autenticação-oauth-20)
- [Endpoint e Parâmetros](#-endpoint-e-parâmetros)
- [Formato de Dados](#-formato-de-dados)
- [Exemplo de Implementação](#-exemplo-de-implementação)
- [Comparação com Santander](#-comparação-com-santander)

---

## 🔑 O que a API Exige

### 1. **Autenticação OAuth 2.0 (Client Credentials)**

- **Tipo**: OAuth 2.0 Client Credentials Flow
- **Token URL**: 
  - Homologação: `https://oauth.hm.bb.com.br/oauth/token`
  - Produção: `https://oauth.bb.com.br/oauth/token` (verificar no portal do desenvolvedor)
- **Scope necessário**: `extrato-info`
- **Descrição**: Permite acionar recursos de consultas relativas à extrato
- **mTLS**: ⚠️ **IMPORTANTE**: A API de Extratos **NÃO requer mTLS** (diferente de outras APIs do BB como Pagamentos). Apenas OAuth 2.0 Client Credentials é necessário.

### 2. **Chave de Aplicativo (Obrigatória)**

- **Parâmetro**: `gw-dev-app-key` (query parameter)
- **Onde obter**: Portal do Desenvolvedor do Banco do Brasil
- **Descrição**: Chave de acesso do aplicativo do desenvolvedor
- **Uso**: Identificação do aplicativo em cada requisição
- **Obrigatório**: ✅ Sim (deve ser enviado em TODAS as requisições)

### 3. **Credenciais OAuth**

Para obter o token de acesso, você precisa de:
- **Client ID** (obtido no Portal do Desenvolvedor)
- **Client Secret** (obtido no Portal do Desenvolvedor)

---

## 📝 O que Você Precisa Solicitar

### 1. **Cadastro no Portal do Desenvolvedor BB**

**Site:** https://developers.bb.com.br

**Passos:**
1. Criar conta de desenvolvedor
2. Registrar aplicativo
3. Solicitar acesso à API de Extratos
4. Obter credenciais:
   - `gw-dev-app-key` (chave do aplicativo)
   - Client ID (para OAuth)
   - Client Secret (para OAuth)

### 2. **Solicitar Permissão para a API**

- **API**: Extratos API
- **Scope**: `extrato-info`
- **Descrição**: Permite acionar recursos de consultas relativas à extrato

### 3. **Ambiente de Teste (Recomendado)**

**URLs de Homologação:**
- `https://api.sandbox.bb.com.br/extratos/v1`
- `https://api.hm.bb.com.br/extratos/v1`
- `https://api-extratos.hm.bb.com.br/extratos/v1`

**Token URL (Homologação):**
- `https://oauth.hm.bb.com.br/oauth/token`

### 4. **Ambiente de Produção (Quando Estiver Pronto)**

**URL de Produção:**
- `https://api-extratos.bb.com.br/extratos/v1`

**Requisitos:**
- Aplicativo aprovado pelo BB
- Testes concluídos em homologação
- Solicitação de acesso à produção

---

## ⚙️ Configuração e Credenciais

### Variáveis de Ambiente Necessárias

```env
# Banco do Brasil - Extratos API
BB_DEV_APP_KEY=sua_gw_dev_app_key_aqui
BB_CLIENT_ID=seu_client_id_oauth
BB_CLIENT_SECRET=seu_client_secret_oauth
BB_BASE_URL=https://api-extratos.bb.com.br/extratos/v1
BB_TOKEN_URL=https://oauth.hm.bb.com.br/oauth/token
BB_ENVIRONMENT=production  # ou sandbox

# Contas Padrão (Opcional - para facilitar consultas)
BB_TEST_AGENCIA=1505  # Agência padrão (sem dígito verificador)
BB_TEST_CONTA=1348   # Conta padrão (sem dígito verificador)
BB_TEST_CONTA_2=43344 # Segunda conta (opcional - mesma agência)
```

### Checklist de Solicitação

- [ ] Criar conta no Portal do Desenvolvedor BB (https://developers.bb.com.br)
- [ ] Registrar aplicativo no portal
- [ ] Solicitar acesso à API de Extratos (scope: `extrato-info`)
- [ ] Obter `gw-dev-app-key`
- [ ] Obter Client ID (OAuth)
- [ ] Obter Client Secret (OAuth)
- [ ] Testar em ambiente de homologação
- [ ] Solicitar acesso à produção (quando estiver pronto)

---

## 🔐 Autenticação OAuth 2.0

### Fluxo de Autenticação

```
1. Obter Token de Acesso
   POST https://oauth.hm.bb.com.br/oauth/token
   Headers:
     Content-Type: application/x-www-form-urlencoded
   Body:
     grant_type=client_credentials
     scope=extrato-info
   Authorization:
     Basic base64(client_id:client_secret)

2. Usar Token nas Requisições
   GET /conta-corrente/agencia/{agencia}/conta/{conta}
   Headers:
     Authorization: Bearer {access_token}
     gw-dev-app-key: {gw-dev-app-key}
```

### Exemplo de Obtenção de Token

```python
import requests
import base64

def obter_token_bb(client_id, client_secret):
    """Obtém token de acesso OAuth 2.0 do Banco do Brasil"""
    token_url = "https://oauth.hm.bb.com.br/oauth/token"
    
    # Credenciais em base64
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    data = {
        "grant_type": "client_credentials",
        "scope": "extrato-info"
    }
    
    response = requests.post(token_url, headers=headers, data=data)
    response.raise_for_status()
    
    token_data = response.json()
    return token_data["access_token"]
```

---

## 🌐 Endpoints e mTLS

### Endpoints Disponíveis

A API de Extratos do Banco do Brasil oferece diferentes endpoints conforme o ambiente e uso de mTLS (conforme especificação OpenAPI):

| Ambiente | mTLS | Endpoint | Quando Usar |
|----------|------|----------|-------------|
| **Homologação** | ❌ Sem mTLS | `https://api.sandbox.bb.com.br/extratos/v1` | Sandbox padrão (mais simples) |
| **Homologação 2** | ❌ Sem mTLS | `https://api.hm.bb.com.br/extratos/v1` | Homologação alternativa |
| **Homologação 3** | ✅ Com mTLS | `https://api-extratos.hm.bb.com.br/extratos/v1` | Testes com certificado |
| **Produção** | ✅ Com mTLS | `https://api-extratos.bb.com.br/extratos/v1` | Ambiente de produção |

### Configuração Automática

O código detecta automaticamente qual endpoint usar:

- **Homologação sem certificado**: Usa `api.sandbox.bb.com.br` (sandbox padrão, mais simples para testes)
- **Homologação com certificado**: Usa `api-extratos.hm.bb.com.br` (se `BB_CERT_PATH` configurado)
- **Produção**: Sempre usa `api-extratos.bb.com.br` (sempre requer mTLS)

Você pode sobrescrever o endpoint padrão configurando `BB_BASE_URL` no `.env`.

### Certificados mTLS

⚠️ **IMPORTANTE**: 
- **Homologação**: mTLS é **opcional** - você pode testar sem certificado
- **Produção**: mTLS pode ser **obrigatório** dependendo da API
  - **API de Extratos**: Conforme especificação OpenAPI, produção usa endpoint `api-extratos.bb.com.br` que pode requerer mTLS
  - **Outras APIs**: Geralmente requerem mTLS em produção
  - **Certificado**: Deve ser ICP-Brasil tipo A1 (e-CNPJ preferencialmente)
  - **Envio**: Envie a cadeia do certificado no portal do BB (menu Certificado)

Para configurar certificados (opcional em homologação, obrigatório em produção):

```env
# Opção 1: Certificado combinado (cert + key no mesmo arquivo)
BB_CERT_PATH=/caminho/para/certificado.pem

# Opção 2: Certificado e chave separados
BB_CERT_FILE=/caminho/para/certificado.crt
BB_KEY_FILE=/caminho/para/chave.key
```

### Header de Teste (Homologação)

Para testes em homologação, você pode usar o header `x-br-com-bb-ipa-mciteste`:

```env
BB_TEST_HEADER=valor_conforme_massa_de_testes
```

⚠️ Este header **só deve ser usado em homologação**, não em produção.

---

## 📡 Endpoint e Parâmetros

### Endpoint Principal

```
GET /conta-corrente/agencia/{agencia}/conta/{conta}
```

### Parâmetros de Path (Obrigatórios)

| Parâmetro | Tipo | Descrição | Exemplo |
|-----------|------|-----------|---------|
| `agencia` | string | Número da agência, **sem dígito verificador** | `1505` |
| `conta` | string | Número da conta, **sem dígito verificador** | `1348` |

### Parâmetros de Query

| Parâmetro | Tipo | Obrigatório | Descrição | Exemplo |
|-----------|------|-------------|-----------|---------|
| `gw-dev-app-key` | string | ✅ **SIM** | Chave de acesso do aplicativo | `sua-chave-aqui` |
| `numeroPaginaSolicitacao` | integer | ❌ Não | Número da página (padrão: 1) | `1` |
| `quantidadeRegistroPaginaSolicitacao` | integer | ❌ Não | Registros por página (50-200, padrão: 200) | `200` |
| `dataInicioSolicitacao` | integer | ❌ Não* | Data inicial (formato DDMMAAAA) | `01122025` |
| `dataFimSolicitacao` | integer | ❌ Não* | Data final (formato DDMMAAAA) | `31122025` |

**Notas:**
- `gw-dev-app-key` é **OBRIGATÓRIO** em todas as requisições
- Se `dataInicioSolicitacao` for informado, `dataFimSolicitacao` é obrigatório
- Se `dataFimSolicitacao` for informado, `dataInicioSolicitacao` é obrigatório
- Se nenhuma data for informada, retorna extrato dos **últimos 30 dias**
- Período máximo entre datas: **31 dias**
- Limite máximo para data inicial: **5 anos** a partir da data atual

### Formato de Data

**Formato**: `DDMMAAAA` (inteiro, sem separadores)

**Exemplos:**
- `01122025` = 01/12/2025
- `31122025` = 31/12/2025
- `01012026` = 01/01/2026

---

## 📊 Formato de Dados

### Resposta de Sucesso (200)

```json
{
  "numeroPaginaAtual": 1,
  "quantidadeRegistroPaginaAtual": 100,
  "numeroPaginaAnterior": 0,
  "numeroPaginaProximo": 2,
  "quantidadeTotalPagina": 5,
  "quantidadeTotalRegistro": 1000,
  "listaLancamento": [
    {
      "indicadorTipoLancamento": "1",
      "dataLancamento": 11112022,
      "dataMovimento": 10112022,
      "codigoAgenciaOrigem": 7988,
      "numeroLote": 12345,
      "numeroDocumento": 607984000004010,
      "codigoHistorico": 470,
      "textoDescricaoHistorico": "Transferência enviada",
      "valorLancamento": 120.35,
      "indicadorSinalLancamento": "D",
      "textoInformacaoComplementar": "Tar. agrupadas - ocorrencia 10/11/2022",
      "numeroCpfCnpjContrapartida": 35484829100,
      "indicadorTipoPessoaContrapartida": "F",
      "codigoBancoContrapartida": 341,
      "codigoAgenciaContrapartida": 7894,
      "numeroContaContrapartida": "4010",
      "textoDvContaContrapartida": "X"
    }
  ]
}
```

### Campos Importantes

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `indicadorTipoLancamento` | string | `"1"` = Efetivados, `"2"` = Futuros |
| `dataLancamento` | integer | Data do lançamento (DDMMAAAA) |
| `dataMovimento` | integer | Data do movimento (DDMMAAAA) - para lançamentos retroativos |
| `valorLancamento` | number | Valor em BRL (duas casas decimais) |
| `indicadorSinalLancamento` | string | `"D"` = Débito, `"C"` = Crédito |
| `textoDescricaoHistorico` | string | Descrição do lançamento (máx. 25 caracteres) |
| `numeroCpfCnpjContrapartida` | integer | CPF/CNPJ da contrapartida |
| `indicadorTipoPessoaContrapartida` | string | `"F"` = Física, `"J"` = Jurídica |

### Paginação

- **Máximo por página**: 200 registros
- **Mínimo por página**: 50 registros
- **Padrão**: 200 registros
- **Importante**: O `pagesize` informado na primeira página deve ser mantido nas páginas subsequentes

---

## 💻 Exemplo de Implementação

### Cliente Python Completo

```python
import requests
import base64
from typing import Optional, Dict, Any
from datetime import datetime

class BancoBrasilExtratoAPI:
    """Cliente para API de Extratos do Banco do Brasil"""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        gw_dev_app_key: str,
        environment: str = "sandbox"
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.gw_dev_app_key = gw_dev_app_key
        
        # URLs por ambiente
        if environment == "production":
            self.base_url = "https://api-extratos.bb.com.br/extratos/v1"
            self.token_url = "https://oauth.bb.com.br/oauth/token"  # Verificar no portal
        else:
            self.base_url = "https://api.sandbox.bb.com.br/extratos/v1"
            self.token_url = "https://oauth.hm.bb.com.br/oauth/token"
        
        self._access_token = None
    
    def _obter_token(self) -> str:
        """Obtém token de acesso OAuth 2.0"""
        if self._access_token:
            return self._access_token
        
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}"
        }
        
        data = {
            "grant_type": "client_credentials",
            "scope": "extrato-info"
        }
        
        response = requests.post(self.token_url, headers=headers, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self._access_token = token_data["access_token"]
        return self._access_token
    
    def _formatar_data(self, data: datetime) -> int:
        """Formata data para DDMMAAAA (inteiro)"""
        return int(data.strftime("%d%m%Y"))
    
    def consultar_extrato(
        self,
        agencia: str,
        conta: str,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        pagina: int = 1,
        registros_por_pagina: int = 200
    ) -> Dict[str, Any]:
        """
        Consulta extrato de conta corrente
        
        Args:
            agencia: Número da agência (sem dígito verificador)
            conta: Número da conta (sem dígito verificador)
            data_inicio: Data inicial (opcional, padrão: últimos 30 dias)
            data_fim: Data final (opcional, obrigatório se data_inicio for informado)
            pagina: Número da página (padrão: 1)
            registros_por_pagina: Registros por página (50-200, padrão: 200)
        
        Returns:
            Dict com dados do extrato
        """
        token = self._obter_token()
        
        url = f"{self.base_url}/conta-corrente/agencia/{agencia}/conta/{conta}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        params = {
            "gw-dev-app-key": self.gw_dev_app_key,
            "numeroPaginaSolicitacao": pagina,
            "quantidadeRegistroPaginaSolicitacao": registros_por_pagina
        }
        
        # Adicionar datas se fornecidas
        if data_inicio:
            params["dataInicioSolicitacao"] = self._formatar_data(data_inicio)
        if data_fim:
            params["dataFimSolicitacao"] = self._formatar_data(data_fim)
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def consultar_extrato_periodo(
        self,
        agencia: str,
        conta: str,
        data_inicio: datetime,
        data_fim: datetime
    ) -> list:
        """
        Consulta extrato completo de um período (com paginação automática)
        
        Args:
            agencia: Número da agência
            conta: Número da conta
            data_inicio: Data inicial
            data_fim: Data final
        
        Returns:
            Lista com todos os lançamentos do período
        """
        todos_lancamentos = []
        pagina = 1
        
        while True:
            extrato = self.consultar_extrato(
                agencia=agencia,
                conta=conta,
                data_inicio=data_inicio,
                data_fim=data_fim,
                pagina=pagina
            )
            
            lancamentos = extrato.get("listaLancamento", [])
            todos_lancamentos.extend(lancamentos)
            
            # Verificar se há próxima página
            if extrato.get("numeroPaginaProximo", 0) == 0:
                break
            
            pagina = extrato["numeroPaginaProximo"]
        
        return todos_lancamentos

# Exemplo de uso
if __name__ == "__main__":
    # Configuração
    api = BancoBrasilExtratoAPI(
        client_id="seu_client_id",
        client_secret="seu_client_secret",
        gw_dev_app_key="sua_gw_dev_app_key",
        environment="sandbox"
    )
    
    # Consultar extrato dos últimos 30 dias
    extrato = api.consultar_extrato(
        agencia="1505",
        conta="1348"
    )
    
    # Consultar extrato de um período específico
    from datetime import datetime, timedelta
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=7)
    
    extrato_periodo = api.consultar_extrato(
        agencia="1505",
        conta="1348",
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    
    # Consultar extrato completo (todas as páginas)
    todos_lancamentos = api.consultar_extrato_periodo(
        agencia="1505",
        conta="1348",
        data_inicio=data_inicio,
        data_fim=data_fim
    )
```

---

## ⚖️ Comparação com Santander

| Aspecto | Banco do Brasil | Santander |
|--------|----------------|-----------|
| **Certificado mTLS** | ⚠️ Opcional (homologação sem mTLS disponível) | ✅ Obrigatório (ICP-Brasil tipo A1) |
| **Autenticação** | OAuth2 Client Credentials | OAuth2 mTLS |
| **Chave de aplicativo** | `gw-dev-app-key` (obrigatória) | Client ID/Secret |
| **Portal** | https://developers.bb.com.br | Portal do Desenvolvedor Santander |
| **Complexidade** | ✅ Mais simples (homologação sem certificado) | ⚠️ Mais complexa (requer certificado) |
| **Formato de data** | DDMMAAAA (inteiro, sem zeros à esquerda) | ISO 8601 (YYYY-MM-DD) |
| **Paginação** | 50-200 registros/página | Configurável via parâmetros |
| **Período máximo** | 31 dias | 31 dias |
| **Endpoints** | Homologação: 2 opções (com/sem mTLS)<br>Produção: apenas com mTLS | Único endpoint por ambiente |

### Vantagens do Banco do Brasil

✅ **Mais simples em homologação**: Não requer certificado mTLS para testes  
✅ **Autenticação padrão**: OAuth2 Client Credentials (mais comum)  
✅ **Processo mais rápido**: Cadastro mais direto  
✅ **Flexibilidade**: Pode testar sem certificado em homologação

---

## ⚠️ Limitações e Observações

### Limitações da API

1. **Período máximo**: 31 dias entre data inicial e final
2. **Data inicial máxima**: 5 anos a partir da data atual
3. **Registros por página**: Mínimo 50, máximo 200
4. **Sem data**: Retorna últimos 30 dias se nenhuma data for informada
5. **Datas interdependentes**: Se informar uma data, deve informar ambas

### Observações Importantes

- **Agência e conta**: Sem dígito verificador (apenas números)
- **Formato de data**: DDMMAAAA como inteiro (sem separadores)
- **Chave obrigatória**: `gw-dev-app-key` deve ser enviada em TODAS as requisições
- **Token expira**: Implementar renovação automática do token
- **Paginação**: Manter mesmo `pagesize` em todas as páginas

---

## 🔗 Referências

- **Portal do Desenvolvedor**: https://developers.bb.com.br
- **Documentação da API**: (verificar no portal após cadastro)
- **Token URL (Homologação)**: https://oauth.hm.bb.com.br/oauth/token
- **Base URL (Homologação)**: https://api.sandbox.bb.com.br/extratos/v1

---

## 📌 Checklist de Implementação

- [ ] Criar conta no Portal do Desenvolvedor BB
- [ ] Registrar aplicativo
- [ ] Solicitar acesso à API de Extratos
- [ ] Obter `gw-dev-app-key`, Client ID e Client Secret
- [ ] Implementar cliente OAuth 2.0
- [ ] Implementar função de consulta de extrato
- [ ] Implementar paginação automática
- [ ] Testar em ambiente de homologação
- [ ] Tratar erros e exceções
- [ ] Implementar cache de token
- [ ] Solicitar acesso à produção
- [ ] Testar em produção

---

## 🔐 Cadeia Completa de Certificados para APIs mTLS

**Data:** 06/01/2026  
**Importante:** Algumas APIs do Banco do Brasil (como Pagamentos) requerem mTLS (mutual TLS) com cadeia completa de certificados.

### ⚠️ Requisito do Portal BB

O Portal do Banco do Brasil exige que você envie a **cadeia completa de certificados** no formato:
- **Formato**: Certificado X.509 em formato PEM (Base 64)
- **Conteúdo**: Certificado da empresa + Certificados intermediários + Certificado raiz
- **Sem metadados**: Apenas blocos `-----BEGIN CERTIFICATE-----` e `-----END CERTIFICATE-----`

### 📋 Processo Completo de Criação da Cadeia

#### 1. Extrair Certificado da Empresa

```bash
cd /Users/helenomaffra/Chat-IA-Independente/.secure/certificados_bb

# Extrair certificado da empresa do arquivo .pfx
openssl pkcs12 -in "../eCNPJ 4PL (valid 23-03-26) senha001.pfx" \
  -clcerts -nokeys -out certificado_empresa.pem \
  -passin pass:senha001 -legacy
```

**Nota:** Se o OpenSSL 3.0+ der erro, use a flag `-legacy` ou `-provider legacy`.

#### 2. Baixar Certificados Intermediários e Raiz

**O arquivo .pfx geralmente NÃO contém os certificados intermediários.** Você precisa baixá-los:

**Sites para baixar:**
- https://www.gov.br/iti/pt-br/assuntos/repositorio
- https://www.safeweb.com.br/repositorio

**Certificados necessários:**
- **AC SAFEWEB RFB v5** (intermediário que emite o certificado da empresa)
- **AC Raiz Brasileira v5** (raiz que emite o intermediário)

**Salvar em:**
```
/Users/helenomaffra/Chat-IA-Independente/.secure/certificados_bb/
```

#### 3. Validar Certificados Baixados

```bash
cd /Users/helenomaffra/Chat-IA-Independente/.secure/certificados_bb

# Verificar se são certificados válidos
openssl x509 -in AC_SAFEWEB_RFB_v5.crt -noout -subject -issuer
openssl x509 -in ICP-Brasilv5.crt -noout -subject -issuer
```

Cada comando deve mostrar o Subject e Issuer do certificado. Se mostrar erro, o arquivo não é válido.

#### 4. Criar Cadeia Completa (Método Automatizado)

```bash
cd /Users/helenomaffra/Chat-IA-Independente/.secure/certificados_bb
./criar_cadeia_com_arquivos_encontrados.sh
```

Este script:
- Verifica se os certificados são válidos
- Identifica qual é qual (Raiz vs Intermediário)
- Converte para formato PEM
- Cria a cadeia no formato correto (igual ao exemplo do BB)

#### 5. Criar Cadeia Completa (Método Manual)

```bash
cd /Users/helenomaffra/Chat-IA-Independente/.secure/certificados_bb

# Converter certificados para PEM (se necessário)
openssl x509 -in AC_SAFEWEB_RFB_v5.crt -out ac_safeweb_rfb_v5.pem -outform PEM
openssl x509 -in ICP-Brasilv5.crt -out ac_raiz_brasileira_v5.pem -outform PEM

# Criar cadeia completa (formato PEM puro - sem metadados)
rm -f cadeia_completa_para_importacao.pem

# Extrair apenas blocos BEGIN/END CERTIFICATE (sem "Bag Attributes")
awk '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/' certificado_empresa.pem > cadeia_completa_para_importacao.pem
echo "" >> cadeia_completa_para_importacao.pem
awk '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/' ac_safeweb_rfb_v5.pem >> cadeia_completa_para_importacao.pem
echo "" >> cadeia_completa_para_importacao.pem
awk '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/' ac_raiz_brasileira_v5.pem >> cadeia_completa_para_importacao.pem

# Verificar
grep -c "BEGIN CERTIFICATE" cadeia_completa_para_importacao.pem
# Deve retornar: 3
```

#### 6. Verificar Formato da Cadeia

```bash
# Verificar quantos certificados tem
grep -c "BEGIN CERTIFICATE" cadeia_completa_para_importacao.pem
# Deve retornar: 3

# Verificar primeira linha (deve ser BEGIN CERTIFICATE, não "Bag Attributes")
head -1 cadeia_completa_para_importacao.pem
# Deve mostrar: -----BEGIN CERTIFICATE-----

# Verificar estrutura (hierarquia)
openssl crl2pkcs7 -nocrl -certfile cadeia_completa_para_importacao.pem 2>/dev/null | \
  openssl pkcs7 -print_certs -noout -text 2>/dev/null | \
  grep -E "Subject:|Issuer:" | head -6
```

#### 7. Enviar ao Portal BB

1. Acesse: https://app.developers.bb.com.br/#/aplicacoes/[ID_APLICACAO]/certificado/enviar
2. Clique em **"Importar cadeia completa"**
3. Selecione: `cadeia_completa_para_importacao.pem`
4. O Portal BB deve aceitar a cadeia completa (3 certificados)

### ✅ Estrutura Final da Cadeia

A cadeia completa deve conter **3 certificados** na ordem:

1. **Certificado da Empresa** (4PL)
   - Subject: CN=4PL APOIO ADMINISTRATIVO...
   - Issuer: CN=AC SAFEWEB RFB v5

2. **AC SAFEWEB RFB v5** (Intermediário)
   - Subject: CN=AC SAFEWEB RFB v5
   - Issuer: CN=AC Secretaria da Receita Federal do Brasil v4 ou AC Raiz Brasileira v5

3. **AC Raiz Brasileira v5** (Raiz)
   - Subject: CN=Autoridade Certificadora Raiz Brasileira v5
   - Issuer: CN=Autoridade Certificadora Raiz Brasileira v5 (auto-assinado)

### 📁 Arquivos e Scripts Disponíveis

**Localização:** `/Users/helenomaffra/Chat-IA-Independente/.secure/certificados_bb/`

**Scripts úteis:**
- `criar_cadeia_com_arquivos_encontrados.sh` - Cria cadeia completa automaticamente
- `verificar_arquivos.sh` - Valida se os certificados são válidos
- `extrair_pem_limpo.sh` - Extrai apenas certificados PEM (sem metadados)
- `ordenar_cadeia_bb.sh` - Ordena cadeia na hierarquia correta

**Documentação:**
- `COMANDOS_CADEIA_COMPLETA.txt` - Comandos passo a passo
- `INSTRUCOES_FINAIS.txt` - Instruções resumidas
- `ALTERNATIVAS_DOWNLOAD.txt` - Alternativas para baixar certificados

### ⚠️ Problemas Comuns

**Problema:** "O arquivo contém apenas um certificado, envie a cadeia completa"
- **Solução:** Verifique se a cadeia tem 3 certificados: `grep -c "BEGIN CERTIFICATE" cadeia_completa_para_importacao.pem`

**Problema:** Arquivo começa com "Bag Attributes"
- **Solução:** Use `awk '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/'` para extrair apenas os certificados

**Problema:** Certificados intermediários inválidos
- **Solução:** Baixe novamente do site do governo e valide com `openssl x509 -in arquivo.crt -noout -subject`

**Problema:** Site do governo não abre
- **Solução:** Tente:
  - https://www.gov.br/iti/pt-br/assuntos/repositorio (sem /certificados-digital)
  - https://www.safeweb.com.br/repositorio
  - Busca no Google: "AC SAFEWEB RFB v5 download"

### 📝 Exemplo de Cadeia Válida

```
-----BEGIN CERTIFICATE-----
[conteúdo base64 do certificado da empresa]
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
[conteúdo base64 do AC SAFEWEB RFB v5]
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
[conteúdo base64 do AC Raiz Brasileira v5]
-----END CERTIFICATE-----
```

**Importante:** Não deve conter "Bag Attributes" ou outros metadados. Apenas os blocos de certificado.

---

**Última atualização:** 06/01/2026

