# ⚖️ Procedimento de Auditoria: Origem de Recursos (IN RFB nº 1986/2020)

**Data:** 24/01/2026  
**Status:** 🔴 CRÍTICO / COMPLIANCE  
**Objetivo:** Garantir a rastreabilidade total da origem lícita dos recursos utilizados para pagamento de tributos aduaneiros, mitigando o risco de crime de interposição fraudulenta.

---

## 1. Contexto Legal: IN RFB nº 1986/2020

A **Instrução Normativa RFB nº 1.986/2020** disciplina o procedimento de fiscalização de combate às fraudes aduaneiras. Um dos pontos mais sensíveis para a Receita Federal é a **Ocultação do Sujeito Passivo** (Interposição Fraudulenta).

### ⚠️ O Risco Jurídico e Criminal
*   **Interposição Fraudulenta:** Ocorre quando uma empresa utiliza seus próprios recursos ou conta bancária para pagar impostos de terceiros sem a devida comprovação de que o dinheiro veio originalmente do importador de fato.
*   **Consequências:** 
    *   Retenção da mercadoria (Canal Cinza).
    *   Pena de perdimento da carga.
    *   Representação fiscal para fins penais (pode ser tipificado como **crime contra a ordem tributária**).
    *   Multas pesadas e cancelamento do RADAR.

---

## 2. Estratégia de Blindagem: Saldo Virtual por Cliente

Para processos onde os recursos de vários clientes transitam pela conta da empresa (ex: Banco do Brasil), o sistema mAIke implementa a lógica de **Subcontas Virtuais**.

### A. Identificação do Aporte (Entrada/Crédito)
Todo crédito identificado no extrato bancário deve ser classificado por sua **Natureza Jurídica**:

1.  **[VENDA]**: Recursos próprios da empresa oriundos de Notas Fiscais de Venda. Estes recursos **NÃO** podem ser usados para lastrear pagamentos de impostos de clientes.
2.  **[APORTE_TRIBUTOS]**: Recursos de terceiros destinados especificamente ao pagamento de impostos e taxas aduaneiras.
3.  **Detecção Automática:** O sistema usa o CNPJ da contrapartida (PIX/TED) e cruza com valores de DIs/DUIMPs abertas para sugerir a classificação correta.
4.  **Alimentação de Saldo:** Apenas valores classificados como `APORTE_TRIBUTOS` alimentam o **Saldo de Recursos** (Carteira Virtual) do cliente.

### B. Lastro do Pagamento (Saída/Débito)
Ao classificar um débito como "Impostos de Importação" (Siscomex/PUCOMEX):
1.  **Verificação de Disponibilidade:** O sistema verifica se o cliente detentor da categoria (ex: ALH, BND) possui saldo na sua **Carteira Virtual** (proveniente de aportes prévios).
2.  **Vínculo de Auditoria:** O débito é "lastreado" no crédito original de aporte. O sistema registra: *"O pagamento de R$ 13.337,88 foi realizado utilizando o recurso aportado via TED em [DATA] pelo Cliente X"*.
3.  **Segregação de Patrimônio:** O sistema garante que recursos de [VENDA] nunca sejam misturados com recursos de [APORTE_TRIBUTOS] no relatório de auditoria.

---

## 3. Regras de Operação para o Agente de IA

O Agente mAIke deve seguir rigorosamente estas diretrizes ao lidar com conciliação:

1.  **Prioridade de Crédito:** Nunca sugerir a classificação de um imposto sem antes verificar se houve uma entrada de recurso compatível daquele cliente.
2.  **Alerta de Risco:** Caso o usuário tente vincular um pagamento de imposto sem saldo virtual suficiente do cliente, o Agente deve emitir um aviso de **Risco de Compliance (IN 1986)**.
3.  **Dossiê de Auditoria:** O Agente deve ser capaz de gerar um resumo mostrando:
    *   Total de aportes do cliente no período.
    *   Total de impostos pagos com esses aportes.
    *   Saldo remanescente.

---

## 4. Estrutura de Dados Relacionada

*   **Tabela `MOVIMENTACAO_BANCARIA`**: Armazena os lançamentos brutos.
*   **Tabela `SALDO_RECURSO_CLIENTE`**: Mantém o saldo acumulado por CNPJ.
*   **Tabela `LANCAMENTO_TIPO_DESPESA`**: Vincula o débito ao processo e, consequentemente, ao cliente.

---

**⚠️ NOTA DE SEGURANÇA:**  
Erros nesta conciliação não são apenas falhas operacionais; eles expõem a empresa a riscos criminais. O sistema deve ser tratado como uma ferramenta de **prova documental** para auditorias da Receita Federal.
