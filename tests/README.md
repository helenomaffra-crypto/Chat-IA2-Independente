# 🧪 Testes

Esta pasta contém scripts de teste para validar funcionalidades do sistema.

## 📁 Estrutura

```
tests/
├── scripts/          # Scripts de teste executáveis
│   ├── test_consulta_service.py
│   ├── test_processo_list_service.py
│   ├── test_servicos_migrados.py
│   ├── testar_notificacao_desembaraco.py
│   ├── testar_notificacao_tts.py
│   ├── test_tts_html.html
│   └── ouvir_audio_tts.py
└── README.md         # Este arquivo
```

## 🚀 Como Executar

### Testes de Serviços Migrados

```bash
# Testar ConsultaService
python tests/scripts/test_consulta_service.py

# Testar ProcessoListService
python tests/scripts/test_processo_list_service.py

# Testar todos os serviços migrados
python tests/scripts/test_servicos_migrados.py
```

### Testes de Notificações

```bash
# Testar notificações de desembaraço
python tests/scripts/testar_notificacao_desembaraco.py

# Testar notificações TTS
python tests/scripts/testar_notificacao_tts.py
```

## ⚠️ Importante

Antes de executar os testes, certifique-se de:
1. Ajustar os valores nos scripts (CEs, processos, categorias) para valores que existem no seu sistema
2. Ter o Flask rodando (se os testes precisarem de endpoints)
3. Ter o banco de dados inicializado

## 📝 Notas

- Os testes são scripts independentes que podem ser executados diretamente
- Alguns testes podem precisar de dados específicos no banco
- Verifique os logs para entender melhor o que está sendo testado












