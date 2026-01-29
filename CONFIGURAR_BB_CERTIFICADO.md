# 🔐 CONFIGURAÇÃO RÁPIDA - Certificado BB para mTLS

**Data:** 06/01/2026  
**Status:** ✅ Código pronto - só precisa configurar o .env

---

## ✅ SOLUÇÃO SIMPLES

**Configure no `.env` apontando DIRETAMENTE para o arquivo `.pfx`:**

```env
# Banco do Brasil - Certificado mTLS (PRODUÇÃO)
# ✅ Use o .pfx diretamente - o código extrai automaticamente!
BB_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ 4PL (valid 23-03-26) senha001.pfx
BB_PFX_PASSWORD=senha001
```

**⚠️ IMPORTANTE:**
- NÃO use `cadeia_completa_para_importacao.pem` (não tem chave privada)
- Use o arquivo `.pfx` diretamente
- O código detecta automaticamente e extrai o certificado com chave privada

---

## 📋 Passo a Passo

1. **Abra o arquivo `.env`**

2. **Procure por `BB_CERT_PATH`** (se existir, comente ou remova a linha antiga)

3. **Adicione estas linhas:**
   ```env
   BB_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ 4PL (valid 23-03-26) senha001.pfx
   BB_PFX_PASSWORD=senha001
   ```

4. **Salve o arquivo**

5. **Teste:**
   ```bash
   python3 teste_bb_api.py
   ```

---

## ✅ O Que Deve Acontecer

Quando você executar o teste, deve ver:

```
✅ Certificado .pfx convertido automaticamente para uso em mTLS
✅ Token obtido com sucesso!
✅ Extrato obtido com sucesso!
```

**Se ainda der erro**, verifique:
- O caminho do `.pfx` está correto no `.env`?
- O arquivo `.pfx` existe no caminho especificado?
- A senha está correta? (padrão: `senha001`)

---

## 🔍 Verificar Configuração

Para verificar se está configurado corretamente:

```bash
# Verificar se a variável está no .env
grep BB_CERT_PATH .env

# Deve mostrar:
# BB_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ 4PL (valid 23-03-26) senha001.pfx
```

---

**Última atualização:** 06/01/2026



