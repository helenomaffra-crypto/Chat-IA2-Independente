# 🎛️ Regras de Cálculo: UI vs Código - Onde Armazenar?

**Última atualização:** 05/01/2026

---

## ❓ A Pergunta

**"As regras de cálculo (instruções do assistente) podem ser colocadas na UI ou teriam que ser dentro do código?"**

**Resposta:** Pode ser **ambos**, mas cada abordagem tem vantagens e desvantagens.

---

## 📊 Comparação das Opções

### **Opção 1: No Código (Hardcoded)**

**Como funciona:**
```python
# services/assistants_service.py
def criar_assistente_calculos_fiscais(self):
    assistant = self.client.beta.assistants.create(
        instructions="""
        REGRAS DE CÁLCULO:
        1. II: Base = CIF, Fórmula = CIF × Alíquota_II
        2. IPI: Base = CIF + II, Fórmula = (CIF + II) × Alíquota_IPI
        ...
        """
    )
```

**✅ Vantagens:**
- ✅ Versionado no Git (histórico de mudanças)
- ✅ Fácil de revisar em PRs
- ✅ Não precisa de banco de dados adicional
- ✅ Mais simples de implementar

**❌ Desvantagens:**
- ❌ Precisa de deploy para mudar
- ❌ Não pode ser editado por usuários não-técnicos
- ❌ Mudanças requerem acesso ao código

---

### **Opção 2: Na UI (Editável pelo Usuário)**

**Como funciona:**
- Regras armazenadas em banco de dados (SQLite)
- Interface na UI para editar
- Assistente lê do banco ao ser criado/atualizado

**✅ Vantagens:**
- ✅ Pode ser editado sem deploy
- ✅ Usuários não-técnicos podem editar
- ✅ Mudanças imediatas (sem reiniciar servidor)
- ✅ Pode ter histórico de versões

**❌ Desvantagens:**
- ❌ Mais complexo de implementar
- ❌ Precisa de validação de entrada
- ❌ Precisa de backup/restore
- ❌ Pode ser editado incorretamente

---

### **Opção 3: Híbrida (Recomendada)**

**Como funciona:**
- Regras padrão no código (template)
- Regras customizadas no banco de dados
- UI para editar apenas as customizações
- Fallback para padrão se não houver customização

**✅ Vantagens:**
- ✅ Melhor dos dois mundos
- ✅ Regras padrão sempre disponíveis
- ✅ Customizações sem perder o padrão
- ✅ Fácil de reverter

**❌ Desvantagens:**
- ❌ Implementação mais complexa
- ❌ Precisa gerenciar merge de regras

---

## 🏗️ Arquitetura Recomendada

### **Estrutura de Dados:**

```sql
-- Tabela para armazenar regras de cálculo
CREATE TABLE regras_calculo_impostos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_assistente TEXT NOT NULL,  -- 'calculos_fiscais', 'legislacao', etc.
    nome TEXT NOT NULL,              -- Nome da regra (ex: 'II', 'IPI')
    descricao TEXT,                 -- Descrição da regra
    base_calculo TEXT NOT NULL,      -- 'CIF', 'CIF+II', etc.
    formula TEXT NOT NULL,           -- Fórmula Python (ex: 'cif_brl * aliquota_ii')
    exemplo TEXT,                    -- Exemplo de uso
    ativo BOOLEAN DEFAULT 1,
    ordem INTEGER DEFAULT 0,        -- Ordem de exibição
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela para histórico de mudanças
CREATE TABLE regras_calculo_historico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regra_id INTEGER,
    tipo_mudanca TEXT,               -- 'criado', 'atualizado', 'desativado'
    valor_anterior TEXT,             -- JSON com valores anteriores
    valor_novo TEXT,                 -- JSON com valores novos
    usuario TEXT,
    data_mudanca TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (regra_id) REFERENCES regras_calculo_impostos(id)
);
```

### **Fluxo de Funcionamento:**

```
1. Sistema inicia
   ↓
2. Carrega regras do banco (se existirem)
   ↓
3. Se não existirem, usa regras padrão do código
   ↓
4. Cria/atualiza assistente com essas regras
   ↓
5. Usuário pode editar via UI
   ↓
6. Mudanças são salvas no banco
   ↓
7. Assistente é atualizado automaticamente
```

---

## 💻 Implementação

### **1. Estrutura no Banco de Dados:**

