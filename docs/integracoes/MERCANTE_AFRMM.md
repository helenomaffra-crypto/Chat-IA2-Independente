# 🚢 Mercante — Pagamento AFRMM (RPA)

Este documento descreve a automação do **pagamento AFRMM** no sistema **Mercante** via RPA (`scripts/mercante_bot.py`) integrada ao mAIke.

---

## ✅ Fluxo (alto nível)

1. Usuário pede: **"pague a afrmm do GYM.0050/25"**
2. mAIke gera **preview** (valor AFRMM via CE + saldo BB) e cria um **pending intent**
3. Usuário confirma: **"sim"**
4. Robô executa:
   - Login (se necessário)
   - Navegação até **Pagamento → Pagar AFRMM**
   - Preenche CE + dados bancários
   - Clica **Pagar AFRMM**
   - Aceita o popup **OK**
   - Aguarda aparecer **"Débito efetuado com sucesso"**
   - Salva **print (PNG)** do comprovante
   - Emite JSON `__MAIKE_JSON__` para a UI reportar **sucesso/erro**

---

## 🧾 Comprovante (print)

- O robô salva automaticamente um PNG em: `downloads/mercante/`
- A UI entrega um link para abrir/baixar:
  - `/api/download/mercante/<arquivo>.png`

---

## 🗄️ Persistência no SQL Server (mAIke_assistente)

Além do SQLite (cache local), ao concluir um pagamento com sucesso o sistema tenta gravar também no SQL Server
(`mAIke_assistente`) para auditoria/fonte de verdade.

- **Tabela**: `mAIke_assistente.dbo.MERCANTE_AFRMM_PAGAMENTO`
- **Chave idempotente**: `payload_hash` (evita duplicatas)
- Se o SQL Server estiver fora da rede/indisponível, o pagamento continua funcionando e fica apenas no cache local.

---

## 🔎 Consultar pagamentos gravados

Endpoint (SQL Server com fallback para SQLite):

- `GET /api/mercante/afrmm/pagamentos?processo=GYM.0050/25&limite=20`
- `GET /api/mercante/afrmm/pagamentos?ce=132505419301091`

---

## 🔐 Variáveis de ambiente (Mercante)

Obrigatórias (modo sem CDP):

```env
MERCANTE_USER=seu_cpf
MERCANTE_PASS=sua_senha
```

Opcional (comportamento):

```env
# Se true, roda sem mostrar janela do navegador
MERCANTE_HEADLESS=false

# full (padrão): faz o fluxo completo no "sim"
# click_only/cdp: tenta clicar usando Chrome já aberto via CDP
MERCANTE_CONFIRMATION_MODE=full

# Para usar CDP:
MERCANTE_USE_CDP=false
MERCANTE_CDP_URL=http://127.0.0.1:9222
```

⚠️ **Senha expira** periodicamente (Mercante costuma exigir troca a cada ~20 dias). Se falhar, a UI deve orientar atualizar credenciais em Configurações.

---

## 🧠 Regras importantes

- **Não pagar duplicado**: se o CE retornar `afrmmTUMPago=true`, o mAIke deve bloquear a execução (preview e confirmação).
- **Tempo de execução**: após confirmar, o processamento pode demorar até **2 minutos**.
- **Popup do Mercante**: a confirmação é `window.confirm()`. Sem handler, o Playwright pode auto-dismiss (fecha rápido). Por isso o robô instala handler para `dialog.accept()`.

---

## 🧪 Debug rápido

Rodar manualmente (com janela):

```bash
python3 scripts/mercante_bot.py --acao pagar_afrmm --no_cdp --ignore_https_errors --debug --keep_open --keep_open_seconds 600
```

Com CDP:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-mercante
```

