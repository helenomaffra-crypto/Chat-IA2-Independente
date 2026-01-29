# 💡 Proposta: Cadastro de Destinatários e Histórico de TEDs

**Data:** 12/01/2026  
**Status:** 📋 **PROPOSTA** - Aguardando aprovação

---

## 🎯 Objetivo

Implementar sistema completo de cadastro de destinatários e histórico de TEDs para:
1. **Cadastrar pessoas/empresas** que serão pagas via TED
2. **Gravar transfer_id** quando efetivar TED para consulta posterior
3. **Modal automático** que abre quando detectar intenção de fazer TED
4. **Design sutil** mantendo padrão WhatsApp

---

## 📋 Funcionalidades Propostas

### 1. **Modal de Cadastro de Destinatário**

**Quando abre:**
- Automaticamente quando detectar intenção de fazer TED (ex: "fazer ted", "transferir", "enviar dinheiro")
- Manualmente via comando: "cadastrar destinatário"

**Campos:**
- Nome completo (obrigatório)
- CPF/CNPJ (obrigatório, com validação)
- Banco (código, ex: 001, 033)
- Agência (obrigatório)
- Conta (obrigatório)
- Tipo de conta (Corrente, Poupança, Pagamento)
- Apelido/Nome curto (opcional, para facilitar busca)
- Observações (opcional)

**Comportamento:**
- Se destinatário já existe: Sugerir usar cadastrado ou editar
- Se não existe: Abrir modal para cadastrar
- Design sutil tipo WhatsApp (seguindo padrão dos outros modais)

---

### 2. **Histórico de TEDs**

**O que gravar:**
- `transfer_id` (ID único da TED)
- `workspace_id` (workspace usado)
- `destinatario_id` (ID do destinatário cadastrado)
- `valor` (valor da transferência)
- `status` (READY_TO_PAY, PENDING_CONFIRMATION, AUTHORIZED, SETTLED, REJECTED)
- `data_criacao` (quando foi criada)
- `data_efetivacao` (quando foi efetivada)
- `data_consulta` (última consulta de status)
- `dados_completos` (JSON com resposta completa da API)

**Consultas:**
- Listar TEDs por destinatário
- Listar TEDs por período
- Listar TEDs por status
- Consultar TED por transfer_id

---

## 🗄️ Estrutura de Banco de Dados

### Tabela 1: `TED_DESTINATARIOS` (SQL Server)

```sql
CREATE TABLE [dbo].[TED_DESTINATARIOS] (
    id_destinatario BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Identificação
    nome_completo VARCHAR(255) NOT NULL,
    cpf_cnpj VARCHAR(18) NOT NULL,
    tipo_pessoa VARCHAR(20) NOT NULL,  -- 'PESSOA_FISICA' ou 'PESSOA_JURIDICA'
    apelido VARCHAR(100),  -- Nome curto para facilitar busca
    
    -- Dados Bancários
    banco_codigo VARCHAR(10) NOT NULL,  -- Ex: '001', '033'
    banco_nome VARCHAR(100),  -- Ex: 'Banco do Brasil', 'Santander'
    agencia VARCHAR(20) NOT NULL,
    conta VARCHAR(50) NOT NULL,
    tipo_conta VARCHAR(20) NOT NULL,  -- 'CONTA_CORRENTE', 'CONTA_POUPANCA', 'CONTA_PAGAMENTO'
    
    -- Metadados
    observacoes TEXT,
    ativo BIT DEFAULT 1,  -- Se destinatário está ativo
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_cpf_cnpj (cpf_cnpj),
    INDEX idx_apelido (apelido),
    INDEX idx_banco_conta (banco_codigo, agencia, conta),
    INDEX idx_ativo (ativo)
);
```

### Tabela 2: `TED_TRANSFERENCIAS` (SQL Server)

