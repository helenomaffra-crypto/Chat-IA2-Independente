"""
Auditoria de migração de tools.

Compara:
- tools disponíveis em services/tool_definitions.py (get_available_tools)
- mapeamento do ToolRouter (services/tool_router.py)
- handlers do ToolExecutionService (services/tool_execution_service.py)

Saída:
- Relatório em texto (stdout) com listas de gaps e inconsistências.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path


# Permitir rodar como script (python scripts/auditar_tools.py)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _extract_tool_names(tools: List[dict]) -> List[str]:
    names: List[str] = []
    for t in tools:
        fn = (t or {}).get("function") or {}
        name = fn.get("name")
        if name:
            names.append(str(name))
    return names


@dataclass
class AuditResult:
    total_tools: int
    tool_names: List[str]
    router_mapped: Dict[str, Optional[str]]
    tes_handlers: Set[str]

    missing_in_router: List[str]
    router_none: List[str]
    missing_in_tes: List[str]
    router_none_but_has_tes: List[str]
    router_has_agent_but_no_tes: List[str]


def audit() -> AuditResult:
    from services.tool_definitions import get_available_tools
    from services.tool_router import ToolRouter
    from services.tool_execution_service import ToolExecutionService

    tools = get_available_tools(compact=False)
    tool_names = sorted(set(_extract_tool_names(tools)))

    router = ToolRouter()
    router_mapped = dict(router.tool_to_agent)

    tes = ToolExecutionService(tool_context=None)
    tes_handlers = set(getattr(tes, "_handlers", {}).keys())

    missing_in_router = [n for n in tool_names if n not in router_mapped]
    router_none = sorted([n for n in tool_names if router_mapped.get(n) is None])
    missing_in_tes = sorted([n for n in tool_names if n not in tes_handlers])

    router_none_but_has_tes = sorted([n for n in router_none if n in tes_handlers])
    router_has_agent_but_no_tes = sorted([n for n in tool_names if router_mapped.get(n) and n not in tes_handlers])
    router_has_agent_but_no_tes = [n for n in router_has_agent_but_no_tes if n in tool_names]

    return AuditResult(
        total_tools=len(tool_names),
        tool_names=tool_names,
        router_mapped=router_mapped,
        tes_handlers=tes_handlers,
        missing_in_router=sorted(missing_in_router),
        router_none=router_none,
        missing_in_tes=missing_in_tes,
        router_none_but_has_tes=router_none_but_has_tes,
        router_has_agent_but_no_tes=router_has_agent_but_no_tes,
    )


def _print_section(title: str, items: List[str], limit: int = 200) -> None:
    print(f"\n=== {title} ({len(items)}) ===")
    for i, name in enumerate(items[:limit], 1):
        print(f"{i:02d}. {name}")
    if len(items) > limit:
        print(f"... (+{len(items) - limit} restantes)")


def main() -> None:
    res = audit()

    print("🧪 AUDITORIA DE TOOLS (tool_definitions vs ToolRouter vs ToolExecutionService)")
    print(f"- total_tools: {res.total_tools}")
    print(f"- toolrouter_mapeadas: {len(res.router_mapped)} (inclui tools fora do tool_definitions)")
    print(f"- tool_execution_handlers: {len(res.tes_handlers)}")

    _print_section("Tools presentes no tool_definitions mas AUSENTES no ToolRouter.mapping", res.missing_in_router)
    _print_section("Tools com ToolRouter.agent == None (cai em fallback do ChatService)", res.router_none)
    _print_section("Tools SEM handler no ToolExecutionService (podem estar só em agent ou só no legado)", res.missing_in_tes)
    _print_section("INCONSISTÊNCIA: ToolRouter=None MAS ToolExecutionService TEM handler (ajustar roteamento/documentação)", res.router_none_but_has_tes)
    _print_section("ToolRouter tem agent MAS ToolExecutionService NÃO tem handler (ok se agent implementa; validar)", res.router_has_agent_but_no_tes)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Erro na auditoria: {e}", file=sys.stderr)
        raise

