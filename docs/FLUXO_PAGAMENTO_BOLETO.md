# 💳 Fluxo de Pagamento de Boleto - Análise e Implementação

**Data:** 13/01/2026  
**Status:** 📋 **ANÁLISE COMPLETA** - Pronto para implementação

---

## 🎯 Objetivo

Implementar fluxo completo de pagamento de boleto onde:

1. Usuário diz: **"maike pague esse boleto"**
2. IA abre modal para upload do boleto (PDF)
3. Sistema extrai dados do boleto (código de barras, valor, vencimento)
4. Sistema busca saldo no Santander
5. Sistema monta pagamento para aprovação
6. Usuário aprova
7. Sistema paga e guarda histórico

---

## ✅ O Que Já Temos

### 1. APIs de Pagamento
- ✅ `iniciar_bank_slip_payment_santander` - Inicia pagamento
- ✅ `efetivar_bank_slip_payment_santander` - Efetiva pagamento
- ✅ `consultar_saldo_santander` - Consulta saldo
- ✅ `consultar_bank_slip_payment_santander` - Consulta status
- ✅ `listar_bank_slip_payments_santander` - Lista histórico

### 2. Infraestrutura
- ✅ Extração de PDF (PyPDF2) - usado em legislação
- ✅ Upload de arquivos - existe para legislação
- ✅ Sistema de aprovação - existe para emails

---

## ❌ O Que Precisa Ser Implementado

### 1. **Extração de Dados do Boleto** 🔴 ALTA PRIORIDADE

**Problema:** Precisamos extrair do PDF:
- Código de barras (44 ou 47 dígitos)
- Valor do documento
- Data de vencimento
- Beneficiário (opcional)
- Nosso número (opcional)

**Solução:**
- Usar PyPDF2 para extrair texto
- Usar regex para encontrar código de barras
- Usar regex para encontrar valor e vencimento
- Criar parser específico para boletos

**Biblioteca recomendada:**
- `PyPDF2` (já temos) - para PDFs textuais
- `pdfplumber` (alternativa melhor) - melhor para tabelas
- `opencv-python` + `pytesseract` (se precisar OCR)

### 2. **Tool para Processar Upload de Boleto** 🔴 ALTA PRIORIDADE

**Nova Tool:**
```python
{
    "name": "processar_boleto_upload",
    "description": "📄 PROCESSAR BOLETO UPLOAD - Use quando o usuário enviar um PDF de boleto para pagamento. Extrai código de barras, valor, vencimento e prepara pagamento. Exemplos: 'pague esse boleto', 'processar boleto', 'pagar boleto anexado'.",
    "parameters": {
        "file_path": "string",  # Caminho do arquivo PDF
        "session_id": "string"   # ID da sessão
    }
}
```

**Fluxo:**
1. Recebe PDF do boleto
2. Extrai dados (código de barras, valor, vencimento)
3. Consulta saldo no Santander
4. Valida se tem saldo suficiente
5. Retorna dados para aprovação

### 3. **Workflow Completo com Aprovação** 🟡 MÉDIA PRIORIDADE

**Fluxo:**
```
1. Upload → Extração → Validação → Saldo
2. Mostra resumo para aprovação:
   - Valor: R$ 900,00
   - Vencimento: 08/02/2026
   - Beneficiário: PLUXEE BENEFICIOS BRASIL S.A
   - Saldo disponível: R$ 10.000,00
   - Saldo após pagamento: R$ 9.100,00
3. Usuário aprova
4. Sistema inicia pagamento
5. Sistema efetiva pagamento
6. Sistema salva histórico
```

**Componentes:**
- Modal de aprovação (similar ao de email)
- Validação de saldo
- Confirmação antes de efetivar

### 4. **Histórico de Pagamentos** 🟢 BAIXA PRIORIDADE

**Tabela SQL Server:**
```sql
CREATE TABLE PAGAMENTO_BOLETO (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    payment_id VARCHAR(255) UNIQUE NOT NULL,
    workspace_id VARCHAR(255),
    codigo_barras VARCHAR(100),
    valor DECIMAL(18,2),
    vencimento DATE,
    beneficiario VARCHAR(255),
    status VARCHAR(50), -- PENDING_VALIDATION, READY_TO_PAY, PAYED, REJECTED
    data_pagamento DATETIME,
    agencia_origem VARCHAR(10),
    conta_origem VARCHAR(20),
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE()
);
```

---

## 📋 Implementação Sugerida

### Fase 1: Extração de Dados (CRÍTICO)

