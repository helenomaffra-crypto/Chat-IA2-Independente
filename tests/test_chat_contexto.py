#!/usr/bin/env python3
"""
Script de teste simples para verificar contexto de sessão.

Uso:
    python tests/test_chat_contexto.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.context_service import (
    buscar_contexto_sessao,
    limpar_contexto_sessao,
    obter_contexto_formatado_para_usuario
)

def test_contexto_sessao():
    """Testa consulta de contexto de sessão."""
    print("=" * 60)
    print("TESTE: Consulta de Contexto de Sessão")
    print("=" * 60)
    
    # Usar um session_id de teste
    session_id_teste = "test_session_123"
    
    print(f"\n1. Limpando contexto antigo (se houver)...")
    limpar_contexto_sessao(session_id_teste)
    
    print(f"\n2. Consultando contexto (deve estar vazio)...")
    contexto = obter_contexto_formatado_para_usuario(session_id_teste)
    print(f"   Resultado: {contexto}")
    
    print(f"\n3. Buscando contexto direto do banco...")
    contextos = buscar_contexto_sessao(session_id_teste)
    print(f"   Total de contextos encontrados: {len(contextos)}")
    for ctx in contextos:
        print(f"   - {ctx.get('tipo_contexto')}: {ctx.get('valor')}")
    
    print(f"\n✅ Teste concluído!")
    print("=" * 60)

if __name__ == '__main__':
    test_contexto_sessao()
