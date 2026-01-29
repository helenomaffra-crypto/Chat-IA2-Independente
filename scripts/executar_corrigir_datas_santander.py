"""
Script Python para executar a correção de datas do Santander via SQL Server.
"""
import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Carregar .env
from dotenv import load_dotenv
load_dotenv(root_dir / '.env')

from utils.sql_server_adapter import get_sql_adapter

def executar_correcao_sql():
    """Executa o script SQL de correção de datas."""
    adapter = get_sql_adapter()
    if not adapter:
        print("❌ SQL Server não disponível")
        return
    
    database = 'mAIke_assistente'
    
    # Ler o script SQL
    sql_file = root_dir / 'scripts' / 'corrigir_datas_santander_sql_direto.sql'
    if not sql_file.exists():
        print(f"❌ Arquivo SQL não encontrado: {sql_file}")
        return
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Dividir em comandos individuais (separados por GO ou ;)
    # Remover comentários e linhas vazias
    commands = []
    current_command = []
    
    for line in sql_content.split('\n'):
        line = line.strip()
        if not line or line.startswith('--') or line.upper() == 'GO':
            if current_command:
                commands.append('\n'.join(current_command))
                current_command = []
            continue
        
        current_command.append(line)
    
    if current_command:
        commands.append('\n'.join(current_command))
    
    print(f"🔍 Executando {len(commands)} comandos SQL...")
    
    total_atualizados = 0
    
    for i, cmd in enumerate(commands, 1):
        if not cmd.strip() or cmd.strip().upper().startswith('USE '):
            continue
        
        # Se for SELECT, executar e mostrar resultado
        if cmd.strip().upper().startswith('SELECT'):
            print(f"\n📊 Executando consulta {i}...")
            resultado = adapter.execute_query(cmd, database=database)
            if resultado.get('success') and resultado.get('data'):
                rows = resultado['data']
                for row in rows:
                    if isinstance(row, dict):
                        print(f"  {row}")
                    else:
                        print(f"  {row}")
        else:
            # UPDATE ou outros comandos
            print(f"🔄 Executando comando {i}...")
            resultado = adapter.execute_query(cmd, database=database)
            if resultado.get('success'):
                # Tentar extrair número de linhas afetadas
                if 'rows_affected' in resultado:
                    total_atualizados += resultado.get('rows_affected', 0)
                print(f"  ✅ Comando executado com sucesso")
            else:
                error_msg = resultado.get('error', 'Erro desconhecido')
                print(f"  ⚠️ Aviso: {error_msg}")
    
    print(f"\n✅ Correção concluída!")
    print(f"📊 Total de lançamentos atualizados: {total_atualizados}")
    print(f"\n💡 Agora os lançamentos do dia 08/01/2026 devem aparecer corretamente na tela de conciliação!")

if __name__ == '__main__':
    executar_correcao_sql()