**Arquivo:** `services/boleto_parser.py` (NOVO)

```python
import re
import PyPDF2
from typing import Dict, Any, Optional
from datetime import datetime

class BoletoParser:
    """Parser para extrair dados de boletos bancários."""
    
    def extrair_dados_boleto(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extrai dados do boleto do PDF.
        
        Returns:
            Dict com: codigo_barras, valor, vencimento, beneficiario, nosso_numero
        """
        # 1. Extrair texto do PDF
        texto = self._extrair_texto_pdf(pdf_path)
        
        # 2. Extrair código de barras
        codigo_barras = self._extrair_codigo_barras(texto)
        
        # 3. Extrair valor
        valor = self._extrair_valor(texto)
        
        # 4. Extrair vencimento
        vencimento = self._extrair_vencimento(texto)
        
        # 5. Extrair beneficiário
        beneficiario = self._extrair_beneficiario(texto)
        
        return {
            'codigo_barras': codigo_barras,
            'valor': valor,
            'vencimento': vencimento,
            'beneficiario': beneficiario,
            'sucesso': bool(codigo_barras and valor)
        }
    
    def _extrair_codigo_barras(self, texto: str) -> Optional[str]:
        """Extrai código de barras do texto."""
        # Padrão: números com pontos e espaços (ex: 34191.09321 64129.922932...)
        # Limpar e validar
        padrao = r'(\d{5}\.?\d{5}\s?\d{5}\.?\d{6}\s?\d{5}\.?\d{6}\s?\d\s?\d{14})'
        match = re.search(padrao, texto)
        if match:
            codigo = match.group(1)
            # Limpar pontos e espaços
            codigo_limpo = re.sub(r'[.\s]', '', codigo)
            # Validar tamanho (44 ou 47 dígitos)
            if len(codigo_limpo) in [44, 47]:
                return codigo_limpo
        return None
    
    def _extrair_valor(self, texto: str) -> Optional[float]:
        """Extrai valor do boleto."""
        # Padrão: "Valor do documento" ou "Valor" seguido de número
        padrao = r'(?:Valor\s+(?:do\s+)?documento|Valor)\s*:?\s*R?\$?\s*([\d.,]+)'
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            valor_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                return float(valor_str)
            except:
                pass
        return None
    
    def _extrair_vencimento(self, texto: str) -> Optional[str]:
        """Extrai data de vencimento."""
        # Padrão: DD/MM/YYYY
        padrao = r'Vencimento\s*:?\s*(\d{2}/\d{2}/\d{4})'
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            data_str = match.group(1)
            # Converter para YYYY-MM-DD
            try:
                dt = datetime.strptime(data_str, '%d/%m/%Y')
                return dt.strftime('%Y-%m-%d')
            except:
                pass
        return None
    
    def _extrair_beneficiario(self, texto: str) -> Optional[str]:
        """Extrai nome do beneficiário."""
        # Padrão: "Cedente" seguido de nome
        padrao = r'Cedente\s+(.+?)(?:\n|Agência|CNPJ)'
        match = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
```

### Fase 2: Tool de Processamento

**Arquivo:** `services/tool_definitions.py` (MODIFICAR)

Adicionar nova tool:
```python
{
    "name": "processar_boleto_upload",
    "description": "📄 PROCESSAR BOLETO UPLOAD - Use quando o usuário enviar um PDF de boleto para pagamento. Extrai código de barras, valor, vencimento e prepara pagamento. Exemplos: 'pague esse boleto', 'processar boleto', 'pagar boleto anexado'.",
    "parameters": {
        "file_path": {
            "type": "string",
            "description": "Caminho do arquivo PDF do boleto. Obrigatório."
        },
        "session_id": {
            "type": "string",
            "description": "ID da sessão do chat. Opcional."
        }
    },
    "required": ["file_path"]
}
```

### Fase 3: Handler no Agent

**Arquivo:** `services/agents/santander_agent.py` (MODIFICAR)

