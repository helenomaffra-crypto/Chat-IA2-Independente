# -*- coding: latin-1 -*-
"""
Adaptador SQL Server para Chat IA Independente.

Suporta duas opes:
1. pyodbc (recomendado se funcionar)
2. Node.js adapter (fallback do prottipo)

Configurao via variveis de ambiente:
- SQL_SERVER
- SQL_USERNAME
- SQL_PASSWORD
- SQL_DATABASE
"""
import os
import json
import logging
from typing import Optional, List, Any, Dict
from pathlib import Path
import socket

logger = logging.getLogger(__name__)

# Carregar variveis de ambiente

def load_env_from_file(filepath: str = '.env') -> None:
    """Carrega variveis de ambiente do arquivo .env"""
    # Tentar vrios caminhos possveis
    possible_paths = [
        Path(filepath),
        Path(__file__).parent.parent / filepath if '__file__' in globals() else None,
        Path(os.getcwd()) / filepath,
        Path('/Users/helenomaffra/Chat-IA-Independente') / filepath,  # ? NOVO: Caminho absoluto do workspace atual
        Path('/Users/helenomaffra/Documents/GitHub/Chat-IA-Independente') / filepath,
    ]
    
    for path in possible_paths:
        if path and path.exists():
            abs_path = path.absolute()
            try:
                with open(abs_path, 'r', encoding='utf-8') as env_file:
                    for line in env_file:
                        s = line.strip()
                        if not s or s.startswith('#') or '=' not in s:
                            continue
                        k, v = s.split('=', 1)
                        # Remover aspas do valor
                        v_clean = v.strip().strip('"').strip("'")
                        os.environ[k.strip()] = v_clean
                logger.debug(f" Carregado .env de: {abs_path}")
                return
            except OSError as e:
                logger.debug(f"Erro ao ler .env de {abs_path}: {e}")
                continue
    logger.warning(" Arquivo .env no encontrado em nenhum dos caminhos possveis")


load_env_from_file()

# Configuraes SQL Server
SQL_SERVER = os.getenv('SQL_SERVER', r'172.16.10.8\SQLEXPRESS')
SQL_USERNAME = os.getenv('SQL_USERNAME', 'sa')
SQL_PASSWORD = os.getenv('SQL_PASSWORD', '')
SQL_DATABASE = os.getenv('SQL_DATABASE', 'Make')

# ? NOVO (19/01/2026): Suporte a 2 ambientes (Escritrio vs VPN) com seleo automtica.
# Exemplos:
# - SQL_SERVER_OFFICE=SMKCADM1-001\SQLEXPRESS
# - SQL_SERVER_VPN=sqlserver.matriz.local\SQLEXPRESS
SQL_SERVER_OFFICE = os.getenv('SQL_SERVER_OFFICE', '').strip()
SQL_SERVER_VPN = os.getenv('SQL_SERVER_VPN', '').strip()
SQL_SERVER_MODE = os.getenv('SQL_SERVER_MODE', 'auto').strip().lower()  # 'auto'|'office'|'vpn'|'legacy'


def _parse_sql_server_value(sql_server_value: str) -> tuple[str, Optional[str], str]:
    """
    Parseia valor do SQL Server no formato:
    - "HOST\\INSTANCE" ou "HOST"
    Retorna: (host, instance, full_value)
    """
    v = (sql_server_value or '').strip()
    if not v:
        return '', None, ''
    if '\\' in v:
        parts = v.split('\\', 1)
        return parts[0].strip(), parts[1].strip() or None, v
    return v, None, v


def _quick_tcp_probe(host: str, port: int = 1433, timeout_sec: float = 1.2) -> tuple[bool, str]:
    """
    Probe rpido: DNS + tentativa TCP na porta 1433.
    Isso NO garante que a instncia named esteja acessvel (pode usar porta dinmica),
    mas ajuda a decidir ambiente sem esperar timeouts longos.
    """
    try:
        if not host:
            return False, 'host_vazio'
        # DNS
        socket.getaddrinfo(host, None)
    except Exception as e:
        return False, f'dns_falhou:{type(e).__name__}'
    try:
        with socket.create_connection((host, port), timeout=timeout_sec):
            return True, 'ok'
    except Exception as e:
        # Pode ser firewall/porta diferente - ainda assim serve como sinal forte de indisponibilidade.
        return False, f'tcp_falhou:{type(e).__name__}'


