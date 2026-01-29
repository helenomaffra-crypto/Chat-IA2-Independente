# 🌐 Como Compartilhar o mAIke na Rede Local

**Data:** 13/01/2026

---

## ✅ **Configuração Automática**

O Flask já está configurado para aceitar conexões da rede local (`host='0.0.0.0'`). Quando você iniciar o servidor, ele mostrará automaticamente:

- **IP local:** `http://localhost:5001/chat-ia` (apenas no seu computador)
- **IP da rede:** `http://<SEU_IP>:5001/chat-ia` (para outros na mesma rede)

---

## 🚀 **Passos para Compartilhar**

### 1. **Iniciar o Servidor**

```bash
cd /Users/helenomaffra/Chat-IA-Independente
python3 app.py
```

### 2. **Ver o IP na Mensagem de Inicialização**

Quando o servidor iniciar, você verá algo como:

```
======================================================================
🌐 INICIANDO SERVIDOR FLASK
======================================================================
📱 Acesse localmente: http://localhost:5001/chat-ia
🌐 Acesse na rede: http://192.168.1.100:5001/chat-ia
   Compartilhe este IP com outros na mesma rede: 192.168.1.100
======================================================================
```

### 3. **Compartilhar o IP com Outros**

Envie o IP mostrado na mensagem (ex: `192.168.1.100`) para quem você quer que teste.

**Exemplo de mensagem:**
```
Acesse: http://192.168.1.100:5001/chat-ia
```

---

## 🔍 **Descobrir o IP Manualmente (se necessário)**

### **macOS/Linux:**
```bash
# Método 1: ifconfig
ifconfig | grep 'inet ' | grep -v 127.0.0.1

# Método 2: ipconfig (macOS)
ipconfig getifaddr en0

# Método 3: hostname
hostname -I
```

### **Windows:**
```cmd
ipconfig
```
Procure por "IPv4 Address" na interface de rede ativa.

---

## 🔒 **Segurança e Firewall**

### **macOS:**

**⚠️ IMPORTANTE:** Se o firewall estiver **desativado**, você **NÃO precisa fazer nada**! O acesso na rede já deve funcionar diretamente.

**Como verificar se o firewall está ativo:**
- Preferências do Sistema → Segurança e Privacidade → Firewall
- Se estiver "Desligado", não precisa configurar nada
- Se estiver "Ligado", siga as instruções abaixo

#### **OPÇÃO 1: Permitir Python (RECOMENDADO)**

1. Abra: **Preferências do Sistema** → **Segurança e Privacidade** → **Firewall**
2. Clique no **cadeado 🔒** e digite sua senha
3. Clique em **"Opções de Firewall..."**
4. Procure por **"Python"** na lista:
   - Se não aparecer, clique em **"+"** e adicione o Python
   - Caminho típico: `/usr/bin/python3` ou `/Library/Frameworks/Python.framework/Versions/3.x/bin/python3`
5. Configure como **"Permitir conexões de entrada"**
6. Clique em **"OK"**

#### **OPÇÃO 2: Desabilitar Firewall Temporariamente (TESTE RÁPIDO)**

⚠️ **APENAS PARA TESTE EM REDE CONFIÁVEL!**

1. Abra: **Preferências do Sistema** → **Segurança e Privacidade** → **Firewall**
2. Clique em **"Desligar Firewall"**
3. Teste se outros conseguem acessar
4. **⚠️ IMPORTANTE:** Reative o firewall depois do teste!

#### **OPÇÃO 3: Via Terminal (RÁPIDO)**

```bash
# Ver status do firewall
/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# Permitir Python (ajuste o caminho se necessário)
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/python3
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /usr/bin/python3
```

**Para encontrar o caminho do Python:**
```bash
which python3
```

### **Linux:**
```bash
# Ubuntu/Debian
sudo ufw allow 5001

# Ou temporariamente desabilitar
sudo ufw disable  # ⚠️ apenas para teste
```

### **Windows:**
1. Painel de Controle → Firewall do Windows
2. Configurações Avançadas → Regras de Entrada
3. Nova Regra → Porta → TCP → 5001 → Permitir

