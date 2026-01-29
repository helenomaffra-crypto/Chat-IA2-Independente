"""
Utilitário para verificar disponibilidade de fontes de dados.
"""
import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


def verificar_fontes_dados_disponiveis() -> Dict[str, Any]:
    """
    Verifica quais fontes de dados estão disponíveis.
    
    Returns:
        Dict com status de cada fonte:
        {
            'sqlite': {
                'disponivel': bool,
                'mensagem': str,
                'tabelas': int (opcional)
            },
            'sql_server': {
                'disponivel': bool,
                'mensagem': str,
                'erro': str (se houver)
            },
            'api_kanban': {
                'disponivel': bool,
                'mensagem': str
            },
            'api_portal_unico': {
                'disponivel': bool,
                'mensagem': str
            }
        }
    """
    resultado = {
        'sqlite': {'disponivel': False, 'mensagem': ''},
        'sql_server': {'disponivel': False, 'mensagem': ''},
        'api_kanban': {'disponivel': False, 'mensagem': ''},
        'api_portal_unico': {'disponivel': False, 'mensagem': ''},
        'api_integracomex': {'disponivel': False, 'mensagem': ''},
        'api_shipsgo': {'disponivel': False, 'mensagem': ''},
    }
    
    # 1. Verificar SQLite (sempre disponível se o arquivo existir)
    try:
        db_path = Path('chat_ia.db')
        if db_path.exists():
            import sqlite3
            conn = sqlite3.connect('chat_ia.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tabelas = cursor.fetchall()
            conn.close()
            
            resultado['sqlite'] = {
                'disponivel': True,
                'mensagem': f'✅ SQLite disponível (offline) - {len(tabelas)} tabela(s)',
                'tabelas': len(tabelas)
            }
        else:
            resultado['sqlite'] = {
                'disponivel': False,
                'mensagem': '❌ SQLite não encontrado (arquivo chat_ia.db não existe)'
            }
    except Exception as e:
        logger.warning(f"⚠️ Erro ao verificar SQLite: {e}")
        resultado['sqlite'] = {
            'disponivel': False,
            'mensagem': f'❌ SQLite com erro: {str(e)[:50]}'
        }
    
    # 2. Verificar SQL Server (precisa estar na rede do escritório)
    try:
        from utils.sql_server_adapter import get_sql_adapter
        sql_adapter = get_sql_adapter()
        if sql_adapter:
            # Tentar uma query simples para verificar conexão
            try:
                # ✅ CORREÇÃO: Usar test_connection com notificar_erro=False
                # para evitar notificações duplicadas na UI
                test_result = sql_adapter.test_connection(notificar_erro=False)
                if test_result.get('success'):
                    resultado['sql_server'] = {
                        'disponivel': True,
                        'mensagem': '✅ SQL Server disponível (rede do escritório)'
                    }
                else:
                    error_msg = test_result.get('error', 'Erro desconhecido')
                    resultado['sql_server'] = {
                        'disponivel': False,
                        'mensagem': '❌ SQL Server não disponível',
                        'erro': error_msg[:100]
                    }
            except Exception as e:
                resultado['sql_server'] = {
                    'disponivel': False,
                    'mensagem': '❌ SQL Server não disponível (fora da rede do escritório)',
                    'erro': str(e)[:100]
                }
        else:
            resultado['sql_server'] = {
                'disponivel': False,
                'mensagem': '❌ SQL Server não configurado'
            }
    except ImportError:
        resultado['sql_server'] = {
            'disponivel': False,
            'mensagem': '❌ SQL Server adapter não disponível'
        }
    except Exception as e:
        logger.debug(f"SQL Server não disponível: {e}")
        resultado['sql_server'] = {
            'disponivel': False,
            'mensagem': '❌ SQL Server não disponível (fora da rede do escritório)',
            'erro': str(e)[:100] if str(e) else 'Erro de conexão'
        }
    
    # 3. Verificar API Kanban (verificar variável de ambiente)
    try:
        import os
        kanban_api_url = os.getenv('KANBAN_API_URL') or os.getenv('API_KANBAN_URL')
        if kanban_api_url:
            # Tentar fazer uma requisição simples (opcional - pode ser pesado)
            # Por enquanto, só verificar se a URL está configurada
            resultado['api_kanban'] = {
                'disponivel': True,
                'mensagem': f'✅ API Kanban configurada ({kanban_api_url[:30]}...)'
            }
        else:
            resultado['api_kanban'] = {
                'disponivel': False,
                'mensagem': '⚠️ API Kanban não configurada (variável KANBAN_API_URL não encontrada)'
            }
    except Exception as e:
        resultado['api_kanban'] = {
            'disponivel': False,
            'mensagem': f'❌ Erro ao verificar API Kanban: {str(e)[:50]}'
        }
    
    # 4. Verificar API Portal Único (verificar variável de ambiente)
    try:
        import os
        portal_unico_url = os.getenv('PORTAL_UNICO_API_URL') or os.getenv('DUIMP_API_URL')
        portal_unico_token = os.getenv('PORTAL_UNICO_API_TOKEN') or os.getenv('DUIMP_API_TOKEN')
        if portal_unico_url and portal_unico_token:
            resultado['api_portal_unico'] = {
                'disponivel': True,
                'mensagem': '✅ API Portal Único configurada'
            }
        else:
            resultado['api_portal_unico'] = {
                'disponivel': False,
                'mensagem': '⚠️ API Portal Único não configurada (variáveis PORTAL_UNICO_API_URL/TOKEN não encontradas)'
            }
    except Exception as e:
        resultado['api_portal_unico'] = {
            'disponivel': False,
            'mensagem': f'❌ Erro ao verificar API Portal Único: {str(e)[:50]}'
        }
    
    # 5. Verificar API Integra Comex / Serpro (token mTLS)
    try:
        import os
        integracomex_token = os.getenv('INTEGRACOMEX_TOKEN')
        if integracomex_token:
            resultado['api_integracomex'] = {
                'disponivel': True,
                'mensagem': '✅ API Integra Comex configurada (token presente)'
            }
        else:
            resultado['api_integracomex'] = {
                'disponivel': False,
                'mensagem': '⚠️ API Integra Comex não configurada (INTEGRACOMEX_TOKEN não encontrado)'
            }
    except Exception as e:
        resultado['api_integracomex'] = {
            'disponivel': False,
            'mensagem': f'❌ Erro ao verificar API Integra Comex: {str(e)[:50]}'
        }

    # 6. Verificar API ShipsGo (tracking)
    # Obs: nomes de variáveis podem variar por ambiente; cobrimos alguns comuns.
    try:
        import os
        shipsgo_api_key = (
            os.getenv('SHIPSGO_API_KEY')
            or os.getenv('SHIPSGO_TOKEN')
            or os.getenv('SHIPSGO_BEARER_TOKEN')
        )
        if shipsgo_api_key:
            resultado['api_shipsgo'] = {
                'disponivel': True,
                'mensagem': '✅ API ShipsGo configurada (chave/token presente)'
            }
        else:
            resultado['api_shipsgo'] = {
                'disponivel': False,
                'mensagem': '⚠️ API ShipsGo não configurada (SHIPSGO_API_KEY/TOKEN não encontrado)'
            }
    except Exception as e:
        resultado['api_shipsgo'] = {
            'disponivel': False,
            'mensagem': f'❌ Erro ao verificar API ShipsGo: {str(e)[:50]}'
        }

    return resultado


def formatar_status_fontes_dados(status: Dict[str, Any]) -> str:
    """
    Formata o status das fontes de dados em uma mensagem amigável.
    
    Args:
        status: Resultado de verificar_fontes_dados_disponiveis()
        
    Returns:
        String formatada com o status
    """
    mensagem = "📊 **FONTES DE DADOS DISPONÍVEIS:**\n\n"
    
    for fonte, info in status.items():
        nome_fonte = {
            'sqlite': '💾 SQLite (Local/Offline)',
            'sql_server': '🗄️ SQL Server (Rede do Escritório)',
            'api_kanban': '🌐 API Kanban',
            'api_portal_unico': '🌐 API Portal Único (DUIMP)',
            'api_integracomex': '🌐 API Integra Comex (CE/DI/CCT)',
            'api_shipsgo': '🌐 API ShipsGo (Tracking/ETA)',
        }.get(fonte, fonte)
        
        mensagem += f"{info['mensagem']}\n"
        if info.get('erro'):
            mensagem += f"   ⚠️ Detalhes: {info['erro']}\n"
        mensagem += "\n"
    
    # Resumo
    disponiveis = [f for f, info in status.items() if info.get('disponivel')]
    if disponiveis:
        mensagem += f"✅ **Fontes disponíveis:** {', '.join(disponiveis)}\n"
    else:
        mensagem += "⚠️ **Nenhuma fonte de dados disponível no momento.**\n"
    
    return mensagem













