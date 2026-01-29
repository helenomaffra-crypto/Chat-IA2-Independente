"""
Contrato único de retorno de tools.

Garante que tools sempre retornam dict padronizado, nunca None.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Literal

ToolKind = Literal["tool_result", "email_preview", "report", "generic", "error"]

class ToolResult(Dict[str, Any]):
    """
    Contrato padronizado de retorno de tools.
    
    Campos obrigatórios:
    - ok: bool - Se a operação foi bem-sucedida
    - tool: str - Nome da tool executada
    - kind: ToolKind - Tipo de resultado
    
    Campos opcionais:
    - text: str - Texto pronto para exibir no chat
    - dados_json: Dict[str, Any] - Payload estruturado
    - resposta: str - Alias para text (compatibilidade)
    - sucesso: bool - Alias para ok (compatibilidade)
    - erro: str - Mensagem de erro (se ok=False)
    - error: str - Alias para erro (compatibilidade)
    - meta: Dict[str, Any] - Informações auxiliares (ids, timings, etc.)
    """
    pass


def ok_result(
    tool: str,
    kind: ToolKind = "tool_result",
    text: str = "",
    dados_json: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
    **kwargs
) -> ToolResult:
    """
    Cria resultado de sucesso padronizado.
    
    Args:
        tool: Nome da tool
        kind: Tipo de resultado
        text: Texto para exibir
        dados_json: Dados estruturados
        meta: Metadados auxiliares
        **kwargs: Campos adicionais (resposta, sucesso, etc. para compatibilidade)
    
    Returns:
        ToolResult com ok=True
    """
    r: ToolResult = ToolResult({
        "ok": True,
        "sucesso": True,  # Compatibilidade
        "tool": tool,
        "kind": kind
    })
    
    if text:
        r["text"] = text
        r["resposta"] = text  # Compatibilidade
    
    if dados_json is not None:
        r["dados_json"] = dados_json
    
    if meta is not None:
        r["meta"] = meta
    
    # Adicionar campos extras para compatibilidade
    for key, value in kwargs.items():
        r[key] = value
    
    return r


def err_result(
    tool: str,
    error: str,
    text: str = "",
    meta: Optional[Dict[str, Any]] = None,
    **kwargs
) -> ToolResult:
    """
    Cria resultado de erro padronizado.
    
    Args:
        tool: Nome da tool
        error: Mensagem de erro
        text: Texto adicional (opcional)
        meta: Metadados auxiliares
        **kwargs: Campos adicionais
    
    Returns:
        ToolResult com ok=False
    """
    r: ToolResult = ToolResult({
        "ok": False,
        "sucesso": False,  # Compatibilidade
        "tool": tool,
        "kind": "error",
        "error": error,
        "erro": error  # Compatibilidade
    })
    
    if text:
        r["text"] = text
        r["resposta"] = text  # Compatibilidade
    
    if meta is not None:
        r["meta"] = meta
    
    # Adicionar campos extras para compatibilidade
    for key, value in kwargs.items():
        r[key] = value
    
    return r


def normalize_tool_result(tool: str, raw: Any) -> ToolResult:
    """
    Garante que tool nunca 'vaza' None para pipeline.
    
    Normaliza qualquer retorno de tool para ToolResult padronizado.
    
    Args:
        tool: Nome da tool executada
        raw: Retorno bruto da tool (pode ser None, dict, str, etc.)
    
    Returns:
        ToolResult sempre válido (nunca None)
    """
    if raw is None:
        return err_result(tool, "Tool retornou None")
    
    if isinstance(raw, dict):
        # Normaliza campos mínimos
        normalized = ToolResult(raw)
        normalized.setdefault("tool", tool)
        normalized.setdefault("kind", "tool_result")
        
        # ✅ CRÍTICO (14/01/2026): Preservar sinal de fallback ANTES de normalizar
        # Se error="FALLBACK_REQUIRED" ou use_fallback=True, preservar esses campos
        is_fallback = (
            normalized.get("error") == "FALLBACK_REQUIRED" or
            normalized.get("erro") == "FALLBACK_REQUIRED" or
            normalized.get("use_fallback") is True
        )
        
        # Garantir campos obrigatórios
        if "ok" not in normalized and "sucesso" in normalized:
            normalized["ok"] = normalized["sucesso"]
        elif "ok" not in normalized:
            # ✅ Se é fallback, ok=False (mas não é erro final)
            normalized["ok"] = False if is_fallback else True
        
        if "sucesso" not in normalized:
            normalized["sucesso"] = normalized.get("ok", True)
        
        # Normalizar text/resposta
        if "text" not in normalized and "resposta" in normalized:
            normalized["text"] = normalized["resposta"]
        elif "resposta" not in normalized and "text" in normalized:
            normalized["resposta"] = normalized["text"]
        
        # Normalizar error/erro
        if "error" not in normalized and "erro" in normalized:
            normalized["error"] = normalized["erro"]
        elif "erro" not in normalized and "error" in normalized:
            normalized["erro"] = normalized["error"]
        
        # ✅ Garantir que use_fallback está presente se é fallback
        if is_fallback:
            normalized["use_fallback"] = True
            if "error" not in normalized:
                normalized["error"] = "FALLBACK_REQUIRED"
            if "erro" not in normalized:
                normalized["erro"] = "FALLBACK_REQUIRED"
            # ✅ CRÍTICO (14/01/2026): Marcar como não-sucesso mas não erro final
            # Isso evita que seja tratado como sucesso em métricas/log
            normalized["ok"] = False
            normalized["sucesso"] = False
        
        return normalized
    
    # Se devolveu string ou outra coisa, encapsula
    return ok_result(tool, kind="generic", text=str(raw))
