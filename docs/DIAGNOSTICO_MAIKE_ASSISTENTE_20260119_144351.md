# Diagnóstico `mAIke_assistente`

- **Database**: `mAIke_assistente`
- **Gerado em**: `2026-01-19T14:43:51.133304`

## Contagens por tabela

| Tabela | Registros |
|---|---:|
| `dbo.PROCESSO_IMPORTACAO` | 2 |
| `dbo.DOCUMENTO_ADUANEIRO` | 718 |
| `dbo.HISTORICO_DOCUMENTO_ADUANEIRO` | 0 |
| `dbo.VALOR_MERCADORIA` | 110 |
| `dbo.IMPOSTO_IMPORTACAO` | 5 |
| `dbo.MOVIMENTACAO_BANCARIA` | 0 |
| `dbo.LANCAMENTO_TIPO_DESPESA` | 3 |

## Perfil de nulos/vazios (colunas essenciais)

### `dbo.PROCESSO_IMPORTACAO`

| Coluna | Nulos/Vazios |
|---|---:|
| `numero_processo` | -1 |
| `id_importacao` | -1 |
| `status_processo` | -1 |
| `data_embarque` | -1 |
| `data_chegada_prevista` | -1 |
| `data_desembaraco` | -1 |
| `data_ultima_modificacao` | -1 |

### `dbo.DOCUMENTO_ADUANEIRO`

| Coluna | Nulos/Vazios |
|---|---:|
| `numero_documento` | 0 |
| `tipo_documento` | 0 |
| `processo_referencia` | 6 |
| `status_documento` | 38 |
| `status_documento_codigo` | 689 |
| `situacao_documento` | 689 |
| `canal_documento` | 718 |
| `data_registro` | 431 |
| `data_situacao` | 325 |
| `data_desembaraco` | 451 |
| `json_dados_originais` | 688 |
| `atualizado_em` | 0 |

### `dbo.HISTORICO_DOCUMENTO_ADUANEIRO`

| Coluna | Nulos/Vazios |
|---|---:|
| `id_documento` | -1 |
| `tipo_mudanca` | -1 |
| `campo_alterado` | -1 |
| `valor_anterior` | -1 |
| `valor_novo` | -1 |
| `data_mudanca` | -1 |
| `fonte_dados` | -1 |

### `dbo.VALOR_MERCADORIA`

| Coluna | Nulos/Vazios |
|---|---:|
| `processo_referencia` | 0 |
| `numero_documento` | 0 |
| `tipo_documento` | 0 |
| `tipo_valor` | 0 |
| `moeda` | 0 |
| `valor` | 0 |
| `atualizado_em` | 0 |

### `dbo.IMPOSTO_IMPORTACAO`

| Coluna | Nulos/Vazios |
|---|---:|
| `processo_referencia` | -1 |
| `numero_documento` | -1 |
| `tipo_documento` | -1 |
| `tipo_imposto` | -1 |
| `valor` | -1 |
| `moeda` | -1 |
| `atualizado_em` | -1 |

### `dbo.MOVIMENTACAO_BANCARIA`

| Coluna | Nulos/Vazios |
|---|---:|
| `id_movimentacao` | 0 |
| `banco_origem` | 0 |
| `data_movimentacao` | 0 |
| `valor_movimentacao` | 0 |
| `sinal_movimentacao` | 0 |
| `descricao_movimentacao` | 0 |

### `dbo.LANCAMENTO_TIPO_DESPESA`

| Coluna | Nulos/Vazios |
|---|---:|
| `id_movimentacao` | -1 |
| `id_tipo_despesa` | -1 |
| `valor_classificado` | -1 |
| `criado_em` | -1 |

## Duplicidades (chaves naturais)

### `dbo.DOCUMENTO_ADUANEIRO(tipo_documento, numero_documento, versao_documento)`

- **Grupos duplicados**: 197

| Chave | Qtd |
|---|---:|
| `tipo_documento=CE, numero_documento=172505417636125, versao_documento=` | 12 |
| `tipo_documento=CE, numero_documento=132505413279094, versao_documento=` | 9 |
| `tipo_documento=CE, numero_documento=132505413173180, versao_documento=` | 7 |
| `tipo_documento=CE, numero_documento=132505415795847, versao_documento=` | 7 |
| `tipo_documento=CE, numero_documento=152505353184607, versao_documento=` | 7 |
| `tipo_documento=CE, numero_documento=172505412595668, versao_documento=` | 7 |
| `tipo_documento=CE, numero_documento=132505337166085, versao_documento=` | 6 |
| `tipo_documento=CE, numero_documento=172505381482018, versao_documento=` | 6 |
| `tipo_documento=CE, numero_documento=172505417753946, versao_documento=` | 6 |
| `tipo_documento=DI, numero_documento=2524055980, versao_documento=` | 6 |
| `tipo_documento=DI, numero_documento=2526605112, versao_documento=` | 6 |
| `tipo_documento=DI, numero_documento=2527059898, versao_documento=` | 6 |
| `tipo_documento=DI, numero_documento=2600031870, versao_documento=` | 6 |
| `tipo_documento=CE, numero_documento=132505328596692, versao_documento=` | 5 |
| `tipo_documento=CE, numero_documento=132505358504680, versao_documento=` | 5 |
| `tipo_documento=CE, numero_documento=132505382976031, versao_documento=` | 5 |
| `tipo_documento=CE, numero_documento=132505398212508, versao_documento=` | 5 |
| `tipo_documento=CE, numero_documento=132505404820721, versao_documento=` | 5 |
| `tipo_documento=CE, numero_documento=132505408550303, versao_documento=` | 5 |
| `tipo_documento=CE, numero_documento=132505413173423, versao_documento=` | 5 |
| `tipo_documento=CE, numero_documento=172505330442116, versao_documento=` | 5 |
| `tipo_documento=CE, numero_documento=172505376506559, versao_documento=` | 5 |
| `tipo_documento=CE, numero_documento=172505380457982, versao_documento=` | 5 |
| `tipo_documento=CE, numero_documento=172505412595749, versao_documento=` | 5 |
| `tipo_documento=CE, numero_documento=172505416942974, versao_documento=` | 5 |
| `tipo_documento=CE, numero_documento=172605003120557, versao_documento=` | 5 |
| `tipo_documento=DI, numero_documento=2523497424, versao_documento=` | 5 |
| `tipo_documento=DI, numero_documento=2524745537, versao_documento=` | 5 |
| `tipo_documento=DI, numero_documento=2600196411, versao_documento=` | 5 |
| `tipo_documento=DI, numero_documento=2600362869, versao_documento=` | 5 |

