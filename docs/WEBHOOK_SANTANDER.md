# 🔔 Webhooks do Santander - Requisitos e Configuração

**Data:** 06/01/2026  
**Fonte:** Documentação do Portal do Desenvolvedor Santander

---

## 📋 Requisitos para Habilitar Webhooks

### 1. **URL do Webhook**

- **Única por chave/recurso**: Cada chave/recurso pode estar associado a uma única URL para recebimento de notificações
- **Múltiplas chaves, mesma URL**: Uma única URL pode ser atribuída a múltiplas chaves/recurso
- **Validação obrigatória**: O Santander realizará uma chamada de validação ao registrar a URL

### 2. **Requisitos Técnicos da URL**

#### ✅ Método GET (Validação)
- A URL **DEVE** responder a requisições **GET** para validação inicial
- O Santander faz uma chamada GET para validar a URL antes de registrar
- Se a validação falhar, o cadastro não será efetuado

#### ✅ Método POST (Notificações)
- A URL **DEVE** aceitar requisições **POST** para receber notificações
- As notificações serão enviadas via POST quando eventos ocorrerem

#### ✅ Categorização CISCO
- A URL **DEVE** estar categorizada na **CISCO** (https://www.talosintelligence.com/)
- A CISCO é uma ferramenta de categorização de URLs usada pelo Santander para segurança
- URLs não categorizadas ou categorizadas como maliciosas serão rejeitadas

#### ✅ Headers Flexíveis
- A URL **DEVE** aceitar chamadas **sem exigir headers específicos**
- Não deve rejeitar requisições que não tenham headers customizados
- Deve ignorar headers enviados pelo banco se não forem críticos

### 3. **Segurança Adicional (Opcional - Recomendado)**

#### 🔒 mTLS (Mutual TLS)
- **Opcional mas recomendado** para aumentar a segurança
- Requer solicitar ao Santander a parte pública do certificado
- O certificado deve ser configurado na aplicação
- Deve ser atualizado conforme necessário (renovação de certificados)

---

## 🔧 Passos para Configuração

### Passo 1: Preparar a URL do Webhook

1. **Criar endpoint na aplicação:**
   ```python
   # Exemplo Flask
   @app.route('/webhook/santander', methods=['GET', 'POST'])
   def webhook_santander():
       if request.method == 'GET':
           # Validação inicial
           return jsonify({'status': 'ok'}), 200
       
       # Receber notificação POST
       data = request.json
       # Processar notificação
       return jsonify({'status': 'received'}), 200
   ```

2. **Garantir que a URL atende aos requisitos:**
   - ✅ Responde a GET (validação)
   - ✅ Responde a POST (notificações)
   - ✅ Não exige headers específicos
   - ✅ Está categorizada na CISCO

### Passo 2: Verificar Categorização CISCO

#### Como Verificar a Categorização

1. **Acessar o Cisco Talos Intelligence Center:**
   - URL: https://www.talosintelligence.com/
   - Ou diretamente: https://www.talosintelligence.com/reputation_center

2. **Localizar a barra de pesquisa:**
   - Na página principal, procure pela barra de pesquisa "Intelligence Search"
   - Geralmente está no topo da página ou em uma seção destacada

3. **Pesquisar a URL ou domínio:**
   - Digite a URL completa (ex: `https://seu-dominio.com/webhook/santander`)
   - Ou apenas o domínio (ex: `seu-dominio.com`)
   - Pressione Enter ou clique em buscar

4. **Analisar os resultados:**
   - A página exibirá informações sobre a URL/domínio
   - Verifique a **categorização de conteúdo** (category)
   - Verifique a **reputação** (reputation)
   - Categorias aceitáveis geralmente incluem: Business, Technology, Finance, etc.
   - Categorias problemáticas: Malicious, Phishing, Malware, Suspicious, etc.

#### O Que Fazer Se a Categorização Estiver Incorreta

Se a URL não estiver categorizada ou estiver com categoria incorreta (ex: "malicious"):

1. **Criar conta no Cisco Talos** (se não tiver):
   - Acesse: https://www.talosintelligence.com/
   - Clique em "Cisco Login" ou "Sign Up"
   - Crie uma conta gratuita

2. **Solicitar revisão de categorização:**
   - Acesse: https://talosintelligence.com/reputation_center/web_categorization
   - Faça login na sua conta
   - Preencha o formulário de solicitação:
     - **URL ou domínio**: Informe a URL completa
     - **Categorias sugeridas**: Sugira até 5 categorias (da mais relevante para a menos relevante)
       - Exemplos: Business, Technology, Finance, Information Technology, etc.
     - **Informações adicionais**: Explique o propósito da URL (ex: "Webhook endpoint para receber notificações do Santander Open Banking")
   - Envie o formulário

3. **Aguardar revisão:**
   - A equipe do Cisco Talos revisa manualmente todas as solicitações
   - O processo pode levar alguns dias úteis
   - Você receberá notificação quando a revisão for concluída

#### Categorias Recomendadas para Webhooks

Para webhooks bancários/financeiros, as categorias mais apropriadas são:
1. **Business** - Para aplicações de negócios
2. **Technology** - Para APIs e integrações técnicas
3. **Finance** - Para serviços financeiros
4. **Information Technology** - Para serviços de TI
5. **Computer and Internet** - Para serviços web

#### Verificação Rápida via API (Opcional)

Se você precisar verificar programaticamente, o Cisco Talos oferece APIs, mas geralmente requer autenticação e plano pago. Para verificação manual, use o site web.

### Passo 3: Registrar URL no Portal do Desenvolvedor

1. Acessar o Portal do Desenvolvedor Santander
2. Navegar até a seção de webhooks/configurações
3. Registrar a URL do webhook
4. Aguardar validação automática (chamada GET)
5. Se a validação passar, o webhook estará habilitado

### Passo 4: Configurar mTLS (Opcional)

1. Solicitar ao Santander a parte pública do certificado
2. Configurar o certificado na aplicação
3. Testar recebimento de notificações com mTLS

---

## 📝 Exemplo de Implementação

### Flask (Python)

```python
from flask import Flask, request, jsonify
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

@app.route('/webhook/santander', methods=['GET', 'POST'])
def webhook_santander():
    """
    Endpoint para receber webhooks do Santander.
    
    GET: Validação inicial pelo Santander
    POST: Recebimento de notificações
    """
    if request.method == 'GET':
        # Validação inicial - Santander verifica se a URL está acessível
        logger.info("✅ Validação de webhook recebida do Santander")
        return jsonify({
            'status': 'ok',
            'message': 'Webhook endpoint is ready'
        }), 200
    
    # POST - Recebimento de notificação
    try:
        data = request.get_json()
        logger.info(f"📨 Notificação recebida: {data}")
        
        # Processar notificação
        # Exemplo: evento de pagamento, mudança de saldo, etc.
        evento_tipo = data.get('eventType')
        evento_dados = data.get('data')
        
        # Processar conforme o tipo de evento
        processar_notificacao(evento_tipo, evento_dados)
        
        return jsonify({
            'status': 'received',
            'message': 'Notification processed'
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar notificação: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def processar_notificacao(tipo, dados):
    """Processa a notificação recebida"""
    if tipo == 'payment_received':
        # Processar pagamento recebido
        pass
    elif tipo == 'balance_changed':
        # Processar mudança de saldo
        pass
    # ... outros tipos de eventos
```

### Variáveis de Ambiente

```env
# Webhook Santander
SANTANDER_WEBHOOK_URL=https://seu-dominio.com/webhook/santander
SANTANDER_WEBHOOK_SECRET=seu_secret_aqui  # Se aplicável
SANTANDER_MTLS_CERT_PATH=./certs/santander_webhook_cert.pem  # Se usar mTLS
```

---

## ⚠️ Observações Importantes

### Validação de URL
- O Santander faz uma chamada GET imediatamente após o registro
- Se a validação falhar, o cadastro não será efetuado
- A API retornará uma resposta indicando o tipo de erro encontrado

### Tratamento de Erros
- Sempre retornar status HTTP apropriado (200 para sucesso, 500 para erro)
- Logar todas as notificações recebidas para auditoria
- Implementar retry logic caso o processamento falhe

### Segurança
- Validar origem das requisições (se possível)
- Usar HTTPS obrigatoriamente
- Considerar mTLS para maior segurança
- Não expor informações sensíveis nos logs

### Testes
- Testar endpoint GET antes de registrar
- Testar endpoint POST com payloads de exemplo
- Verificar se a URL está acessível publicamente
- Verificar categorização CISCO

---

## 🔗 Referências

- **Portal do Desenvolvedor Santander**: https://developer.santander.com.br
- **CISCO Talos Intelligence**: https://www.talosintelligence.com/
- **Documentação API PIX Recebimentos**: User Guide API PIX Recebimentos v11 (15/01/24)
- **Documentação API Hub de Pagamentos**: User Guide Hub de Pagamentos API v1.1 (10/10/23)

---

## 📌 Próximos Passos

1. **Verificar endpoint específico**: Confirmar se o endpoint `taxes_by_fields_payments` tem requisitos específicos adicionais
2. **Solicitar acesso**: Verificar se é necessário solicitar acesso específico para webhooks no Portal do Desenvolvedor
3. **Testar em sandbox**: Testar webhooks no ambiente de sandbox antes de produção
4. **Documentar eventos**: Documentar quais eventos são enviados via webhook para o endpoint específico

---

**Última atualização:** 06/01/2026