---

## ⚠️ **Avisos Importantes**

1. **Rede Confiável:** Apenas compartilhe em redes confiáveis (escritório, casa)
2. **Sem Autenticação:** A interface não tem autenticação por padrão - qualquer pessoa na rede pode acessar
3. **Dados Sensíveis:** Certifique-se de que não há dados sensíveis expostos
4. **Porta:** A porta padrão é `5001` (configurável via variável `PORT` no `.env`)

---

## 🧪 **Testar Acesso Remoto**

### **Do seu computador:**
```bash
curl http://localhost:5001/health
```

### **De outro computador na rede:**
```bash
curl http://<SEU_IP>:5001/health
```

**Nota:** A rota é `/health` (não `/api/health`). Se retornar JSON com `{"status": "healthy"}`, está funcionando! ✅

---

## 📱 **Acessar pelo Navegador**

1. **No seu computador:**
   - Abra: `http://localhost:5001/chat-ia`

2. **Em outro computador na mesma rede:**
   - Abra: `http://<SEU_IP>:5001/chat-ia`
   - Exemplo: `http://192.168.1.100:5001/chat-ia`

---

## 🐛 **Troubleshooting**

### **Problema: "Connection refused" ou timeout**

**Soluções:**
1. Verificar se o servidor está rodando
2. Verificar se o firewall está bloqueando
3. Verificar se está na mesma rede
4. Tentar pingar o IP: `ping <SEU_IP>`

### **Problema: iPhone não consegue acessar**

**Checklist de diagnóstico:**

1. **Servidor está rodando?**
   - Veja se o terminal mostra "INICIANDO SERVIDOR FLASK"
   - Deve mostrar o IP da rede

2. **iPhone está na mesma rede Wi‑Fi?**
   - iPhone: Configurações → Wi‑Fi → Verifique o nome da rede
   - Mac: Preferências do Sistema → Rede → Verifique o nome da rede
   - ⚠️ **IMPORTANTE:** iPhone deve estar em Wi‑Fi, **NÃO em dados móveis!**

3. **IP está correto?**
   - Use o IP mostrado na mensagem do servidor
   - Formato: `http://192.168.x.x:5001/chat-ia`
   - ⚠️ Use `http://` (não `https://`)

4. **Teste no navegador do iPhone:**
   - Abra Safari
   - Digite: `http://<SEU_IP>:5001/chat-ia`
   - ⚠️ **NÃO use https://** (use http://)

5. **Verificar IP do iPhone:**
   - iPhone: Configurações → Wi‑Fi → Toque no "i" ao lado da rede
   - Veja o "Endereço IP" (deve começar com `192.168.x.x` ou `10.x.x.x`)
   - Compare com o IP do Mac - devem começar igual!
   - Exemplo:
     - Mac: `192.168.1.100`
     - iPhone: `192.168.1.105` ✅ (mesma rede!)
     - iPhone: `172.20.10.2` ❌ (rede diferente - dados móveis!)

**Teste rápido no Mac:**
```bash
# Verificar se servidor está acessível
curl http://localhost:5001/api/health

# Verificar IP do Mac
ifconfig | grep "inet " | grep -v 127.0.0.1
# Ou
ipconfig getifaddr en0
```

### **Problema: IP não aparece na mensagem**

**Solução:**
- Descubra manualmente usando os comandos acima
- O servidor ainda funciona, apenas não detectou o IP automaticamente

### **Problema: Outros não conseguem acessar**

**Soluções:**
1. Verificar firewall (ver seção acima)
2. Verificar se estão na mesma rede Wi-Fi/Ethernet
3. Verificar se o IP está correto
4. Tentar acessar de outro dispositivo na mesma rede primeiro

---

## 💡 **Dica: Usar Nome do Computador (Opcional)**

Se quiser usar um nome ao invés de IP, você pode configurar no `/etc/hosts` (Linux/macOS) ou usar um serviço de DNS local, mas o IP é mais simples para testes rápidos.

---

**Última atualização:** 13/01/2026