Adicionar handler:
```python
def _processar_boleto_upload(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Processa upload de boleto e prepara pagamento."""
    from services.boleto_parser import BoletoParser
    from services.santander_service import SantanderService
    
    # 1. Extrair dados do boleto
    parser = BoletoParser()
    dados = parser.extrair_dados_boleto(arguments.get('file_path'))
    
    if not dados.get('sucesso'):
        return {
            'sucesso': False,
            'erro': 'Não foi possível extrair dados do boleto',
            'resposta': '❌ Erro ao processar boleto. Verifique se o PDF está legível.'
        }
    
    # 2. Consultar saldo
    santander_service = SantanderService()
    saldo_result = santander_service.consultar_saldo()
    
    if not saldo_result.get('sucesso'):
        return {
            'sucesso': False,
            'erro': 'Erro ao consultar saldo',
            'resposta': '❌ Erro ao consultar saldo no Santander.'
        }
    
    saldo_disponivel = saldo_result.get('dados', {}).get('disponivel', 0)
    valor_boleto = dados.get('valor', 0)
    
    # 3. Validar saldo
    if saldo_disponivel < valor_boleto:
        return {
            'sucesso': False,
            'erro': 'Saldo insuficiente',
            'resposta': f'❌ Saldo insuficiente. Disponível: R$ {saldo_disponivel:,.2f}, Necessário: R$ {valor_boleto:,.2f}'
        }
    
    # 4. Preparar dados para aprovação
    resposta = f"📄 **Boleto Processado com Sucesso!**\n\n"
    resposta += f"**Código de Barras:** `{dados.get('codigo_barras')}`\n"
    resposta += f"**Valor:** R$ {valor_boleto:,.2f}\n"
    resposta += f"**Vencimento:** {dados.get('vencimento')}\n"
    if dados.get('beneficiario'):
        resposta += f"**Beneficiário:** {dados.get('beneficiario')}\n"
    resposta += f"\n**Saldo Disponível:** R$ {saldo_disponivel:,.2f}\n"
    resposta += f"**Saldo Após Pagamento:** R$ {saldo_disponivel - valor_boleto:,.2f}\n\n"
    resposta += f"💡 Use 'iniciar_bank_slip_payment_santander' para iniciar o pagamento."
    
    return {
        'sucesso': True,
        'resposta': resposta,
        'dados': {
            **dados,
            'saldo_disponivel': saldo_disponivel,
            'saldo_apos_pagamento': saldo_disponivel - valor_boleto
        },
        'acao': 'aprovar_pagamento'  # Flag para abrir modal de aprovação
    }
```

### Fase 4: Endpoint de Upload

**Arquivo:** `app.py` (MODIFICAR)

Adicionar endpoint:
```python
@app.route('/api/banco/upload-boleto', methods=['POST'])
def upload_boleto():
    """Endpoint para upload de boleto."""
    from flask import request
    import os
    import uuid
    from services.boleto_parser import BoletoParser
    
    try:
        if 'file' not in request.files:
            return jsonify({'sucesso': False, 'erro': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        session_id = request.form.get('session_id', 'default')
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'sucesso': False, 'erro': 'Apenas PDFs são permitidos'}), 400
        
        # Salvar arquivo temporariamente
        upload_dir = os.path.join('uploads', 'boletos')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_id = str(uuid.uuid4())
        file_path = os.path.join(upload_dir, f'{file_id}.pdf')
        file.save(file_path)
        
        # Processar boleto
        parser = BoletoParser()
        dados = parser.extrair_dados_boleto(file_path)
        
        # Limpar arquivo temporário
        try:
            os.remove(file_path)
        except:
            pass
        
        if dados.get('sucesso'):
            return jsonify({
                'sucesso': True,
                'dados': dados,
                'file_id': file_id
            })
        else:
            return jsonify({
                'sucesso': False,
                'erro': 'Não foi possível extrair dados do boleto'
            }), 400
            
    except Exception as e:
        logger.error(f"Erro ao processar upload de boleto: {e}", exc_info=True)
        return jsonify({'sucesso': False, 'erro': str(e)}), 500
```

---

## 🎯 Resposta à Pergunta

**Sim, é possível pagar um boleto usando os workflows disponíveis!**

**O que já funciona:**
- ✅ API de pagamento de boleto (`iniciar_bank_slip_payment_santander`, `efetivar_bank_slip_payment_santander`)
- ✅ Consulta de saldo (`consultar_saldo_santander`)
- ✅ Extração de PDF (PyPDF2)

**O que precisa ser implementado:**
1. 🔴 **Parser de boleto** - Extrair código de barras, valor, vencimento
2. 🔴 **Tool de processamento** - `processar_boleto_upload`
3. 🟡 **Workflow de aprovação** - Modal similar ao de email
4. 🟢 **Histórico de pagamentos** - Tabela SQL Server

**Estimativa de implementação:**
- Fase 1 (Parser): 2-3 horas
- Fase 2 (Tool): 1 hora
- Fase 3 (Workflow): 2-3 horas
- Fase 4 (Histórico): 1 hora

