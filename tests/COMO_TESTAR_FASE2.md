# 🧪 Como Testar a Fase 2 do Passo 3

**Data:** 09/01/2026

---

## 📋 O Que Foi Implementado na Fase 2

1. ✅ **Detecção de comandos de interface** (`_detectar_comando_interface`)
   - Detecta "maike menu", "maike quero conciliar banco", etc.
   - Retorna `ProcessingResult` com `comando_interface` preenchido

2. ✅ **Detecção de melhorar email** (`_detectar_melhorar_email`)
   - Detecta "melhore", "elabore", "reescreva", etc.
   - Retorna flag `eh_pedido_melhorar_email` no `ProcessingResult`

3. ✅ **ProcessingResult melhorado**
   - Método `to_dict()` para compatibilidade
   - Flag `eh_pedido_melhorar_email` adicionada

---

## 🚀 Como Rodar os Testes

### **1. Instalar pytest (se ainda não tiver):**
```bash
pip install pytest
```

### **2. Rodar todos os testes da Fase 2:**
```bash
pytest tests/test_message_processing_service_fase2.py -v
```

### **3. Rodar um teste específico:**
```bash
# Teste de detecção de menu
pytest tests/test_message_processing_service_fase2.py::TestMessageProcessingServiceFase2::test_detectar_comando_menu -v

# Teste de detecção de melhorar email
pytest tests/test_message_processing_service_fase2.py::TestMessageProcessingServiceFase2::test_detectar_melhorar_email_com_email_pendente -v
```

### **4. Rodar com mais detalhes:**
```bash
pytest tests/test_message_processing_service_fase2.py -v -s
```

---

## 📝 Testes Disponíveis

### **Testes de Comandos de Interface:**
1. `test_detectar_comando_menu` - Detecta "maike menu"
2. `test_detectar_comando_conciliação` - Detecta "maike quero conciliar banco"
3. `test_nao_detectar_comando_em_mensagem_normal` - Não detecta em mensagem normal

### **Testes de Melhorar Email:**
4. `test_detectar_melhorar_email_com_email_pendente` - Detecta quando há email pendente
5. `test_detectar_melhorar_email_variacoes` - Testa diferentes variações
6. `test_nao_detectar_melhorar_email_sem_email_pendente` - Não detecta sem email pendente
7. `test_nao_detectar_melhorar_email_em_mensagem_normal` - Não detecta em mensagem normal

### **Testes de ProcessingResult:**
8. `test_processing_result_to_dict` - Testa conversão para dict

### **Testes de Integração:**
9. `test_comando_interface_tem_prioridade_sobre_melhorar_email` - Testa prioridade

---

## ✅ Resultado Esperado

Todos os testes devem passar (9 testes):

```
tests/test_message_processing_service_fase2.py::TestMessageProcessingServiceFase2::test_detectar_comando_menu PASSED
tests/test_message_processing_service_fase2.py::TestMessageProcessingServiceFase2::test_detectar_comando_conciliação PASSED
tests/test_message_processing_service_fase2.py::TestMessageProcessingServiceFase2::test_nao_detectar_comando_em_mensagem_normal PASSED
tests/test_message_processing_service_fase2.py::TestMessageProcessingServiceFase2::test_detectar_melhorar_email_com_email_pendente PASSED
tests/test_message_processing_service_fase2.py::TestMessageProcessingServiceFase2::test_detectar_melhorar_email_variacoes PASSED
tests/test_message_processing_service_fase2.py::TestMessageProcessingServiceFase2::test_nao_detectar_melhorar_email_sem_email_pendente PASSED
tests/test_message_processing_service_fase2.py::TestMessageProcessingServiceFase2::test_nao_detectar_melhorar_email_em_mensagem_normal PASSED
tests/test_message_processing_service_fase2.py::TestMessageProcessingServiceFase2::test_processing_result_to_dict PASSED
tests/test_message_processing_service_fase2.py::TestMessageProcessingServiceFase2::test_comando_interface_tem_prioridade_sobre_melhorar_email PASSED

======================== 9 passed in X.XXs ========================
```

---

## 🔧 Se Der Erro

### **Erro: "pytest: command not found"**
```bash
pip install pytest
```

### **Erro: "ModuleNotFoundError: No module named 'services.message_processing_service'"**
```bash
# Certifique-se de estar no diretório raiz do projeto
cd /Users/helenomaffra/Chat-IA-Independente
pytest tests/test_message_processing_service_fase2.py -v
```

### **Erro: "ImportError: cannot import name 'MessageProcessingService'"**
- Verifique se `services/message_processing_service.py` existe
- Verifique se não há erros de sintaxe no arquivo

---

## 💡 Teste Manual (Opcional)

Se quiser testar manualmente sem pytest, você pode criar um script simples:

```python
# test_manual_fase2.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from services.message_processing_service import MessageProcessingService

# Criar instância
service = MessageProcessingService()

# Teste 1: Detectar comando de menu
resultado = service.processar_core("maike menu", historico=[], session_id='test')
print(f"Comando detectado: {resultado.comando_interface}")
print(f"Resposta: {resultado.resposta}")

# Teste 2: Detectar melhorar email
email_pendente = {'destinatarios': ['test@example.com'], 'assunto': 'Teste', 'conteudo': 'Teste'}
resultado = service.processar_core(
    "melhore o email",
    historico=[],
    session_id='test',
    ultima_resposta_aguardando_email=email_pendente
)
print(f"Melhorar email detectado: {resultado.eh_pedido_melhorar_email}")

# Teste 3: to_dict()
resultado_dict = resultado.to_dict()
print(f"Resultado como dict: {resultado_dict.keys()}")
```

Execute:
```bash
python3 test_manual_fase2.py
```

---

**Última atualização:** 09/01/2026