### `dbo.VALOR_MERCADORIA(processo_referencia, numero_documento, tipo_documento, tipo_valor, moeda)`

- **Grupos duplicados**: 0

### `dbo.IMPOSTO_IMPORTACAO(processo_referencia, numero_documento, tipo_documento, tipo_imposto, moeda)`

- **Grupos duplicados**: 0

### `dbo.PROCESSO_IMPORTACAO(numero_processo)`

- **Grupos duplicados**: 0

## Top 20 piores registros (DOCUMENTO_ADUANEIRO)

| id | tipo | número | processo | status | código | situação | canal | missing_score | atualizado_em |
|---:|---|---|---|---|---|---|---|---:|---|
| 631 | DI | 2505279038 |  |  |  |  |  | 9 | 2026-01-14T13:45:24.940Z |
| 518 | DI | 2505231566 |  |  |  |  |  | 9 | 2026-01-10T17:26:35.363Z |
| 458 | DI | 2502596105 |  |  |  |  |  | 9 | 2026-01-08T20:33:40.560Z |
| 423 | DUIMP | api |  |  |  |  |  | 9 | 2026-01-08T15:05:03.170Z |
| 620 | DI | 2526380897 | MDA.0090/25 |  |  |  |  | 8 | 2026-01-14T21:08:46.230Z |
| 634 | CCT | HKGA025489 | GPS.0010/24 |  |  |  |  | 8 | 2026-01-14T17:30:46.817Z |
| 508 | CCT | MIA4705 | GLT.0047/25 |  |  |  |  | 8 | 2026-01-13T14:36:01.490Z |
| 591 | DI | 2428428607 | MK3.0006/24 |  |  |  |  | 8 | 2026-01-12T15:34:02.060Z |
| 585 | DI | 2524745537 | GYM.0048/25 |  |  |  |  | 8 | 2026-01-12T15:07:16.250Z |
| 581 | DUIMP | 26BR00000065332 | DMD.0083/25 |  |  |  |  | 8 | 2026-01-12T14:35:59.200Z |
| 245 | DUIMP | 26BR00000065332 | DMD.0083/25 |  |  |  |  | 8 | 2026-01-12T09:37:00.790Z |
| 549 | CCT | MIA4717 | GLT.0002/26 |  |  |  |  | 8 | 2026-01-12T09:33:13.887Z |
| 258 | DI | 2526380897 | MDA.0090/25 |  |  |  |  | 8 | 2026-01-12T09:30:34.073Z |
| 540 | CCT | MIA4703 | GLT.0046/25 |  |  |  |  | 8 | 2026-01-12T08:34:33.913Z |
| 279 | DUIMP | 25BR00001946023 | SLL.0009/25 |  |  |  |  | 8 | 2026-01-12T08:05:58.727Z |
| 496 | CCT | MIA4717 | GLT.0002/26 |  |  |  |  | 8 | 2026-01-10T18:10:51.250Z |
| 507 | DI | 2524745537 | GYM.0048/25 |  |  |  |  | 8 | 2026-01-10T11:37:31.753Z |
| 410 | DI | 2428428607 | MK3.0006/24 |  |  |  |  | 8 | 2026-01-08T20:02:27.227Z |
| 234 | CCT | MIA4705 | GLT.0047/25 |  |  |  |  | 8 | 2026-01-08T16:18:45.610Z |
| 236 | CCT | MIA4703 | GLT.0046/25 |  |  |  |  | 8 | 2026-01-08T16:04:31.750Z |

## Metadados (JSON)

```json
{
  "database": "mAIke_assistente",
  "started_at": "2026-01-19T14:43:07.335162",
  "finished_at": "2026-01-19T14:43:51.133304",
  "counts": {
    "dbo.PROCESSO_IMPORTACAO": 2,
    "dbo.DOCUMENTO_ADUANEIRO": 718,
    "dbo.HISTORICO_DOCUMENTO_ADUANEIRO": 0,
    "dbo.VALOR_MERCADORIA": 110,
    "dbo.IMPOSTO_IMPORTACAO": 5,
    "dbo.MOVIMENTACAO_BANCARIA": 0,
    "dbo.LANCAMENTO_TIPO_DESPESA": 3
  },
  "duplicates": {
    "dbo.DOCUMENTO_ADUANEIRO(tipo_documento, numero_documento, versao_documento)": {
      "groups": 197
    },
    "dbo.VALOR_MERCADORIA(processo_referencia, numero_documento, tipo_documento, tipo_valor, moeda)": {
      "groups": 0
    },
    "dbo.IMPOSTO_IMPORTACAO(processo_referencia, numero_documento, tipo_documento, tipo_imposto, moeda)": {
      "groups": 0
    },
    "dbo.PROCESSO_IMPORTACAO(numero_processo)": {
      "groups": 0
    }
  }
}
```