```python
# db_manager.py

def init_db():
    # ... código existente ...
    
    # Tabela de regras de cálculo
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regras_calculo_impostos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_assistente TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            base_calculo TEXT NOT NULL,
            formula TEXT NOT NULL,
            exemplo TEXT,
            ativo BOOLEAN DEFAULT 1,
            ordem INTEGER DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tipo_assistente, nome)
        )
    ''')
    
    # Inserir regras padrão se não existirem
    regras_padrao = [
        {
            'tipo_assistente': 'calculos_fiscais',
            'nome': 'II',
            'descricao': 'Imposto de Importação',
            'base_calculo': 'CIF',
            'formula': 'cif_brl * aliquota_ii',
            'exemplo': 'Se CIF = R$ 50.000 e Alíquota = 18%, então II = R$ 50.000 × 0.18 = R$ 9.000',
            'ordem': 1
        },
        {
            'tipo_assistente': 'calculos_fiscais',
            'nome': 'IPI',
            'descricao': 'Imposto sobre Produtos Industrializados',
            'base_calculo': 'CIF + II',
            'formula': '(cif_brl + ii_brl) * aliquota_ipi',
            'exemplo': 'Se CIF = R$ 50.000 e II = R$ 9.000 e Alíquota = 10%, então IPI = (R$ 50.000 + R$ 9.000) × 0.10 = R$ 5.900',
            'ordem': 2
        },
        # ... mais regras
    ]
    
    for regra in regras_padrao:
        cursor.execute('''
            INSERT OR IGNORE INTO regras_calculo_impostos 
            (tipo_assistente, nome, descricao, base_calculo, formula, exemplo, ordem)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            regra['tipo_assistente'],
            regra['nome'],
            regra['descricao'],
            regra['base_calculo'],
            regra['formula'],
            regra['exemplo'],
            regra['ordem']
        ))
```

### **2. Serviço para Gerenciar Regras:**

```python
# services/regras_calculo_service.py

class RegrasCalculoService:
    """Gerencia regras de cálculo de impostos."""
    
    def obter_regras(self, tipo_assistente: str) -> List[Dict]:
        """Obtém regras ativas do banco."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM regras_calculo_impostos
            WHERE tipo_assistente = ? AND ativo = 1
            ORDER BY ordem
        ''', (tipo_assistente,))
        
        regras = []
        for row in cursor.fetchall():
            regras.append(dict(row))
        
        conn.close()
        return regras
    
    def gerar_instrucoes_assistente(self, tipo_assistente: str) -> str:
        """Gera instruções do assistente a partir das regras."""
        regras = self.obter_regras(tipo_assistente)
        
        instrucoes = f"""Você é um especialista em cálculos fiscais de importação no Brasil.

REGRAS DE CÁLCULO:

"""
        for regra in regras:
            instrucoes += f"""
{regra['ordem']}. {regra['nome']} ({regra['descricao']}):
   - Base de cálculo: {regra['base_calculo']}
   - Fórmula: {regra['formula']}
   - Exemplo: {regra['exemplo']}

"""
        
        instrucoes += """
REGRAS IMPORTANTES:
- Sempre arredonde para 2 casas decimais
- Use a cotação PTAX fornecida
- Se algum valor estiver faltando, informe claramente qual
"""
        
        return instrucoes
    
    def salvar_regra(self, regra: Dict) -> bool:
        """Salva ou atualiza uma regra."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO regras_calculo_impostos
            (tipo_assistente, nome, descricao, base_calculo, formula, exemplo, ordem, ativo, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            regra['tipo_assistente'],
            regra['nome'],
            regra.get('descricao', ''),
            regra['base_calculo'],
            regra['formula'],
            regra.get('exemplo', ''),
            regra.get('ordem', 0),
            regra.get('ativo', 1)
        ))
        
        conn.commit()
        conn.close()
        return True
```

### **3. Endpoints da API:**

```python
# app.py

@app.route('/api/regras-calculo', methods=['GET'])
def listar_regras_calculo():
    """Lista regras de cálculo."""
    tipo = request.args.get('tipo', 'calculos_fiscais')
    
    from services.regras_calculo_service import RegrasCalculoService
    service = RegrasCalculoService()
    
    regras = service.obter_regras(tipo)
    
    return jsonify({
        'sucesso': True,
        'regras': regras
    })

@app.route('/api/regras-calculo', methods=['POST'])
def salvar_regra_calculo():
    """Salva ou atualiza uma regra."""
    data = request.get_json()
    
    from services.regras_calculo_service import RegrasCalculoService
    service = RegrasCalculoService()
    
    sucesso = service.salvar_regra(data)
    
    if sucesso:
        # Atualizar assistente com novas regras
        from services.assistants_service import AssistantsService
        assistants_service = AssistantsService()
        assistants_service.atualizar_assistente_calculos()
    
    return jsonify({
        'sucesso': sucesso
    })
```

