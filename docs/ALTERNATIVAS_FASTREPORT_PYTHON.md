# 🎨 Alternativas ao FastReport em Python

**Data:** 26/01/2026  
**Contexto:** Busca por ferramenta visual de design de relatórios (drag-and-drop) similar ao FastReport

---

## 📋 Situação Atual

**FastReport (Delphi/C#):**
- ✅ Designer visual (drag-and-drop)
- ✅ Cria template visualmente
- ✅ Depois só preenche com dados
- ✅ Fácil de usar, não precisa programar layout

**Sistema Atual (Python):**
- ❌ Template HTML/CSS manual (`templates/extrato_di.html`)
- ❌ Precisa editar código HTML/CSS
- ❌ Não tem designer visual
- ✅ Usa Jinja2 para preencher dados

---

## 🎯 Alternativas em Python

### **1. Stimulsoft Reports.PYTHON** ⭐ **MAIS PARECIDO COM FASTREPORT**

**Características:**
- ✅ **Designer visual** (igual FastReport)
- ✅ Drag-and-drop de elementos
- ✅ Template visual + dados depois
- ✅ Suporta Python 3.10+
- ✅ Gera PDF, Excel, HTML, etc.

**Como funciona:**
```python
from stimulsoft.reports import StiReport

# 1. Criar template no designer visual (arquivo .mrt)
report = StiReport()
report.loadFile('template_di.mrt')  # Template criado visualmente

# 2. Preencher com dados
report.regData('dados_di', dados_di)
report.render()

# 3. Exportar PDF
report.exportDocument(StiExportFormat.Pdf, 'extrato_di.pdf')
```

**Vantagens:**
- ✅ **Mais próximo do FastReport** (designer visual)
- ✅ Não precisa programar layout
- ✅ Template separado do código
- ✅ Fácil de manter

**Desvantagens:**
- ⚠️ **Comercial** (pago)
- ⚠️ Requer licença

**Preço:** ~$500-1000 (licença única)

**Link:** https://stimulsoft.com/en/products/reports-python

---

### **2. ZipReport** ⭐ **GRATUITO E OPEN SOURCE**

**Características:**
- ✅ Designer baseado em HTML/CSS
- ✅ Template HTML com Jinja2
- ✅ Suporta CSS3 completo
- ✅ **Gratuito e open source**
- ✅ Pode usar ferramentas visuais HTML (Dreamweaver, etc.)

**Como funciona:**
```python
from zipreport import ZipReport

# 1. Criar template HTML (pode usar designer visual HTML)
# template.html com Jinja2: {{ di.numero }}, {{ di.importador.nome }}

# 2. Gerar PDF
report = ZipReport('template.html')
report.render({'di': dados_di})
report.save('extrato_di.pdf')
```

**Vantagens:**
- ✅ **Gratuito**
- ✅ Open source
- ✅ Pode usar qualquer editor HTML visual
- ✅ CSS completo (melhor que xhtml2pdf)

**Desvantagens:**
- ⚠️ Não tem designer próprio (usa HTML)
- ⚠️ Precisa conhecer HTML/CSS

**Link:** https://zipreport.github.io/zipreport/

---

### **3. ReportLab + Designer Visual (Custom)**

**Características:**
- ✅ ReportLab é a biblioteca mais poderosa para PDF em Python
- ✅ Pode criar designer visual customizado
- ✅ Controle total sobre layout

**Como funciona:**
```python
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

# Criar PDF programaticamente
c = canvas.Canvas("extrato_di.pdf", pagesize=A4)

# Logo
c.drawImage("logo_receita.png", 2*cm, 27*cm, width=4*cm, height=2*cm)

# Título
c.setFont("Helvetica-Bold", 16)
c.drawString(7*cm, 28*cm, "DECLARAÇÃO DE IMPORTAÇÃO")

# Dados
c.setFont("Helvetica", 10)
c.drawString(2*cm, 25*cm, f"DI: {dados_di['numero']}")
c.drawString(2*cm, 24*cm, f"Importador: {dados_di['importador']['nome']}")

c.save()
```

**Vantagens:**
- ✅ **Controle pixel-perfect**
- ✅ Suporte nativo a imagens/logos
- ✅ Gratuito
- ✅ Muito usado em produção

**Desvantagens:**
- ❌ **Não tem designer visual** (precisa programar)
- ❌ Layout é código Python

**Link:** https://www.reportlab.com/

---

### **4. WeasyPrint + HTML Designer**

**Características:**
- ✅ HTML/CSS → PDF (igual navegador)
- ✅ CSS completo (flexbox, grid, etc.)
- ✅ Pode usar qualquer designer HTML visual
- ✅ Gratuito

**Como funciona:**
```python
from weasyprint import HTML

# Template HTML (pode criar visualmente com Dreamweaver, etc.)
html = render_template('extrato_di.html', di=dados_di)

# Gerar PDF
HTML(string=html).write_pdf('extrato_di.pdf')
```

**Vantagens:**
- ✅ **CSS completo** (melhor que xhtml2pdf)
- ✅ Pode usar designer HTML visual
- ✅ Gratuito
- ✅ Logos/imagens funcionam perfeitamente

**Desvantagens:**
- ⚠️ Não tem designer próprio (usa HTML)
- ⚠️ Precisa conhecer HTML/CSS

**Link:** https://weasyprint.org/

---

### **5. FastReport Online Designer (via API)**

**Características:**
- ✅ **FastReport Online Designer** (browser-based)
- ✅ Designer visual real do FastReport
- ✅ Pode usar via API/Web

**Como funciona:**
1. Criar template no FastReport Online Designer (browser)
2. Salvar template
3. Chamar API do FastReport para gerar PDF com dados

**Vantagens:**
- ✅ **Designer visual real do FastReport**
- ✅ Familiar se já usa FastReport

**Desvantagens:**
- ⚠️ Requer servidor FastReport
- ⚠️ Comercial (pago)
- ⚠️ Mais complexo de integrar

**Link:** https://www.fast-report.com/products/online-designer

---

## 💡 Recomendações por Cenário

### **Se você quer algo EXATAMENTE como FastReport:**
→ **Stimulsoft Reports.PYTHON**
- Designer visual igual
- Template separado do código
- Mais fácil de manter

### **Se você quer GRATUITO e pode usar HTML:**
→ **ZipReport** ou **WeasyPrint**
- Gratuito
- Pode usar designer HTML visual (Dreamweaver, etc.)
- CSS completo

### **Se você quer CONTROLE TOTAL:**
→ **ReportLab**
- Pixel-perfect
- Logos/imagens nativos
- Mas precisa programar layout

### **Se você quer MELHORAR O ATUAL (xhtml2pdf):**
→ **WeasyPrint**
- Substitui xhtml2pdf
- CSS completo
- Logos funcionam
- Mantém template HTML

---

## 🚀 Migração Sugerida

### **Opção A: WeasyPrint (Mais Simples)**

**Vantagem:** Substitui `xhtml2pdf` sem mudar muito código

```python
# Antes (xhtml2pdf):
from xhtml2pdf import pisa
pisa.CreatePDF(html, dest=arquivo_pdf)

# Depois (WeasyPrint):
from weasyprint import HTML
HTML(string=html).write_pdf('extrato_di.pdf')
```

**Mudanças necessárias:**
1. Instalar: `pip install weasyprint`
2. Trocar `xhtml2pdf` por `weasyprint` em `di_pdf_service.py`
3. Template HTML pode usar CSS completo (flexbox, grid, etc.)
4. Logos/imagens funcionam perfeitamente

**Tempo:** ~30 minutos

---

### **Opção B: Stimulsoft (Mais Visual)**

**Vantagem:** Designer visual igual FastReport

**Mudanças necessárias:**
1. Instalar: `pip install stimulsoft-reports-python`
2. Criar template visual no Stimulsoft Designer
3. Modificar `di_pdf_service.py` para usar Stimulsoft
4. Template separado do código

**Tempo:** ~2-3 horas (incluindo aprender Stimulsoft)

---

## 📝 Exemplo: Como Ficaria com WeasyPrint

**Template HTML (pode editar visualmente):**
```html
<!-- templates/extrato_di.html -->
<!DOCTYPE html>
<html>
<head>
  <style>
    @page {
      size: A4;
      margin: 2cm;
      @top-center {
        content: url('static/logo_receita.png');
        width: 150px;
      }
    }
    
    .header {
      text-align: center;
      border-bottom: 2px solid #000;
      padding-bottom: 10px;
      margin-bottom: 20px;
    }
    
    .logo {
      width: 200px;
      height: auto;
    }
  </style>
</head>
<body>
  <div class="header">
    <img src="{{ url_for('static', filename='logo_receita.png') }}" class="logo" />
    <h1>DECLARAÇÃO DE IMPORTAÇÃO</h1>
  </div>
  
  <div class="info">
    <p><strong>DI:</strong> {{ di.numero }}</p>
    <p><strong>Importador:</strong> {{ di.importador.nome }}</p>
  </div>
</body>
</html>
```

**Código Python:**
```python
from weasyprint import HTML
from flask import render_template

html = render_template('extrato_di.html', di=dados_di)
HTML(string=html).write_pdf('extrato_di.pdf')
```

---

## 🎯 Próximos Passos

**Qual opção você prefere?**

1. **WeasyPrint** - Substitui xhtml2pdf, CSS completo, logos funcionam
2. **Stimulsoft** - Designer visual igual FastReport (pago)
3. **ZipReport** - Gratuito, HTML/CSS, pode usar designer HTML
4. **ReportLab** - Controle total, mas precisa programar layout

**Recomendação:** Começar com **WeasyPrint** (mais simples, gratuito, resolve problemas de logos) e depois avaliar Stimulsoft se precisar de designer visual.
