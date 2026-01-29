# Diagnóstico `mAIke_assistente`

- **Database**: `mAIke_assistente`
- **Gerado em**: `2026-01-19T14:53:29.331021`

## Contagens por tabela

| Tabela | Registros |
|---|---:|
| `dbo.PROCESSO_IMPORTACAO` | 2 |
| `dbo.DOCUMENTO_ADUANEIRO` | 242 |
| `dbo.HISTORICO_DOCUMENTO_ADUANEIRO` | 0 |
| `dbo.VALOR_MERCADORIA` | 358 |
| `dbo.IMPOSTO_IMPORTACAO` | 5 |
| `dbo.MOVIMENTACAO_BANCARIA` | 522 |
| `dbo.LANCAMENTO_TIPO_DESPESA` | 3 |

## Perfil de nulos/vazios (colunas essenciais)

### `dbo.PROCESSO_IMPORTACAO`

| Coluna | Nulos/Vazios |
|---|---:|
| `numero_processo` | 0 |
| `id_importacao` | 0 |
| `status_processo` | 0 |
| `data_embarque` | 2 |
| `data_chegada_prevista` | 2 |
| `data_desembaraco` | 2 |
| `atualizado_em|data_ultima_modificacao` | 0 |

### `dbo.DOCUMENTO_ADUANEIRO`

| Coluna | Nulos/Vazios |
|---|---:|
| `numero_documento` | 0 |
| `tipo_documento` | 0 |
| `processo_referencia` | 4 |
| `status_documento` | 15 |
| `status_documento_codigo` | 112 |
| `situacao_documento` | 112 |
| `canal_documento` | 242 |
| `data_registro` | 133 |
| `data_situacao` | 124 |
| `data_desembaraco` | 144 |
| `json_dados_originais` | 108 |
| `atualizado_em` | 0 |

### `dbo.HISTORICO_DOCUMENTO_ADUANEIRO`

| Coluna | Nulos/Vazios |
|---|---:|
| `id_documento` | 0 |
| `tipo_evento|tipo_mudanca` | 0 |
| `campo_alterado` | 0 |
| `valor_anterior` | 0 |
| `valor_novo` | 0 |
| `data_evento|data_mudanca` | 0 |
| `fonte_dados` | 0 |

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
| `processo_referencia` | 0 |
| `numero_documento` | 0 |
| `tipo_documento` | 0 |
| `tipo_imposto` | 0 |
| `valor_brl|valor` | 0 |
| `valor_usd` | 5 |
| `atualizado_em` | 0 |

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
| `id_movimentacao_bancaria|id_movimentacao` | 0 |
| `id_tipo_despesa` | 0 |
| `valor_despesa|valor_classificado` | 0 |
| `criado_em|atualizado_em` | 0 |

## Duplicidades (chaves naturais)

### `dbo.DOCUMENTO_ADUANEIRO(tipo_documento, numero_documento, versao_documento)`

- **Grupos duplicados**: 0

### `dbo.VALOR_MERCADORIA(processo_referencia, numero_documento, tipo_documento, tipo_valor, moeda)`

- **Grupos duplicados**: 0

### `dbo.IMPOSTO_IMPORTACAO(processo_referencia, numero_documento, tipo_documento, tipo_imposto, numero_retificacao)`

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
| 634 | CCT | HKGA025489 | GPS.0010/24 |  |  |  |  | 8 | 2026-01-14T17:30:46.817Z |
| 508 | CCT | MIA4705 | GLT.0047/25 |  |  |  |  | 8 | 2026-01-13T14:36:01.490Z |
| 591 | DI | 2428428607 | MK3.0006/24 |  |  |  |  | 8 | 2026-01-12T15:34:02.060Z |
| 540 | CCT | MIA4703 | GLT.0046/25 |  |  |  |  | 8 | 2026-01-12T08:34:33.913Z |
| 279 | DUIMP | 25BR00001946023 | SLL.0009/25 |  |  |  |  | 8 | 2026-01-12T08:05:58.727Z |
| 238 | CCT | MIA4701 | GLT.0045/25 |  |  |  |  | 8 | 2026-01-08T15:50:59.910Z |
| 413 | DUIMP | 25BR00001948441 | SLL.0009/25 |  |  |  |  | 8 | 2026-01-08T14:19:51.277Z |
| 620 | DI | 2526380897 | MDA.0090/25 |  |  |  |  | 7 | 2026-01-19T14:40:29.730Z |
| 585 | DI | 2524745537 | GYM.0048/25 |  |  |  |  | 7 | 2026-01-19T14:40:17.430Z |
| 581 | DUIMP | 26BR00000065332 | DMD.0083/25 |  |  |  |  | 7 | 2026-01-19T14:39:00.183Z |
| 712 | CCT | MIA4717 | GLT.0002/26 |  |  |  |  | 7 | 2026-01-19T14:35:07.183Z |
| 612 | DI | 2600686869 | MDA.0095/25 | DI_DESEMBARACADA |  |  |  | 6 | 2026-01-19T14:30:49.117Z |
| 437 | DI | 2600395929 | BGR.0071/25 | DI_DESEMBARACADA |  |  |  | 6 | 2026-01-19T14:30:21.547Z |
| 708 | DI | 2600842585 | ARG.0001/26 | DI_DESEMBARACADA |  |  |  | 6 | 2026-01-19T14:28:37.237Z |
| 643 | DI | 2408045370 | GPS.0010/24 | INTERROMPIDA_DESPACHO_INTERROMPIDO |  |  |  | 6 | 2026-01-19T14:23:16.470Z |
| 689 | DI | 2504026314 | MSS.0015/24 | DI_DESEMBARACADA |  |  |  | 6 | 2026-01-19T14:22:59.133Z |

## Metadados (JSON)

```json
{
  "database": "mAIke_assistente",
  "started_at": "2026-01-19T14:52:49.830513",
  "finished_at": "2026-01-19T14:53:29.331021",
  "counts": {
    "dbo.PROCESSO_IMPORTACAO": 2,
    "dbo.DOCUMENTO_ADUANEIRO": 242,
    "dbo.HISTORICO_DOCUMENTO_ADUANEIRO": 0,
    "dbo.VALOR_MERCADORIA": 358,
    "dbo.IMPOSTO_IMPORTACAO": 5,
    "dbo.MOVIMENTACAO_BANCARIA": 522,
    "dbo.LANCAMENTO_TIPO_DESPESA": 3
  },
  "duplicates": {
    "dbo.DOCUMENTO_ADUANEIRO(tipo_documento, numero_documento, versao_documento)": {
      "groups": 0
    },
    "dbo.VALOR_MERCADORIA(processo_referencia, numero_documento, tipo_documento, tipo_valor, moeda)": {
      "groups": 0
    },
    "dbo.IMPOSTO_IMPORTACAO(processo_referencia, numero_documento, tipo_documento, tipo_imposto, numero_retificacao)": {
      "groups": 0
    },
    "dbo.PROCESSO_IMPORTACAO(numero_processo)": {
      "groups": 0
    }
  }
}
```
