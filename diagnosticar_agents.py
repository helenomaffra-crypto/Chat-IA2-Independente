#!/usr/bin/env python3
"""
Script para diagnosticar problemas com agents.
"""
import sys
import traceback
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

print("=" * 60)
print("DIAGNÓSTICO DE AGENTS")
print("=" * 60)
print()

# Teste 1: Importar ToolRouter
print("1️⃣  Testando importação do ToolRouter...")
try:
    from services.tool_router import ToolRouter
    print("   ✅ ToolRouter importado com sucesso")
except Exception as e:
    print(f"   ❌ Erro ao importar ToolRouter: {e}")
    traceback.print_exc()
    sys.exit(1)

# Teste 2: Inicializar ToolRouter
print()
print("2️⃣  Testando inicialização do ToolRouter...")
try:
    router = ToolRouter()
    print(f"   ✅ ToolRouter inicializado")
    print(f"   📊 Agents carregados: {len(router.agents)}")
    print(f"   📋 Agents disponíveis: {list(router.agents.keys())}")
except Exception as e:
    print(f"   ❌ Erro ao inicializar ToolRouter: {e}")
    traceback.print_exc()
    sys.exit(1)

# Teste 3: Verificar cada agent individualmente
print()
print("3️⃣  Testando importação de cada agent...")
agents_to_test = [
    ('processo', 'ProcessoAgent', 'services.agents.processo_agent'),
    ('duimp', 'DuimpAgent', 'services.agents.duimp_agent'),
    ('ce', 'CeAgent', 'services.agents.ce_agent'),
    ('di', 'DiAgent', 'services.agents.di_agent'),
    ('cct', 'CctAgent', 'services.agents.cct_agent'),
    ('sistema', 'SistemaAgent', 'services.agents.sistema_agent'),
]

for agent_key, agent_class_name, agent_module in agents_to_test:
    try:
        module = __import__(agent_module, fromlist=[agent_class_name])
        agent_class = getattr(module, agent_class_name)
        print(f"   ✅ {agent_class_name} importado")
        
        # Tentar instanciar
        try:
            instance = agent_class()
            print(f"      ✅ {agent_class_name} instanciado com sucesso")
        except Exception as e:
            print(f"      ❌ Erro ao instanciar {agent_class_name}: {e}")
            traceback.print_exc()
    except Exception as e:
        print(f"   ❌ Erro ao importar {agent_class_name}: {e}")
        traceback.print_exc()

# Teste 4: Verificar tool mapping
print()
print("4️⃣  Verificando mapeamento de tools...")
if router.tool_to_agent:
    print(f"   ✅ {len(router.tool_to_agent)} tools mapeadas")
    # Verificar algumas tools importantes
    important_tools = ['obter_dashboard_hoje', 'listar_processos', 'consultar_status_processo']
    for tool in important_tools:
        agent = router.tool_to_agent.get(tool)
        if agent:
            print(f"      ✅ {tool} → {agent}")
        else:
            print(f"      ⚠️  {tool} não mapeada")
else:
    print("   ❌ Nenhuma tool mapeada!")

# Teste 5: Testar roteamento de uma tool
print()
print("5️⃣  Testando roteamento de tool...")
test_tool = 'obter_dashboard_hoje'
agent_name = router.tool_to_agent.get(test_tool)
if agent_name:
    print(f"   📍 Tool '{test_tool}' mapeada para agent '{agent_name}'")
    if agent_name in router.agents:
        print(f"   ✅ Agent '{agent_name}' está disponível")
    else:
        print(f"   ❌ Agent '{agent_name}' NÃO está disponível!")
        print(f"      Agents disponíveis: {list(router.agents.keys())}")
else:
    print(f"   ⚠️  Tool '{test_tool}' não está mapeada")

print()
print("=" * 60)
print("DIAGNÓSTICO CONCLUÍDO")
print("=" * 60)