```sql
CREATE TABLE [dbo].[TED_TRANSFERENCIAS] (
    id_transferencia BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- IDs
    transfer_id VARCHAR(100) NOT NULL UNIQUE,  -- ID retornado pela API
    workspace_id VARCHAR(100),  -- Workspace usado
    destinatario_id BIGINT,  -- FK para TED_DESTINATARIOS
    
    -- Dados da Transferência
    valor DECIMAL(18,2) NOT NULL,
    moeda VARCHAR(3) DEFAULT 'BRL',
    status VARCHAR(50) NOT NULL,  -- READY_TO_PAY, PENDING_CONFIRMATION, AUTHORIZED, SETTLED, REJECTED
    
    -- Conta Origem
    agencia_origem VARCHAR(20),
    conta_origem VARCHAR(50),
    
    -- Conta Destino (pode ser diferente do cadastrado se editado)
    banco_destino VARCHAR(10),
    agencia_destino VARCHAR(20),
    conta_destino VARCHAR(50),
    tipo_conta_destino VARCHAR(20),
    nome_destinatario VARCHAR(255),  -- Nome usado na transferência
    cpf_cnpj_destinatario VARCHAR(18),
    
    -- Datas
    data_criacao DATETIME NOT NULL DEFAULT GETDATE(),
    data_efetivacao DATETIME,
    data_consulta DATETIME,  -- Última consulta de status
    data_settled DATETIME,  -- Quando foi liquidada
    
    -- Dados Completos
    json_dados_completos NVARCHAR(MAX),  -- JSON completo da API
    
    -- Metadados
    observacoes TEXT,
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_transfer_id (transfer_id),
    INDEX idx_destinatario (destinatario_id),
    INDEX idx_status (status),
    INDEX idx_data_criacao (data_criacao DESC),
    INDEX idx_workspace (workspace_id)
);
```

---

## 🔄 Fluxo Completo

### Cenário 1: TED com Destinatário Novo

```
1. Usuário: "fazer ted de 100 reais para joão silva cpf 12345678901"
2. Sistema detecta intenção de TED
3. Sistema verifica se destinatário existe (por CPF)
4. Destinatário não existe → Abre modal de cadastro
5. Usuário preenche dados bancários no modal
6. Sistema salva destinatário no banco
7. Sistema cria TED usando dados cadastrados
8. Sistema salva TED no histórico com transfer_id
9. Sistema retorna transfer_id para efetivação
```

### Cenário 2: TED com Destinatário Cadastrado

```
1. Usuário: "fazer ted de 200 reais para maria santos"
2. Sistema detecta intenção de TED
3. Sistema busca destinatário por nome/apelido
4. Destinatário encontrado → Pergunta: "Usar dados cadastrados de Maria Santos?"
5. Usuário confirma → Sistema cria TED usando dados cadastrados
6. Sistema salva TED no histórico com transfer_id e destinatario_id
7. Sistema retorna transfer_id para efetivação
```

### Cenário 3: Efetivar TED

```
1. Usuário: "efetivar ted 4ef8791d-415a-4987-9206-4553a8f1d609"
2. Sistema busca TED no histórico por transfer_id
3. Sistema efetiva TED via API
4. Sistema atualiza status e data_efetivacao no histórico
5. Sistema retorna confirmação
```

### Cenário 4: Consultar TED

```
1. Usuário: "consultar ted 4ef8791d-415a-4987-9206-4553a8f1d609"
2. Sistema busca TED no histórico por transfer_id
3. Sistema consulta status atual via API
4. Sistema atualiza status e data_consulta no histórico
5. Sistema retorna status atualizado
```

---

## 🎨 Design do Modal

**Seguindo padrão WhatsApp dos outros modais:**

