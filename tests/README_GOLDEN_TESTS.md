# 🧪 Golden Tests - Passo 0 da Refatoração

**Data:** 09/01/2026  
**Status:** ⏳ **EM DESENVOLVIMENTO** - Estrutura básica criada

---

## 📋 Objetivo

Estes testes servem como **"airbag"** durante a refatoração do `chat_service.py`. Eles garantem que funcionalidades críticas não quebram quando extraímos código para novos serviços.

---

## 🗂️ Estrutura dos Testes

### **Arquivos Criados:**

1. **`test_email_flows_golden.py`**
   - Testes para fluxos críticos de email
   - 6 testes planejados (estrutura básica criada)
   - Helpers para criar/verificar drafts

2. **`test_duimp_flows_golden.py`**
   - Testes para fluxos críticos de DUIMP
   - 2 testes planejados (estrutura básica criada)

### **Testes Planejados:**

#### **Email Flows:**
- ✅ `test_criar_email_preview_confirmar_enviado` - Fluxo completo
- ✅ `test_criar_email_melhorar_confirmar_enviar_melhorado` - Melhoria de email
- ✅ `test_criar_email_corrigir_destinatario_confirmar_enviar` - Correção de destinatário
- ✅ `test_enviar_relatorio_preview_confirmar_enviado` - Envio de relatório
- ✅ `test_idempotencia_confirmar_duas_vezes_nao_duplica` - Idempotência
- ✅ `test_confirmacao_funciona_igual_streaming_e_normal` - Streaming vs Normal

#### **DUIMP Flows:**
- ✅ `test_criar_duimp_preview_confirmar_criada` - Fluxo completo
- ✅ `test_criar_duimp_cancelar_nova_duimp` - Cancelamento

---

## 🚀 Como Usar

### **Executar Todos os Testes:**

```bash
# Executar todos os golden tests
pytest tests/test_email_flows_golden.py tests/test_duimp_flows_golden.py -v

# Executar apenas testes de email
pytest tests/test_email_flows_golden.py -v

# Executar apenas testes de DUIMP
pytest tests/test_duimp_flows_golden.py -v
```

### **Executar Teste Específico:**

```bash
# Teste específico de email
pytest tests/test_email_flows_golden.py::TestEmailFlowsGolden::test_criar_email_preview_confirmar_enviado -v

# Teste específico de DUIMP
pytest tests/test_duimp_flows_golden.py::TestDuimpFlowsGolden::test_criar_duimp_preview_confirmar_criada -v
```

### **Com Cobertura:**

```bash
pytest tests/test_email_flows_golden.py tests/test_duimp_flows_golden.py --cov=services --cov-report=html -v
```

---

## ⚠️ Status Atual

**Estrutura básica criada, mas testes ainda não implementados.**

Todos os testes estão marcados com `pytest.skip()` e contêm `# TODO: Implementar teste`.

**Próximos passos:**
1. Implementar mocks necessários (AI Service, Email Service, DuimpAgent)
2. Implementar fixtures para ChatService
3. Implementar cada teste seguindo a documentação em `docs/TESTES_GOLDEN_TESTS.md`
4. Validar que testes passam antes de continuar refatoração

---

## 📚 Documentação Relacionada

- **`docs/TESTES_GOLDEN_TESTS.md`** - Documentação completa dos testes sugeridos
- **`docs/ANALISE_REFATORACAO_CHAT_SERVICE.md`** - Plano de refatoração completo

---

## 🔧 Helpers Disponíveis

### **Email Drafts:**
- `criar_draft_teste()` - Cria draft de teste
- `verificar_draft_existe()` - Verifica se draft existe
- `verificar_draft_status()` - Verifica status do draft
- `limpar_drafts_teste()` - Limpa drafts de teste

---

## ✅ Checklist de Implementação

- [x] Estrutura básica dos arquivos criada
- [x] Fixtures básicas definidas
- [x] Helpers criados
- [ ] Mocks implementados (AI Service, Email Service, DuimpAgent)
- [ ] Fixtures do ChatService implementadas
- [ ] Teste 1.1 implementado
- [ ] Teste 1.2 implementado
- [ ] Teste 1.3 implementado
- [ ] Teste 1.4 implementado
- [ ] Teste 1.5 implementado
- [ ] Teste 1.6 implementado
- [ ] Teste 2.1 implementado
- [ ] Teste 2.2 implementado
- [ ] Todos os testes passando
- [ ] Documentação atualizada

---

**Última atualização:** 09/01/2026
