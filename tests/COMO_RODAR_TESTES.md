# 🧪 Como Rodar os Testes Golden

## ❌ **NÃO FAÇA ISSO:**
```bash
python3 tests/test_email_flows_golden.py  # ❌ Não funciona assim!
```

## ✅ **FAÇA ASSIM:**

### **1. Instalar pytest (se ainda não tiver):**
```bash
pip install pytest
```

### **2. Rodar os testes:**
```bash
# Rodar todos os testes implementados
pytest tests/test_email_flows_golden.py -v

# Rodar um teste específico
pytest tests/test_email_flows_golden.py::TestEmailFlowsGolden::test_criar_email_preview_confirmar_enviado -v

# Rodar com mais detalhes
pytest tests/test_email_flows_golden.py -v -s
```

---

## 🤔 **O Que São Esses Testes?**

### **Resumo Simples:**

Esses testes **simulam** o que você faz no chat e verificam se tudo funciona corretamente.

**Exemplo do que o teste faz:**

1. **Simula você digitando:** "mande um email para helenomaffra@gmail.com sobre a reunião"
2. **Verifica se:** O sistema criou um preview do email
3. **Simula você digitando:** "sim" (para confirmar)
4. **Verifica se:** O email foi enviado corretamente

### **Por Que São Importantes?**

- ✅ **Protegem contra bugs:** Se você mudar algo no código, os testes avisam se quebrou
- ✅ **Documentam como funciona:** Mostram o comportamento esperado do sistema
- ✅ **Permitem refatorar com segurança:** Você pode mudar o código sabendo que os testes vão avisar se algo quebrar

---

## 📋 **Testes Implementados:**

### **1. Teste de Criação e Envio de Email**
- **O que testa:** Criar email → preview → confirmar → enviar
- **Por que é importante:** É o fluxo mais básico e usado

### **2. Teste de Melhoria de Email**
- **O que testa:** Criar email → melhorar → confirmar → enviar melhorado
- **Por que é importante:** Garante que quando você pede para melhorar, o email melhorado é enviado (não o antigo)

### **3. Teste de Correção de Email**
- **O que testa:** Criar email com email errado → corrigir → confirmar → enviar
- **Por que é importante:** Garante que você pode corrigir o email sem perder o contexto (assunto/conteúdo)

### **4. Teste de Idempotência**
- **O que testa:** Confirmar envio duas vezes → não deve enviar duas vezes
- **Por que é importante:** Protege contra envio duplicado acidental

---

## 🔧 **Se Der Erro:**

### **Erro: "pytest: command not found"**
```bash
pip install pytest
```

### **Erro: "ModuleNotFoundError"**
```bash
# Certifique-se de estar no diretório raiz do projeto
cd /Users/helenomaffra/Chat-IA-Independente
pytest tests/test_email_flows_golden.py -v
```

### **Erro: "Database locked" ou similar**
- Os testes criam um banco de dados temporário
- Se der erro, pode ser que outro processo esteja usando o banco
- Tente fechar o Flask se estiver rodando

---

## 💡 **Dica:**

Você **não precisa** rodar os testes agora se não quiser. Eles estão prontos para quando você precisar refatorar o código (Passo 3).

Os testes são como um **"airbag"** - você espera não precisar, mas é bom ter quando precisar! 😊