```html
<!-- Modal de Cadastro de Destinatário -->
<div id="modal-cadastro-destinatario">
  <div class="modal-content">
    <div class="modal-header">
      <h2>💸 Cadastrar Destinatário</h2>
      <button class="modal-close" onclick="fecharModalDestinatario()">✕</button>
    </div>
    
    <div class="modal-body">
      <form id="form-destinatario">
        <!-- Nome -->
        <div class="form-group">
          <label>Nome Completo *</label>
          <input type="text" id="destinatario-nome" required>
        </div>
        
        <!-- CPF/CNPJ -->
        <div class="form-group">
          <label>CPF/CNPJ *</label>
          <input type="text" id="destinatario-cpf-cnpj" required>
        </div>
        
        <!-- Banco -->
        <div class="form-group">
          <label>Banco *</label>
          <select id="destinatario-banco" required>
            <option value="">Selecione...</option>
            <option value="001">001 - Banco do Brasil</option>
            <option value="033">033 - Santander</option>
            <option value="104">104 - Caixa Econômica</option>
            <!-- ... -->
          </select>
        </div>
        
        <!-- Agência e Conta -->
        <div class="form-row">
          <div class="form-group">
            <label>Agência *</label>
            <input type="text" id="destinatario-agencia" required>
          </div>
          <div class="form-group">
            <label>Conta *</label>
            <input type="text" id="destinatario-conta" required>
          </div>
        </div>
        
        <!-- Tipo de Conta -->
        <div class="form-group">
          <label>Tipo de Conta *</label>
          <select id="destinatario-tipo-conta" required>
            <option value="CONTA_CORRENTE">Conta Corrente</option>
            <option value="CONTA_POUPANCA">Poupança</option>
            <option value="CONTA_PAGAMENTO">Conta Pagamento</option>
          </select>
        </div>
        
        <!-- Apelido (opcional) -->
        <div class="form-group">
          <label>Apelido (opcional)</label>
          <input type="text" id="destinatario-apelido" 
                 placeholder="Ex: João do Frete">
        </div>
        
        <!-- Observações -->
        <div class="form-group">
          <label>Observações</label>
          <textarea id="destinatario-observacoes" rows="2"></textarea>
        </div>
      </form>
    </div>
    
    <div class="modal-footer">
      <button class="modal-btn modal-btn-cancel" 
              onclick="fecharModalDestinatario()">
        Cancelar
      </button>
      <button class="modal-btn modal-btn-save" 
              onclick="salvarDestinatario()">
        Salvar e Continuar
      </button>
    </div>
  </div>
</div>
```

---

## 🔧 Implementação Técnica

### 1. **Serviço Python: `ted_destinatarios_service.py`**

```python
# services/ted_destinatarios_service.py

class TedDestinatariosService:
    """Gerencia cadastro de destinatários de TED"""
    
    def cadastrar_destinatario(self, dados: Dict) -> Dict:
        """Cadastra novo destinatário"""
        # Validar CPF/CNPJ
        # Verificar se já existe
        # Salvar no SQL Server
        # Retornar ID do destinatário
    
    def buscar_destinatario(self, cpf_cnpj: str = None, 
                           nome: str = None, 
                           apelido: str = None) -> Dict:
        """Busca destinatário por CPF/CNPJ, nome ou apelido"""
    
    def listar_destinatarios(self, ativo: bool = True) -> List[Dict]:
        """Lista todos os destinatários ativos"""
    
    def atualizar_destinatario(self, id_destinatario: int, dados: Dict) -> Dict:
        """Atualiza dados de destinatário"""
```

### 2. **Serviço Python: `ted_historico_service.py`**

```python
# services/ted_historico_service.py

class TedHistoricoService:
    """Gerencia histórico de TEDs"""
    
    def salvar_ted(self, transfer_id: str, dados: Dict) -> Dict:
        """Salva TED no histórico"""
        # Salvar transfer_id, workspace_id, destinatario_id, valor, status
        # Salvar JSON completo da API
        # Retornar ID do registro
    
    def buscar_ted_por_transfer_id(self, transfer_id: str) -> Dict:
        """Busca TED por transfer_id"""
    
    def atualizar_status_ted(self, transfer_id: str, status: str, 
                             dados_atualizados: Dict = None) -> Dict:
        """Atualiza status de TED"""
    
    def listar_teds(self, destinatario_id: int = None, 
                   data_inicio: str = None, 
                   data_fim: str = None,
                   status: str = None) -> List[Dict]:
        """Lista TEDs com filtros"""
```

### 3. **Detecção de Intenção: `MessageIntentService`**

```python
# services/message_intent_service.py

def detectar_intencao_ted(self, mensagem: str) -> Dict:
    """Detecta intenção de fazer TED"""
    patterns = [
        r'fazer\s+ted',
        r'transferir\s+\d+',
        r'enviar\s+dinheiro',
        r'pagar\s+via\s+ted',
        # ...
    ]
    
    if match:
        return {
            'tipo': 'ted',
            'acao': 'abrir_cadastro_destinatario',
            'dados_extraidos': {
                'valor': ...,
                'nome': ...,
                'cpf_cnpj': ...
            }
        }
```

### 4. **Integração no Chat Service**

