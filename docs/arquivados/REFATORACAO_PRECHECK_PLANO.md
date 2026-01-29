# Plano de Refatoração do PrecheckService

## Estrutura Proposta

### 1. EmailPrecheckService (`services/email_precheck_service.py`)
- `tentar_precheck_email()` - método principal que orquestra
- `_precheck_envio_email_ncm()` - email de NCM + alíquotas
- `_precheck_envio_email_relatorio_generico()` - relatório genérico
- `_precheck_envio_email()` - resumo/briefing específico
- `_precheck_envio_email_livre()` - email livre
- `_precheck_envio_email_processo()` - email de processo/NCM misturado

### 2. ProcessoPrecheckService (`services/processo_precheck_service.py`)
- `precheck_situacao()` - situação/detalhe de processo
- `precheck_followup()` - follow-up contextual de processo

### 3. NcmPrecheckService (`services/ncm_precheck_service.py`)
- `precheck_tecwin_ncm()` - consulta TECwin NCM
- `eh_pergunta_ncm()` - verifica se é pergunta de NCM

### 4. PrecheckService Principal (refatorado)
- Mantém apenas orquestração
- Ordem de chamadas (mantida):
  1. TECwin NCM
  2. Follow-up processo
  3. Situação processo
  4. Email (todos os tipos via EmailPrecheckService)
  5. Pergunta NCM (só marca, não responde)

## Ordem de Implementação

1. ✅ Criar EmailPrecheckService (parcial - já criado)
2. ⏳ Completar EmailPrecheckService (mover métodos restantes)
3. ⏳ Criar ProcessoPrecheckService
4. ⏳ Criar NcmPrecheckService
5. ⏳ Refatorar PrecheckService principal
6. ⏳ Criar testes automatizados

## Notas Importantes

- Manter EXATAMENTE a mesma ordem de prechecks
- Não alterar comportamento (apenas organização)
- Manter todos os logs
- Manter formato de retorno (sucesso, resposta, _processado_precheck, etc.)

