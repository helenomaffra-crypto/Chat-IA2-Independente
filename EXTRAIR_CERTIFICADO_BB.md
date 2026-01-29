# 🔐 Guia: Extrair Cadeia de Certificados para Banco do Brasil

## 📁 Arquivo de Entrada

- **Arquivo**: `.secure/eCNPJ 4PL (valid 23-03-26) senha001.pfx`
- **Senha**: `senha001`

## 🛠️ Comandos OpenSSL

Execute estes comandos no terminal (na raiz do projeto):

### 1. Criar diretório para os certificados

```bash
# O diretório .secure está na raiz do projeto
cd /Users/helenomaffra/Chat-IA-Independente/.secure
mkdir -p certificados_bb
cd certificados_bb
```

### 2. Extrair Certificado da Empresa

⚠️ **Se der erro de algoritmo não suportado (RC2-40-CBC)**, use a flag `-legacy`:

```bash
# OpenSSL 3.0+ (com suporte a algoritmos legados)
openssl pkcs12 -in "../eCNPJ 4PL (valid 23-03-26) senha001.pfx" \
  -clcerts -nokeys -out certificado_empresa.pem \
  -passin pass:senha001 -legacy

# Se ainda não funcionar, tente com provider legacy
openssl pkcs12 -provider legacy -provider default \
  -in "../eCNPJ 4PL (valid 23-03-26) senha001.pfx" \
  -clcerts -nokeys -out certificado_empresa.pem \
  -passin pass:senha001
```

### 3. Extrair Cadeia Completa (Intermediários + Raiz)

```bash
# OpenSSL 3.0+ (com suporte a algoritmos legados)
openssl pkcs12 -in "../eCNPJ 4PL (valid 23-03-26) senha001.pfx" \
  -cacerts -nokeys -out cadeia_completa.pem \
  -passin pass:senha001 -legacy

# Se ainda não funcionar, tente com provider legacy
openssl pkcs12 -provider legacy -provider default \
  -in "../eCNPJ 4PL (valid 23-03-26) senha001.pfx" \
  -cacerts -nokeys -out cadeia_completa.pem \
  -passin pass:senha001
```

### 4. Verificar Certificados Extraídos

```bash
# Ver certificado da empresa
openssl x509 -in certificado_empresa.pem -noout -subject -issuer -dates

# Ver cadeia completa
openssl x509 -in cadeia_completa.pem -noout -subject -issuer -dates
```

### 5. Separar Certificados Intermediários e Raiz

A cadeia completa pode conter múltiplos certificados. Para separá-los:

```bash
# Contar quantos certificados há na cadeia
grep -c "BEGIN CERTIFICATE" cadeia_completa.pem
```

Se houver múltiplos certificados, você pode separá-los manualmente ou usar este script Python:

```python
# separar_certificados.py
with open('cadeia_completa.pem', 'r') as f:
    content = f.read()

certificados = []
current = []
in_cert = False

for line in content.split('\n'):
    if '-----BEGIN CERTIFICATE-----' in line:
        in_cert = True
        current = [line]
    elif '-----END CERTIFICATE-----' in line:
        current.append(line)
        certificados.append('\n'.join(current))
        current = []
        in_cert = False
    elif in_cert:
        current.append(line)

# Salvar intermediários (todos exceto o último)
if len(certificados) > 1:
    with open('certificado_intermediario.pem', 'w') as f:
        for cert in certificados[:-1]:
            f.write(cert + '\n\n')
    
    # Salvar raiz (último)
    with open('certificado_raiz.pem', 'w') as f:
        f.write(certificados[-1])
```

## 📤 Enviar ao Portal Developers BB

### Opção 1: Importar Cadeia Completa (Recomendado)

1. Acesse: https://app.developers.bb.com.br/#/aplicacoes/245394/certificado/enviar
2. Clique em **"Importar cadeia completa"**
3. Selecione o arquivo: `cadeia_completa_para_importacao.pem` (veja abaixo como criar)

### Opção 2: Enviar Individualmente

1. **Certificado Empresa**: `certificado_empresa.pem`
2. **Certificado Intermediário**: `certificado_intermediario.pem` (se existir)
3. **Certificado Raiz**: `certificado_raiz.pem`

## 📝 Criar Arquivo para Importação Completa

Para facilitar, crie um arquivo com tudo junto:

```bash
# Criar arquivo com cadeia completa (empresa + intermediários + raiz)
cat certificado_empresa.pem cadeia_completa.pem > cadeia_completa_para_importacao.pem
```

## ✅ Verificação

Após extrair, verifique se os arquivos foram criados:

```bash
ls -lh certificados_bb/
```

Você deve ver:
- `certificado_empresa.pem`
- `cadeia_completa.pem`
- `certificado_intermediario.pem` (se houver)
- `certificado_raiz.pem`
- `cadeia_completa_para_importacao.pem`

## 🔍 Verificar Conteúdo dos Certificados

```bash
# Ver informações do certificado da empresa
openssl x509 -in certificado_empresa.pem -noout -text | head -20

# Ver CN (Common Name) - deve conter o CNPJ ou nome da empresa
openssl x509 -in certificado_empresa.pem -noout -subject
```

## ⚠️ Importante

- **NÃO envie a chave privada** ao BB (apenas certificados públicos)
- Os certificados devem estar em formato **PEM (Base 64)**
- A cadeia deve incluir: Empresa + Intermediários + Raiz
- Após envio, aguarde até **3 dias úteis** para aprovação

## 📚 Referências

- Portal Developers BB: https://app.developers.bb.com.br/#/aplicacoes/245394/certificado/enviar
- Documentação BB sobre certificados: https://developers.bb.com.br

