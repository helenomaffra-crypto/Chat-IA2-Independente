#!/bin/bash
# Script para iniciar o Chat IA Independente

echo "🚀 Iniciando Chat IA Independente..."
echo ""

# Verificar se Python3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 não encontrado. Por favor, instale Python 3.9 ou superior."
    exit 1
fi

# Navegar para o diretório do projeto
cd "$(dirname "$0")"

# Verificar se o arquivo app.py existe
if [ ! -f "app.py" ]; then
    echo "❌ Arquivo app.py não encontrado."
    exit 1
fi

# Verificar se a porta 5001 está em uso e parar automaticamente
PORTA_5001_PID=$(lsof -ti:5001 2>/dev/null)
if [ ! -z "$PORTA_5001_PID" ]; then
    echo "⚠️  Porta 5001 já está em uso (PID: $PORTA_5001_PID)."
    echo "🛑 Parando processo existente na porta 5001..."
    
    # Tentar matar o processo
    kill -9 $PORTA_5001_PID 2>/dev/null
    sleep 2
    
    # Verificar se ainda está em uso
    PORTA_5001_PID_NOVO=$(lsof -ti:5001 2>/dev/null)
    if [ ! -z "$PORTA_5001_PID_NOVO" ]; then
        echo "⚠️  Tentando novamente com força..."
        kill -9 $PORTA_5001_PID_NOVO 2>/dev/null
        sleep 1
    fi
    
    # Verificação final
    PORTA_5001_PID_FINAL=$(lsof -ti:5001 2>/dev/null)
    if [ ! -z "$PORTA_5001_PID_FINAL" ]; then
        echo "❌ Não foi possível liberar a porta 5001 automaticamente."
        echo "   Processo ainda ativo: $PORTA_5001_PID_FINAL"
        echo "   Tente manualmente: kill -9 $PORTA_5001_PID_FINAL"
        exit 1
    else
        echo "✅ Porta 5001 liberada com sucesso!"
    fi
fi

# ✅ NOVO: Também verificar e matar processos Python/app.py que possam estar rodando em background
echo "🔍 Verificando processos Python/app.py em background..."
PYTHON_PIDS=$(ps aux | grep -E "python.*app\.py|python3.*app\.py" | grep -v grep | awk '{print $2}')
if [ ! -z "$PYTHON_PIDS" ]; then
    echo "⚠️  Encontrados processos Python/app.py em background: $PYTHON_PIDS"
    echo "🛑 Encerrando processos..."
    for pid in $PYTHON_PIDS; do
        kill -9 $pid 2>/dev/null && echo "   ✅ Processo $pid encerrado" || echo "   ⚠️  Não foi possível encerrar processo $pid"
    done
    sleep 1
fi

# Iniciar a aplicação
echo "✅ Iniciando servidor Flask na porta 5001..."
echo "📱 Acesse: http://localhost:5001/chat-ia"
echo ""
echo "Pressione Ctrl+C para parar o servidor."
echo ""

python3 app.py

