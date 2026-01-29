"""
Arruma arquivo .env (dot-env) de forma segura.

O que faz:
- Cria backup: .env.bak_YYYYMMDD_HHMMSS
- Remove linhas "soltas" que não são comentário nem KEY=VALUE
- Normaliza: remove espaços à direita, remove indentação à esquerda
- Garante que valores com espaços sejam colocados entre aspas
- Mantém comentários e ordem o máximo possível

Obs: não imprime valores sensíveis.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _needs_quotes(value: str) -> bool:
    v = value.strip()
    if not v:
        return False
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return False
    # espaços e tab costumam quebrar dotenv (principalmente em paths)
    return any(ch.isspace() for ch in v)


def _split_inline_comment(value: str) -> tuple[str, str]:
    """
    Se houver comentário inline no padrão dotenv (espaço + #),
    separa em (valor, comentario). Não tenta interpretar # dentro de valores citados.
    """
    v = value.rstrip()
    if not v:
        return "", ""
    # Se já está entre aspas, não mexer
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v, ""
    # Padrão: "valor   # comentario"
    m = re.search(r"\s+#", v)
    if not m:
        return v, ""
    idx = m.start()
    return v[:idx].rstrip(), v[idx:].lstrip()


def _quote_value(value: str) -> str:
    v = value.strip()
    # usar aspas duplas e escapar as existentes
    v = v.replace('"', '\\"')
    return f"\"{v}\""


def arrumar_env(env_path: Path) -> dict:
    if not env_path.exists():
        raise FileNotFoundError(f"Não achei {env_path}")

    original = env_path.read_text(encoding="utf-8", errors="replace").splitlines()
    out_lines: list[str] = []

    removidas = 0
    corrigidas = 0
    quotadas = 0

    for line in original:
        raw = line
        s = raw.rstrip("\r\n")
        # preservar linha vazia
        if not s.strip():
            out_lines.append("")
            continue

        # comentários (mantém)
        if s.lstrip().startswith("#"):
            out_lines.append(s.strip())
            if s != s.strip():
                corrigidas += 1
            continue

        # remover indentação à esquerda (dotenv pode falhar)
        if s != s.lstrip():
            s = s.lstrip()
            corrigidas += 1

        # se não tiver '=', é linha inválida -> comentar (não apagar para não perder contexto)
        if "=" not in s:
            out_lines.append(f"# [REMOVIDO] {s}")
            removidas += 1
            continue

        key, value = s.split("=", 1)
        key = key.strip()
        value = value.strip()

        # key inválida -> comentar
        if not _KEY_RE.match(key):
            out_lines.append(f"# [REMOVIDO] {s}")
            removidas += 1
            continue

        # Separar comentário inline (ex.: VAR=123 # comentario)
        value, inline_comment = _split_inline_comment(value)
        if inline_comment:
            corrigidas += 1

        # colocar aspas se tiver espaços
        if _needs_quotes(value):
            value = _quote_value(value)
            quotadas += 1

        line_out = f"{key}={value}"
        if inline_comment:
            line_out += f"  # {inline_comment.lstrip('#').strip()}"
        out_lines.append(line_out)

    # normalizar final de arquivo
    out_text = "\n".join(out_lines).rstrip() + "\n"
    env_path.write_text(out_text, encoding="utf-8")

    return {
        "linhas_antes": len(original),
        "linhas_depois": len(out_lines),
        "removidas_comentadas": removidas,
        "corrigidas": corrigidas,
        "quotadas": quotadas,
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = root / f".env.bak_{ts}"
    backup_path.write_text(env_path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")

    stats = arrumar_env(env_path)

    print("✅ .env arrumado com sucesso")
    print(f"📦 Backup: {backup_path.name}")
    print(
        "📊 Stats: "
        f"{stats['linhas_antes']}→{stats['linhas_depois']} linhas | "
        f"removidas_comentadas={stats['removidas_comentadas']} | "
        f"corrigidas={stats['corrigidas']} | "
        f"quotadas={stats['quotadas']}"
    )


if __name__ == "__main__":
    main()