```python
# services/chat_service.py

def processar_mensagem(self, mensagem: str, ...):
    # 1. Detectar intenção de TED
    intencao = self.message_intent_service.detectar_intencao_ted(mensagem)
    
    if intencao and intencao['tipo'] == 'ted':
        # 2. Verificar se destinatário existe
        destinatario = self.ted_destinatarios_service.buscar_destinatario(
            cpf_cnpj=intencao.get('cpf_cnpj'),
            nome=intencao.get('nome')
        )
        
        if not destinatario:
            # 3. Abrir modal de cadastro
            return {
                'resposta': '💸 Vou abrir o cadastro de destinatário...',
                'comando_interface': {
                    'tipo': 'ted',
                    'acao': 'abrir_cadastro_destinatario',
                    'dados_preenchidos': intencao.get('dados_extraidos', {})
                }
            }
        else:
            # 4. Confirmar uso de destinatário cadastrado
            return {
                'resposta': f'✅ Encontrei {destinatario["nome"]} cadastrado. Usar dados cadastrados?',
                'dados': {'destinatario': destinatario}
            }
```

---

## 📝 Endpoints de API

### 1. **Cadastro de Destinatário**

```python
# app.py

@app.route('/api/ted/destinatarios', methods=['POST'])
def cadastrar_destinatario():
    """Cadastra novo destinatário"""
    dados = request.json
    resultado = ted_destinatarios_service.cadastrar_destinatario(dados)
    return jsonify(resultado)

@app.route('/api/ted/destinatarios', methods=['GET'])
def listar_destinatarios():
    """Lista destinatários"""
    ativo = request.args.get('ativo', 'true') == 'true'
    resultado = ted_destinatarios_service.listar_destinatarios(ativo=ativo)
    return jsonify(resultado)

@app.route('/api/ted/destinatarios/<int:id>', methods=['GET'])
def buscar_destinatario(id):
    """Busca destinatário por ID"""
    resultado = ted_destinatarios_service.buscar_destinatario(id=id)
    return jsonify(resultado)
```

### 2. **Histórico de TEDs**

```python
@app.route('/api/ted/historico', methods=['POST'])
def salvar_ted():
    """Salva TED no histórico"""
    dados = request.json
    resultado = ted_historico_service.salvar_ted(
        transfer_id=dados['transfer_id'],
        dados=dados
    )
    return jsonify(resultado)

@app.route('/api/ted/historico/<transfer_id>', methods=['GET'])
def buscar_ted(transfer_id):
    """Busca TED por transfer_id"""
    resultado = ted_historico_service.buscar_ted_por_transfer_id(transfer_id)
    return jsonify(resultado)

@app.route('/api/ted/historico', methods=['GET'])
def listar_teds():
    """Lista TEDs com filtros"""
    destinatario_id = request.args.get('destinatario_id')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    status = request.args.get('status')
    
    resultado = ted_historico_service.listar_teds(
        destinatario_id=destinatario_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        status=status
    )
    return jsonify(resultado)
```

---

## ✅ Checklist de Implementação

### Fase 1: Banco de Dados
- [ ] Criar tabela `TED_DESTINATARIOS` no SQL Server
- [ ] Criar tabela `TED_TRANSFERENCIAS` no SQL Server
- [ ] Criar índices para performance
- [ ] Testar inserção e consulta

### Fase 2: Backend
- [ ] Criar `TedDestinatariosService`
- [ ] Criar `TedHistoricoService`
- [ ] Criar endpoints de API
- [ ] Integrar com `SantanderPaymentsService` para salvar TEDs
- [ ] Testar fluxo completo

### Fase 3: Frontend
- [ ] Criar modal de cadastro de destinatário
- [ ] Adicionar detecção de intenção de TED no `MessageIntentService`
- [ ] Integrar abertura automática do modal
- [ ] Criar interface para listar destinatários
- [ ] Criar interface para consultar histórico de TEDs
- [ ] Testar UX completa

### Fase 4: Integração
- [ ] Integrar cadastro com criação de TED
- [ ] Integrar efetivação com atualização de status
- [ ] Integrar consulta com atualização de status
- [ ] Testar fluxo end-to-end

---

## 🎯 Benefícios

1. **Facilita uso:** Destinatários cadastrados uma vez, reutilizados sempre
2. **Rastreabilidade:** Histórico completo de todas as TEDs
3. **Consultas rápidas:** Buscar TED por transfer_id ou destinatário
4. **UX melhorada:** Modal automático, design sutil
5. **Compliance:** Registro completo para auditoria

---

**Última atualização:** 12/01/2026