### **4. Interface na UI:**

```html
<!-- templates/chat-ia-isolado.html -->

<!-- Modal de Configuração de Regras -->
<div id="modal-regras-calculo" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <h2>📐 Regras de Cálculo de Impostos</h2>
            <button class="modal-close" onclick="fecharModalRegras()">×</button>
        </div>
        <div class="modal-body">
            <div id="lista-regras-calculo">
                <!-- Regras serão carregadas aqui -->
            </div>
            <button onclick="adicionarRegra()">+ Adicionar Regra</button>
        </div>
    </div>
</div>

<script>
async function carregarRegrasCalculo() {
    const response = await fetch('/api/regras-calculo?tipo=calculos_fiscais');
    const data = await response.json();
    
    if (data.sucesso) {
        const lista = document.getElementById('lista-regras-calculo');
        lista.innerHTML = data.regras.map(regra => `
            <div class="regra-item">
                <h3>${regra.nome}</h3>
                <p><strong>Base:</strong> ${regra.base_calculo}</p>
                <p><strong>Fórmula:</strong> <code>${regra.formula}</code></p>
                <button onclick="editarRegra(${regra.id})">Editar</button>
            </div>
        `).join('');
    }
}

async function salvarRegra(regra) {
    const response = await fetch('/api/regras-calculo', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(regra)
    });
    
    const data = await response.json();
    if (data.sucesso) {
        alert('✅ Regra salva! O assistente será atualizado automaticamente.');
        carregarRegrasCalculo();
    }
}
</script>
```

---

## 🎯 Recomendação Final

### **Para mAIke, recomendo: Opção 3 (Híbrida)**

**Por quê?**
1. ✅ Regras padrão sempre disponíveis (não quebra se banco estiver vazio)
2. ✅ Usuários podem customizar sem perder o padrão
3. ✅ Fácil de reverter (apenas desativar customização)
4. ✅ Versionado no Git (regras padrão)
5. ✅ Flexível (pode editar via UI ou código)

### **Implementação Sugerida:**

1. **Fase 1:** Implementar regras padrão no código (rápido)
2. **Fase 2:** Adicionar tabela no banco (preparar para customização)
3. **Fase 3:** Criar UI para editar (quando necessário)

**Isso permite:**
- ✅ Começar rápido (regras no código)
- ✅ Evoluir gradualmente (adicionar UI depois)
- ✅ Sempre ter fallback (regras padrão)

---

## 📝 Exemplo de Uso

### **Cenário 1: Regras Padrão (Código)**

```python
# Assistente usa regras do código
assistant = criar_assistente_calculos_fiscais()
# Usa regras hardcoded
```

### **Cenário 2: Regras Customizadas (UI)**

```
1. Usuário abre UI: "Configurações > Regras de Cálculo"
2. Edita regra de II: muda base de cálculo de "CIF" para "CIF + Despesas"
3. Salva
4. Sistema atualiza assistente automaticamente
5. Próximos cálculos usam nova regra
```

### **Cenário 3: Reverter para Padrão**

```
1. Usuário desativa regra customizada na UI
2. Sistema volta a usar regra padrão do código
3. Assistente é atualizado automaticamente
```

---

## 🔒 Segurança e Validação

### **Validações Importantes:**

1. **Validação de Fórmula:**
   - Verificar se fórmula Python é válida
   - Testar com dados de exemplo
   - Prevenir código malicioso

2. **Validação de Base de Cálculo:**
   - Verificar se variáveis existem (CIF, II, etc.)
   - Validar sintaxe

3. **Histórico de Mudanças:**
   - Salvar versão anterior antes de atualizar
   - Permitir reverter mudanças

4. **Permissões:**
   - Apenas usuários autorizados podem editar
   - Log de quem fez mudanças

---

## 🚀 Próximos Passos

1. [ ] Criar tabela `regras_calculo_impostos` no banco
2. [ ] Implementar `RegrasCalculoService`
3. [ ] Criar endpoints da API
4. [ ] Criar UI para editar regras
5. [ ] Integrar com `AssistantsService`
6. [ ] Testar com regras reais

---

**Resumo:** As regras podem estar **tanto no código quanto na UI**. A melhor abordagem é **híbrida**: regras padrão no código, customizações na UI, com fallback automático.