**Total:** ~6-8 horas de desenvolvimento

---

## 📝 Exemplo de Uso

**Fluxo completo:**
```
Usuário: "maike pague esse boleto"
  ↓
IA detecta intenção → chama processar_boleto_upload
  ↓
Sistema extrai dados do PDF:
  - Código: 34191093216412992293280145580009313510000090000
  - Valor: R$ 900,00
  - Vencimento: 2026-02-08
  ↓
Sistema consulta saldo: R$ 10.000,00
  ↓
Sistema mostra resumo e pede aprovação
  ↓
Usuário aprova
  ↓
Sistema inicia pagamento (payment_id gerado)
  ↓
Sistema efetiva pagamento
  ↓
Sistema salva histórico
  ↓
Sistema confirma: "✅ Boleto pago com sucesso!"
```

---

---

## 🧪 Teste no Sandbox (ANTES da Implementação Completa)

**Script de teste criado:** `scripts/teste_pagamento_boleto_sandbox.py`

Este script permite testar o fluxo completo de pagamento de boleto no sandbox **antes** de implementar toda a infraestrutura de upload e aprovação.

### Como Usar

```bash
# 1. Colocar o PDF do boleto na pasta downloads/
# Exemplo: downloads/60608-Cobranca.pdf

# 2. Executar o script
python3 scripts/teste_pagamento_boleto_sandbox.py downloads/60608-Cobranca.pdf
```

### O Que o Script Faz

1. ✅ **Extrai dados do boleto** (código de barras, valor, vencimento, beneficiário)
2. ✅ **Consulta saldo no Santander** (valida se tem saldo suficiente)
3. ✅ **Inicia pagamento no sandbox** (cria payment_id)
4. ✅ **Efetiva pagamento no sandbox** (confirma e autoriza)
5. ✅ **Consulta status do pagamento** (verifica resultado final)

### Exemplo de Saída

```
🧪 TESTE DE PAGAMENTO DE BOLETO - SANDBOX SANTANDER
============================================================

📋 FASE 1: Extração de Dados do Boleto
------------------------------------------------------------
📄 Processando boleto: downloads/60608-Cobranca.pdf
✅ Texto extraído: 2847 caracteres
🔍 Código de barras: 34191093216412992293280145580009313510000090000
💰 Valor: R$ 900,00
📅 Vencimento: 2026-02-08
👤 Beneficiário: PLUXEE BENEFICIOS BRASIL S.A
✅ Dados extraídos com sucesso!

💰 FASE 2: Consulta de Saldo
------------------------------------------------------------
✅ Saldo disponível: R$ 10.000,00
✅ Saldo após pagamento: R$ 9.100,00

🚀 FASE 3: Iniciar Pagamento no Sandbox
------------------------------------------------------------
📝 Payment ID gerado: 4ef8791d-415a-4987-9206-4553a8f1d609
📅 Data de pagamento: 2026-01-13
✅ Pagamento iniciado com sucesso!
   Status: PENDING_VALIDATION

✅ FASE 4: Efetivar Pagamento no Sandbox
------------------------------------------------------------
✅ Pagamento efetivado com sucesso!
   Status: AUTHORIZED

🔍 FASE 5: Consultar Status do Pagamento
------------------------------------------------------------
✅ Status do pagamento consultado!
   Resposta: 📋 Consulta de Pagamento de Boleto
   ID: 4ef8791d-415a-4987-9206-4553a8f1d609
   Status: AUTHORIZED

============================================================
✅ TESTE CONCLUÍDO COM SUCESSO!
============================================================

📊 Resumo:
   • Código de barras: 34191093216412992293280145580009313510000090000
   • Valor: R$ 900,00
   • Vencimento: 2026-02-08
   • Beneficiário: PLUXEE BENEFICIOS BRASIL S.A
   • Payment ID: 4ef8791d-415a-4987-9206-4553a8f1d609
   • Status final: AUTHORIZED

⚠️ LEMBRE-SE: Este é um teste no SANDBOX - nenhum dinheiro foi movimentado!
```

### Vantagens do Teste no Sandbox

- ✅ **Validação completa** do fluxo antes de implementar UI
- ✅ **Teste seguro** - nenhum dinheiro real é movimentado
- ✅ **Debug fácil** - vê cada etapa do processo
- ✅ **Valida parser** - confirma que extração de dados funciona
- ✅ **Valida API** - confirma que pagamento funciona no sandbox

---

**Última atualização:** 13/01/2026
