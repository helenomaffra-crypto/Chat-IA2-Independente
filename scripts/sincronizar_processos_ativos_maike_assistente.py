#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CLI: Sincronizar processos ativos do Kanban → mAIke_assistente

Uso:
  python3 scripts/sincronizar_processos_ativos_maike_assistente.py --limite 100
  python3 scripts/sincronizar_processos_ativos_maike_assistente.py --limite 30 --sem-documentos
  python3 scripts/sincronizar_processos_ativos_maike_assistente.py --limite 30 --sem-valores-impostos
"""

import argparse
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limite", type=int, default=50)
    parser.add_argument("--sem-documentos", action="store_true")
    parser.add_argument("--sem-valores-impostos", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, ".")
    from services.processo_sync_service import ProcessoSyncService

    svc = ProcessoSyncService()
    res = svc.sincronizar_processos_ativos(
        limite=args.limite,
        incluir_documentos=not args.sem_documentos,
        incluir_valores_impostos=not args.sem_valores_impostos,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    return 0 if res.get("sucesso") else 1


if __name__ == "__main__":
    raise SystemExit(main())