class SQLServerAdapter:
    """Adaptador para consultas SQL Server.
    
    Tenta usar pyodbc primeiro, fallback para Node.js adapter se necessrio.
    """
    
    def __init__(self):
        """Inicializa o adaptador."""
        import platform
        
        #  Recarregar .env antes de usar variveis
        load_env_from_file()
        
        # ? Selecionar host automaticamente (escritrio vs VPN) se configurado
        self._sql_server_candidates: List[str] = self._build_sql_server_candidates()
        self._sql_server_mode = os.getenv('SQL_SERVER_MODE', SQL_SERVER_MODE).strip().lower()
        self._sql_server_selected_profile = 'legacy'
        self._sql_server_selected_value = os.getenv('SQL_SERVER', SQL_SERVER)

        self._selecionar_sql_server_inicial()

        # Re-carregar variveis aps seleo
        server_env_value = os.getenv('SQL_SERVER', SQL_SERVER)
        self.server = server_env_value.split('\\')[0] if '\\' in server_env_value else server_env_value
        self.instance = server_env_value.split('\\')[1] if '\\' in server_env_value else None
        self.username = os.getenv('SQL_USERNAME', SQL_USERNAME)
        self.password = os.getenv('SQL_PASSWORD', SQL_PASSWORD)
        self.database = os.getenv('SQL_DATABASE', SQL_DATABASE)
        
        #  DETECTAR macOS e priorizar Node.js (pyodbc tem problemas conhecidos no Mac)
        IS_MACOS = platform.system() == 'Darwin'
        
        self.use_node = self._test_node_adapter()
        self.use_pyodbc = self._test_pyodbc() if not IS_MACOS else False  # No tentar pyodbc no macOS
        
        if IS_MACOS:
            if self.use_node:
                logger.debug("macOS detectado - Usando Node.js adapter (pyodbc no  confivel no Mac)")
            else:
                logger.error("L macOS detectado mas Node.js adapter no disponvel!")
        else:
            # Em outros sistemas, tentar pyodbc primeiro
            if self.use_pyodbc:
                if self.use_node:
                    logger.info(" Usando pyodbc para SQL Server (Node.js disponvel como fallback)")
                else:
                    logger.debug("Usando pyodbc para SQL Server")
            elif self.use_node:
                logger.warning(" pyodbc no disponvel, usando Node.js adapter...")
            else:
                logger.error("L Nenhum adaptador SQL Server disponvel!")

    def _build_sql_server_candidates(self) -> List[str]:
        """
        Monta lista de candidatos a SQL Server com base em env vars.
        Prioridade:
        - Se SQL_SERVER_OFFICE/SQL_SERVER_VPN existirem: usar esses (modo auto por padro)
        - Caso contrrio: usar SQL_SERVER (legacy)
        """
        office = os.getenv('SQL_SERVER_OFFICE', SQL_SERVER_OFFICE).strip()
        vpn = os.getenv('SQL_SERVER_VPN', SQL_SERVER_VPN).strip()
        legacy = os.getenv('SQL_SERVER', SQL_SERVER).strip()

        candidates: List[str] = []
        if office:
            candidates.append(office)
        if vpn and vpn not in candidates:
            candidates.append(vpn)
        if not candidates and legacy:
            candidates.append(legacy)
        return candidates

    def _selecionar_sql_server_inicial(self) -> None:
        """
        Seleciona SQL_SERVER no startup (auto/office/vpn/legacy).
        Estratgia:
        - office/vpn: seleciona explicitamente
        - auto: escolhe the primeiro candidato que passar no probe rpido; se nenhum passar, mantm o primeiro
        - legacy: mantm SQL_SERVER atual
        """
        mode = (os.getenv('SQL_SERVER_MODE', SQL_SERVER_MODE) or 'auto').strip().lower()
        office = os.getenv('SQL_SERVER_OFFICE', SQL_SERVER_OFFICE).strip()
        vpn = os.getenv('SQL_SERVER_VPN', SQL_SERVER_VPN).strip()
        legacy = os.getenv('SQL_SERVER', SQL_SERVER).strip()

        def _set(value: str, profile: str) -> None:
            if value:
                os.environ['SQL_SERVER'] = value
                self._sql_server_selected_value = value
                self._sql_server_selected_profile = profile

        if mode in ('office', 'escritorio'):
            # ? Robustez: se office est forado mas no responde, cair para VPN/legacy.
            chosen = office or legacy
            host, _inst, full = _parse_sql_server_value(chosen)
            ok, reason = _quick_tcp_probe(host)
            if ok:
                _set(full, 'office')
            else:
                fallback = vpn or legacy
                logger.warning(f"?? SQL_SERVER_MODE=office mas probe falhou ({reason}) para {full}. Tentando fallback: {fallback}")
                _set(fallback, 'vpn' if vpn and fallback == vpn else 'legacy')
            return
        if mode in ('vpn',):
            # ? Robustez: se VPN est forada mas no responde (ex.: usurio est no escritrio sem VPN),
            # cair para OFFICE/legacy e evitar timeouts longos em cada query.
            chosen = vpn or legacy
            host, _inst, full = _parse_sql_server_value(chosen)
            ok, reason = _quick_tcp_probe(host)
            if ok:
                _set(full, 'vpn')
            else:
                fallback = office or legacy
                logger.warning(f"?? SQL_SERVER_MODE=vpn mas probe falhou ({reason}) para {full}. Tentando fallback: {fallback}")
                _set(fallback, 'office' if office and fallback == office else 'legacy')
            return
        if mode in ('legacy', 'single'):
            _set(legacy, 'legacy')
            return

        # auto
        # Se no houver candidatos, mantm legacy
        if not self._sql_server_candidates:
            _set(legacy, 'legacy')
            return

        # Probe rpido para evitar timeout longo
        best_value = self._sql_server_candidates[0]
        best_profile = 'office' if office and best_value == office else ('vpn' if vpn and best_value == vpn else 'legacy')
        for cand in self._sql_server_candidates:
            host, _inst, full = _parse_sql_server_value(cand)
            ok, reason = _quick_tcp_probe(host)
            if ok:
                best_value = full
                if office and full == office:
                    best_profile = 'office'
                elif vpn and full == vpn:
                    best_profile = 'vpn'
                else:
                    best_profile = 'legacy'
                logger.info(f"? SQL Server selecionado (auto): {best_value} (probe={reason})")
                _set(best_value, best_profile)
                return

        # Nenhum passou no probe: manter o primeiro e registrar contexto para mensagens melhores
        logger.warning(
            f"?? Nenhum host SQL Server passou no probe rpido. Mantendo {best_value}. "
            f"(modo=auto, office={'sim' if office else 'no'}, vpn={'sim' if vpn else 'no'})"
        )
        _set(best_value, best_profile)
    
    def _test_pyodbc(self) -> bool:
        """Testa se pyodbc est disponvel."""
        try:
            import pyodbc
            return True
        except ImportError:
            return False
    
    def _test_node_adapter(self) -> bool:
        """Testa se Node.js adapter est disponvel."""
        # Primeiro, tenta encontrar script Node.js local (no prprio projeto)
        script_dir = Path(__file__).parent
        node_script_local = script_dir / 'sql_server_node.js'
        
        # Fallback: script do prottipo (se existir)
        node_script_prototype = Path('/Users/helenomaffra/CHAT IA/backend/infrastructure/db/sql_server_node.js')
        
        # Verificar se Node.js est instalado
        try:
            import subprocess
            result = subprocess.run(['node', '--version'], capture_output=True, timeout=5)
            if result.returncode != 0:
                return False
        except Exception:
            return False
        
        # Verificar se script existe
        if node_script_local.exists():
            return True
        elif node_script_prototype.exists():
            logger.info(f" Usando script Node.js do prottipo: {node_script_prototype}")
            return True
        
        return False
    
    def execute_query(self, sql_query: str, database: Optional[str] = None, params: Optional[List[Any]] = None, notificar_erro: bool = False) -> Dict[str, Any]:
        """Executa query SQL no SQL Server.
        
        Args:
            sql_query: Query SQL
            database: Nome do banco (opcional, usa padro se None)
            params: Parmetros da query (opcional)
        
        Returns:
            Dict com success, data ou error
        """
        database = database or self.database
        
        if self.use_pyodbc:
            return self._execute_with_pyodbc(sql_query, database, params, notificar_erro=notificar_erro)
        elif self.use_node:
            return self._execute_with_node(sql_query, database, params, notificar_erro=notificar_erro)
        else:
            return {
                'success': False,
                'error': 'Nenhum adaptador SQL Server disponvel. Instale pyodbc ou configure Node.js adapter.'
            }
    
    def _execute_with_pyodbc(self, sql_query: str, database: str, params: Optional[List[Any]] = None, notificar_erro: bool = False) -> Dict[str, Any]:
        """Executa query usando pyodbc. Se falhar, tenta Node.js adapter como fallback."""
        try:
            import pyodbc
            
            # Detectar driver
            drivers = pyodbc.drivers()
            if "ODBC Driver 18 for SQL Server" in drivers:
                driver_name = "ODBC Driver 18 for SQL Server"
            elif "ODBC Driver 17 for SQL Server" in drivers:
                driver_name = "ODBC Driver 17 for SQL Server"
            else:
                # Se no tem driver, tentar Node.js somente se estiver disponvel
                error_msg = "ODBC Driver 17/18 para SQL Server no encontrado no ambiente."
                if self.use_node:
                    logger.warning(f"?? {error_msg} Tentando Node.js adapter...")
                    return self._execute_with_node(sql_query, database, params, notificar_erro=notificar_erro)
                if notificar_erro:
                    self._notificar_erro_conexao(error_msg, tipo='pyodbc_erro')
                else:
                    logger.debug(f"?? Erro SQL Server (no notificado): {error_msg}")
                return {'success': False, 'error': error_msg}
            
            # Construir connection string
            server_full = f"{self.server}\\{self.instance}" if self.instance else self.server
            conn_str = (
                f"DRIVER={{{driver_name}}};"
                f"SERVER={server_full};"
                f"DATABASE={database};"
                f"UID={self.username};"
                f"PWD={self.password};"
                "TrustServerCertificate=yes;"
                "Encrypt=yes;"
            )
            
            # Conectar e executar
            conn = pyodbc.connect(conn_str)
            try:
                cursor = conn.cursor()

                if params:
                    cursor.execute(sql_query, params)
                else:
                    cursor.execute(sql_query)

                # ? IMPORTANTE: INSERT/UPDATE/DELETE no tem cursor.description e NO deve chamar fetchall()
                if not cursor.description:
                    conn.commit()
                    return {
                        'success': True,
                        'data': [],
                        'rows_affected': cursor.rowcount
                    }

                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
                data = [dict(zip(columns, row)) for row in rows]

                return {
                    'success': True,
                    'data': data
                }
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        except Exception as e:
            error_msg = f"Erro ao executar query via pyodbc: {e}"
            logger.error(error_msg)

            # Fallback para Node.js SOMENTE se estiver disponvel (evita erro 'node' no encontrado em Docker)
            if self.use_node:
                return self._execute_with_node(sql_query, database, params, notificar_erro=notificar_erro)

            if notificar_erro:
                self._notificar_erro_conexao(error_msg, tipo='pyodbc_erro')
            else:
                logger.debug(f"?? Erro SQL Server (no notificado): {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
    
    def _execute_with_node(self, sql_query: str, database: str, params: Optional[List[Any]] = None, notificar_erro: bool = False) -> Dict[str, Any]:
        """Executa query usando Node.js adapter."""
        import subprocess
        
        script_dir = Path(__file__).parent
        node_script_local = script_dir / 'sql_server_node.js'
        node_script_prototype = Path('/Users/helenomaffra/CHAT IA/backend/infrastructure/db/sql_server_node.js')
        
        if node_script_local.exists():
            node_script = node_script_local
        elif node_script_prototype.exists():
            node_script = node_script_prototype
        else:
            return {
                'success': False,
                'error': 'Script Node.js adapter no encontrado.'
            }
        
        # ? CORREO: O script Node.js espera formato: node script.js query <sql> [database]
        # E l credenciais de process.env (SQL_SERVER, SQL_USERNAME, SQL_PASSWORD, SQL_DATABASE)
        cmd = [
            'node',
            str(node_script),
            'query',
            sql_query,
        ]
        
        # Adicionar database se fornecido
        if database:
            cmd.append(database)
        
        # Preparar variveis de ambiente para passar ao Node.js
        env = os.environ.copy()
        # ? Robustez (19/01/2026): Alguns ambientes resolvem DNS no Python mas no no Node (ex.: *.local via VPN).
        # Resolver host no Python e passar IP para o Node evita ENOTFOUND no adapter.
        server_for_node = self.server
        try:
            if self.server and not all(ch.isdigit() or ch == '.' for ch in self.server):
                infos = socket.getaddrinfo(self.server, None)
                ips = [i[4][0] for i in infos if i and i[4] and i[4][0]]
                if ips:
                    server_for_node = ips[0]
        except Exception:
            server_for_node = self.server

        env['SQL_SERVER'] = server_for_node
        if self.instance:
            env['SQL_SERVER'] = f"{server_for_node}\\{self.instance}"
        env['SQL_USERNAME'] = self.username
        env['SQL_PASSWORD'] = self.password
        env['SQL_DATABASE'] = database or self.database
        
        try:
            # ? CORREO: Usar stdout e stderr separadamente (no usar capture_output=True)
            # O console.error do Node.js vai para stderr e no deve corromper o JSON do stdout
            import subprocess
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,  # ? Capturar stdout separadamente
                stderr=subprocess.PIPE,  # ? Capturar stderr separadamente
                text=True,
                timeout=120,  # ? Aumentar timeout para queries grandes (318 registros)
                env=env
            )
            
            if result.returncode != 0:
                # ? CORREO: Tentar parsear JSON do stdout primeiro (pode conter erro estruturado)
                error_msg = None
                try:
                    if result.stdout.strip():
                        parsed = json.loads(result.stdout.strip())
                        if not parsed.get('success') and parsed.get('error'):
                            error_msg = parsed.get('error')
                            if parsed.get('code'):
                                error_msg += f" (code: {parsed.get('code')})"
                except (json.JSONDecodeError, ValueError):
                    pass
                
                # Se no encontrou erro no JSON, usar stderr ou stdout
                if not error_msg:
                    # Filtrar mensagens de log do console.error (ex: "[SQL Server Node] Conectando a:")
                    stderr_lines = result.stderr.strip().split('\n') if result.stderr.strip() else []
                    stdout_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
                    
                    # Procurar linha que no seja apenas log de conexo
                    for line in stderr_lines + stdout_lines:
                        if line and '[SQL Server Node] Conectando a:' not in line:
                            error_msg = line
                            break
                    
                    # Se no encontrou, usar primeira linha no vazia
                    if not error_msg:
                        all_lines = stderr_lines + stdout_lines
                        error_msg = next((line for line in all_lines if line.strip()), 'Erro desconhecido no Node.js adapter')
                
                # ? CORREO: Detectar se  erro de conexo (normal quando fora da rede)
                is_connection_error = any(keyword in error_msg.lower() for keyword in [
                    'econnrefused', 'etimedout', 'timeout', 'connection', 
                    'connect econnrefused', 'network', 'unreachable', '172.16',
                    'login failed', 'authentication', 'cannot open database'
                ])
                
                if is_connection_error:
                    # Erro de conexo  esperado quando est fora da rede do escritrio
                    # Logar como WARNING (no ERROR) para no assustar o usurio
                    logger.warning(f"?? SQL Server no acessvel (fora da rede do escritrio): {error_msg[:100]}")
                else:
                    # Outros erros so mais crticos, logar como ERROR
                    logger.error(f"? Node.js adapter erro (code {result.returncode}): {error_msg[:200]}")
                
                # ? CORREO: S notificar erro se explicitamente solicitado
                # Por padro, no notifica para no incomodar usurio com erros no crticos
                # (ex: quando consulta funciona via cache, mas enriquecimento SQL Server falha)
                if notificar_erro:
                    self._notificar_erro_conexao(error_msg)
                else:
                    logger.debug(f"?? Erro SQL Server (no notificado): {error_msg[:100]}")
                
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Parse do JSON retornado pelo Node.js
            try:
                # ? CORREO: Separar stderr (logs) do stdout (JSON)
                # O stderr pode conter logs de conexo que no devem ser parseados como JSON
                output = result.stdout.strip()
                
                # ? CORREO MELHORADA: Extrair JSON vlido mesmo se estiver truncado ou corrompido
                if output:
                    # Procurar pelo primeiro '{' que indica incio do JSON
                    json_start = output.find('{')
                    if json_start >= 0:
                        # ? NOVO: Extrair JSON de forma mais robusta
                        # Estratgia: encontrar o JSON completo contando chaves abertas/fechadas
                        bracket_count = 0
                        json_end = -1
                        in_string = False
                        escape_next = False
                        
                        for i in range(json_start, len(output)):
                            char = output[i]
                            
                            # Controlar se estamos dentro de uma string
                            if escape_next:
                                escape_next = False
                                continue
                            
                            if char == '\\':
                                escape_next = True
                                continue
                            
                            if char == '"' and not escape_next:
                                in_string = not in_string
                                continue
                            
                            # S contar chaves se no estiver dentro de string
                            if not in_string:
                                if char == '{':
                                    bracket_count += 1
                                elif char == '}':
                                    bracket_count -= 1
                                    if bracket_count == 0:
                                        json_end = i
                                        break
                        
                        # Se encontrou JSON completo, usar ele
                        if json_end > json_start:
                            output = output[json_start:json_end+1]
                        else:
                            # Se no encontrou JSON completo, tentar usar at o ltimo '}' disponvel
                            # (pode estar truncado, mas pelo menos tentamos parsear o que temos)
                            last_brace = output.rfind('}')
                            if last_brace > json_start:
                                # Tentar encontrar o JSON vlido mais prximo do final
                                # Contando chaves de trs para frente
                                bracket_count = 0
                                for i in range(last_brace, json_start - 1, -1):
                                    if output[i] == '}':
                                        bracket_count += 1
                                    elif output[i] == '{':
                                        bracket_count -= 1
                                        if bracket_count == 0:
                                            output = output[json_start:i+1]
                                            break
                            else:
                                # ltimo recurso: usar tudo a partir do primeiro '{'
                                output = output[json_start:]
                
                if not output:
                    return {
                        'success': False,
                        'error': 'Node.js adapter nao retornou nenhuma saida'
                    }
                
                # ? CORREO: Logar tamanho do JSON para debug
                logger.debug(f"?? Tamanho do JSON recebido: {len(output)} caracteres")
                
                # ? NOVO: Tentar parsear JSON, se falhar, tentar reparar JSON truncado
                try:
                    data = json.loads(output)
                except json.JSONDecodeError as json_err:
                    # ? NOVO: Tentar reparar JSON truncado removendo ltimo registro incompleto
                    logger.warning(f"?? JSON corrompido na posio {json_err.pos if hasattr(json_err, 'pos') else 'desconhecida'}, tentando reparar...")
                    
                    # Estratgia simples: encontrar ltimo objeto completo no array e fechar o JSON
                    # Procurar padro: }, (fechamento de objeto seguido de vrgula ou fechamento de array)
                    error_pos = json_err.pos if hasattr(json_err, 'pos') else len(output)
                    
                    # Procurar ltimo '}' seguido de ',' ou ']' antes do erro
                    # Isso indica fim de um objeto vlido no array
                    for i in range(min(error_pos, len(output) - 1), json_start, -1):
                        if output[i] == '}' and i + 1 < len(output):
                            next_char = output[i + 1]
                            if next_char in [',', '\n', ']']:
                                # Encontrou fim de objeto vlido, tentar fechar o JSON
                                # Procurar onde est o array
                                array_start = output.find('"data": [', json_start)
                                if array_start > 0:
                                    # Tentar fechar: remover tudo aps o objeto vlido e fechar array + objeto principal
                                    repaired = output[:i+1] + '\n  ]\n}'
                                    try:
                                        data = json.loads(repaired)
                                        logger.info(f"? JSON reparado com sucesso (removido {len(output) - len(repaired)} caracteres)")
                                        output = repaired  # Usar JSON reparado
                                        break
                                    except:
                                        continue
                    
                    # Se ainda no conseguiu reparar, tentar mtodo mais simples: remover ltimo registro
                    if 'data' not in locals() or not isinstance(locals().get('data'), dict):
                        # Procurar ltima vrgula antes do erro e remover ltimo objeto
                        last_comma = output.rfind(',', json_start, error_pos)
                        if last_comma > 0:
                            # Remover da ltima vrgula at o erro e fechar JSON
                            repaired = output[:last_comma] + '\n  ]\n}'
                            try:
                                data = json.loads(repaired)
                                logger.info(f"? JSON reparado (mtodo simples: removido ltimo registro)")
                            except:
                                # Se ainda falhar, levantar erro original
                                raise json_err
                        else:
                            raise json_err
                        
            except json.JSONDecodeError as e:
                # ? CORREO: Logar mais detalhes para debug
                logger.error(f"? Erro ao decodificar JSON do Node.js: {e}")
                logger.error(f"? Primeiros 1000 chars do stdout: {result.stdout[:1000]}")
                logger.error(f"? ltimos 1000 chars do stdout: {result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout}")
                logger.error(f"? stderr completo: {result.stderr[:500] if result.stderr else 'vazio'}")
                logger.error(f"? Tamanho total do stdout: {len(result.stdout)} caracteres")
                return {
                    'success': False,
                    'error': f'Erro ao decodificar JSON do Node.js: {e}'
                }
            
            if isinstance(data, dict) and 'error' in data and not data.get('success', True):
                error_msg = data.get('error', 'Erro no Node.js adapter')
                
                # ? CORREO: Detectar se  erro de conexo (normal quando fora da rede)
                is_connection_error = any(keyword in error_msg.lower() for keyword in [
                    'econnrefused', 'etimedout', 'timeout', 'connection', 
                    'connect econnrefused', 'network', 'unreachable', '172.16'
                ])
                
                if is_connection_error:
                    # Erro de conexo  esperado quando est fora da rede do escritrio
                    logger.warning(f"?? SQL Server no acessvel (fora da rede do escritrio): {error_msg[:100]}")
                else:
                    logger.error(f"? Erro no Node.js adapter: {error_msg[:200]}")
                
                # ? CORREO: S notificar erro se explicitamente solicitado
                if notificar_erro:
                    self._notificar_erro_conexao(error_msg, tipo='node_adapter_erro')
                else:
                    logger.debug(f"?? Erro SQL Server (no notificado): {error_msg[:100]}")
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Se for dict com 'data' (formato esperado do script)
            if isinstance(data, dict) and 'data' in data:
                return {
                    'success': data.get('success', True),
                    'data': data.get('data', [])
                }
            # Se for lista de registros
            elif isinstance(data, list):
                return {
                    'success': True,
                    'data': data
                }
            
            # Qualquer outro formato, retornar como est
            return {
                'success': True,
                'data': data
            }
        except subprocess.TimeoutExpired:
            error_msg = 'Timeout ao executar query via Node.js adapter'
            # ? CORREO: S notificar erro se explicitamente solicitado
            if notificar_erro:
                self._notificar_erro_conexao(error_msg, tipo='timeout')
            else:
                logger.debug(f"?? Erro SQL Server (no notificado): {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f'Erro ao executar query via Node.js adapter: {e}'
            # ? CORREO: S notificar erro se explicitamente solicitado
            if notificar_erro:
                self._notificar_erro_conexao(error_msg, tipo='erro_generico')
            else:
                logger.debug(f"?? Erro SQL Server (no notificado): {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }

    def test_connection(self, notificar_erro: bool = False) -> Dict[str, Any]:
        """
        Testa conexo com SQL Server com uma query simples.
        Usado pelo app.py no startup.
        
        Retorna um dict compatvel com o que app.py espera:
        { "success": bool, "error": str | None }
        """
        try:
            # ? CORREO: Passar notificar_erro para execute_query
            result = self.execute_query("SELECT 1", notificar_erro=notificar_erro)
            if result.get('success'):
                return {"success": True, "error": None}
            else:
                error_msg = result.get("error", "Erro ao executar SELECT 1")
                # ? CORREO: S notificar se explicitamente solicitado
                if notificar_erro:
                    self._notificar_erro_conexao(error_msg, tipo='teste_conexao_falhou')
                else:
                    logger.warning(f"?? Teste de conexo SQL Server falhou: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
        except Exception as e:
            logger.error(f"Erro em test_connection do SQLServerAdapter: {e}")
            # ? CORREO: S notificar se explicitamente solicitado
            if notificar_erro:
                self._notificar_erro_conexao(str(e), tipo='teste_conexao_excecao')
            return {"success": False, "error": str(e)}
    
    def _notificar_erro_conexao(self, error_msg: str, tipo: str = 'conexao_falhou') -> None:
        """
        Notifica erro de conexo SQL Server ao usurio.
        
        Args:
            error_msg: Mensagem de erro
            tipo: Tipo do erro ('timeout', 'conexao_falhou', 'node_adapter_erro', 'pyodbc_erro', 'erro_generico')
        """
        try:
            # Detectar tipo especfico de erro
            error_lower = error_msg.lower()
            # ? Mensagem contextual quando h configurao office/vpn
            office = os.getenv('SQL_SERVER_OFFICE', '').strip()
            vpn = os.getenv('SQL_SERVER_VPN', '').strip()
            modo = os.getenv('SQL_SERVER_MODE', 'auto').strip().lower()
            tem_duplo_ambiente = bool(office and vpn)
            dica_vpn = ""
            if tem_duplo_ambiente:
                dica_vpn = (
                    "\n\n?? **Dica rpida (VPN):** parece que voc est fora da rede do escritrio. "
                    "Conecte a VPN e tente novamente.\n"
                    f"- Escritrio: `{office}`\n"
                    f"- VPN: `{vpn}`\n"
                    f"- Modo atual: `{modo}`"
                )

            if 'timeout' in error_lower or 'etimout' in error_lower:
                tipo_erro = 'sql_server_timeout'
                mensagem = (
                    '?? Timeout ao conectar ao SQL Server.\n\n'
                    'O servidor no respondeu a tempo. Verifique a conexo de rede ou se o servidor est online.'
                    + dica_vpn
                )
            elif 'enotfound' in error_lower or 'einstlookup' in error_lower or 'getaddrinfo' in error_lower:
                tipo_erro = 'sql_server_dns_falhou'
                mensagem = (
                    '?? No foi possvel resolver o endereo do SQL Server.\n\n'
                    'Verifique se o hostname/IP est correto no arquivo .env (SQL_SERVER).'
                    + dica_vpn
                )
            elif 'failed to connect' in error_lower or 'connection' in error_lower:
                tipo_erro = 'sql_server_conexao_falhou'
                mensagem = (
                    f'? Falha ao conectar ao SQL Server.\n\nErro: {error_msg}\n\n'
                    'Verifique se o servidor est online e as credenciais esto corretas.'
                    + dica_vpn
                )
            else:
                tipo_erro = f'sql_server_{tipo}'
                mensagem = (
                    f'?? Erro ao acessar SQL Server.\n\nErro: {error_msg}\n\n'
                    'O sistema est usando cache local. Algumas informaes podem estar desatualizadas.'
                    + dica_vpn
                )
            
            # Importar NotificacaoService e criar notificao
            from services.notificacao_service import NotificacaoService
            notificacao_service = NotificacaoService()
            notificacao_service.notificar_erro_sistema(
                tipo_erro=tipo_erro,
                mensagem=mensagem,
                detalhes={
                    'erro_original': error_msg,
                    'tipo': tipo,
                    'server': self.server,
                    'database': self.database
                }
            )
        except Exception as e:
            # No logar erro aqui para evitar loop infinito
            logger.debug(f"Erro ao criar notificao de erro de conexo: {e}")



# Singleton para o adapter SQL Server
_sql_adapter_instance: Optional[SQLServerAdapter] = None

def get_sql_adapter() -> Optional[SQLServerAdapter]:
    """Retorna uma instância do adaptador SQL Server (singleton), se possível."""
    global _sql_adapter_instance
    
    # Se já existe uma instância, reutilizar
    if _sql_adapter_instance is not None:
        # ? Se o ambiente mudou (ex.: office → VPN), recriar adapter para não ficar preso no host antigo.
        try:
            env_server = (os.getenv('SQL_SERVER') or '').strip()
            env_mode = (os.getenv('SQL_SERVER_MODE') or 'auto').strip().lower()
            
            inst_server = getattr(_sql_adapter_instance, 'server', '') or ''
            inst_instance = getattr(_sql_adapter_instance, 'instance', None)
            inst_full = f"{inst_server}\\{inst_instance}" if inst_instance else inst_server
            inst_mode = getattr(_sql_adapter_instance, '_sql_server_mode', 'auto').strip().lower()
            
            if (env_server and inst_full and env_server != inst_full) or (env_mode != inst_mode):
                logger.info(f"🔄 SQLServerAdapter: detectada mudança de config (server: {inst_full} → {env_server}, mode: {inst_mode} → {env_mode}). Recriando adapter.")
                _sql_adapter_instance = None
        except Exception:
            # Se falhar a checagem, mantém instância atual
            pass
        if _sql_adapter_instance is not None:
            return _sql_adapter_instance
    
    try:
        adapter = SQLServerAdapter()
        if not adapter.use_pyodbc and not adapter.use_node:
            return None
        # Armazenar instância para reutilização
        _sql_adapter_instance = adapter
        return adapter
    except Exception as e:
        logger.error(f"Erro ao inicializar SQLServerAdapter: {e}")
        return None
