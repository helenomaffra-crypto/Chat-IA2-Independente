# 🖼️ OpenAI Vision API para Extração de Boletos

**Data:** 13/01/2026  
**Status:** ✅ **IMPLEMENTADO**

---

## 📋 Visão Geral

Implementação de extração de dados de boletos usando **OpenAI Vision API (GPT-4o)** como fallback quando métodos tradicionais (pdfplumber, PyPDF2) falham.

---

## 🎯 Por que usar OpenAI Vision?

### Problema
Alguns PDFs de boletos têm texto renderizado como **formas vetoriais** (não texto selecionável), então:
- ❌ `pdfplumber` não consegue extrair
- ❌ `PyPDF2` não consegue extrair
- ✅ **OpenAI Vision** consegue "ver" e extrair o texto

### Solução
- ✅ Converter PDF para imagem (PNG)
- ✅ Enviar para GPT-4o Vision
- ✅ Extrair dados estruturados (código de barras, valor, vencimento, beneficiário)

---

## 💰 Custo

**Aproximadamente:** $0.01 - $0.03 por boleto
- Depende da resolução da imagem
- GPT-4o Vision: ~$0.01 por imagem (1024x1024)
- Conversão PDF→imagem: grátis (local)

**Comparação:**
- Tesseract OCR: grátis, mas menos preciso
- Google Vision API: ~$0.0015 por imagem
- AWS Textract: ~$0.0015 por página

---

## 🔧 Como Funciona

### 1. **Fluxo Automático**

```
PDF → pdfplumber (tenta extrair texto)
  ↓ (falha)
PDF → PyPDF2 (tenta extrair texto)
  ↓ (falha)
PDF → OpenAI Vision (converte para imagem e processa)
  ↓ (sucesso)
Dados extraídos: código de barras, valor, vencimento, beneficiário
```

### 2. **Arquivos**

- `services/boleto_parser.py` - Parser principal (já integrado)
- `services/boleto_parser_vision.py` - Parser usando Vision API (novo)

### 3. **Dependências**

```bash
pip install pdf2image pillow openai
```

**Nota:** `pdf2image` requer `poppler`:
- macOS: `brew install poppler`
- Linux: `sudo apt-get install poppler-utils`
- Windows: Baixar de https://github.com/oschwartz10612/poppler-windows/releases

---

## 📝 Como Usar

### Automático (Recomendado)

O sistema tenta automaticamente quando o PDF não pode ser extraído:

1. Usuário anexa PDF no chat
2. Sistema tenta `pdfplumber` → falha
3. Sistema tenta `PyPDF2` → falha
4. Sistema tenta **OpenAI Vision** → sucesso ✅
5. Dados extraídos e pagamento iniciado

### Manual (Opcional)

```python
from services.boleto_parser_vision import BoletoParserVision

parser = BoletoParserVision()
resultado = parser.extrair_dados_boleto_vision('boleto.pdf')

if resultado.get('sucesso'):
    print(f"Código: {resultado['codigo_barras']}")
    print(f"Valor: R$ {resultado['valor']:,.2f}")
    print(f"Vencimento: {resultado['vencimento']}")
```

---

## ⚙️ Configuração

### 1. **Variáveis de Ambiente**

```env
# Já configurado (mesmo do chat)
DUIMP_AI_ENABLED=true
DUIMP_AI_PROVIDER=openai
DUIMP_AI_API_KEY=sk-...
```

### 2. **Instalar Dependências**

```bash
# Python
pip install pdf2image pillow

# Sistema (poppler)
brew install poppler  # macOS
# ou
sudo apt-get install poppler-utils  # Linux
```

---

## 🧪 Teste

```bash
python3 -c "
from services.boleto_parser import BoletoParser
parser = BoletoParser()
resultado = parser.extrair_dados_boleto('downloads/60608-Cobranca.pdf')
print(resultado)
"
```

**Resultado esperado:**
```python
{
    'sucesso': True,
    'codigo_barras': '34191093216412992293280145580009313510000090000',
    'valor': 900.0,
    'vencimento': '2026-02-08',
    'beneficiario': 'PLUXEE BENEFICIOS BRASIL S.A',
    'metodo': 'openai_vision'
}
```

---

## 📊 Comparação de Métodos

| Método | Precisão | Custo | Velocidade | Complexidade |
|--------|----------|-------|------------|---------------|
| **pdfplumber** | ⭐⭐⭐⭐ | Grátis | ⚡⚡⚡⚡⚡ | 🟢 Baixa |
| **PyPDF2** | ⭐⭐⭐ | Grátis | ⚡⚡⚡⚡⚡ | 🟢 Baixa |
| **OpenAI Vision** | ⭐⭐⭐⭐⭐ | $0.01-0.03 | ⚡⚡⚡ | 🟡 Média |
| **Tesseract OCR** | ⭐⭐⭐ | Grátis | ⚡⚡⚡ | 🔴 Alta |
| **Google Vision** | ⭐⭐⭐⭐ | $0.0015 | ⚡⚡⚡⚡ | 🟡 Média |

---

## 🎯 Quando Usar Cada Método

### 1. **pdfplumber/PyPDF2** (Primeiro)
- ✅ PDFs com texto selecionável
- ✅ Mais rápido e grátis
- ❌ Falha em PDFs vetoriais

### 2. **OpenAI Vision** (Fallback)
- ✅ PDFs vetoriais/escaneados
- ✅ Alta precisão
- ⚠️ Custo por uso
- ⚠️ Requer internet

### 3. **Dados Manuais** (Alternativa)
- ✅ Sempre funciona
- ✅ Grátis
- ⚠️ Requer entrada manual

---

## 🚀 Próximos Passos (Opcional)

1. **Cache de resultados** - Evitar reprocessar mesmo PDF
2. **Batch processing** - Processar múltiplos boletos de uma vez
3. **Fallback para Tesseract** - Se Vision API falhar
4. **Métricas de custo** - Monitorar gastos com Vision API

---

**Última atualização:** 13/01/2026
