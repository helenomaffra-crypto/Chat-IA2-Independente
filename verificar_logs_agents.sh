#!/bin/bash
# Script para verificar logs de inicialização dos agents

echo "📋 Verificando logs do container para erros de agents..."
echo ""

# Buscar erros relacionados a agents
docker compose logs web 2>&1 | grep -i "agent\|ProcessoAgent\|ToolRouter" | tail -30

echo ""
echo "📋 Verificando erros de importação..."
docker compose logs web 2>&1 | grep -i "erro\|error\|exception\|import" | grep -i "agent\|processo" | tail -20
