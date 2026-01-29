"""
Serviço genérico para consulta de CPF/CNPJ via APIs externas.

Pode ser usado por qualquer banco (BB, Santander, etc.) para enriquecer
informações de contrapartida com nome da pessoa/empresa.

APIs suportadas:
- ReceitaWS (gratuita, sem cadastro)
- Outras APIs podem ser adicionadas no futuro
"""
import os
import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import sqlite3

logger = logging.getLogger(__name__)

# Cache local em SQLite para evitar consultas repetidas
CACHE_DB = "cpf_cnpj_cache.db"
CACHE_VALIDADE_DAYS = 30  # Cache válido por 30 dias


class ConsultaCpfCnpjService:
    """Serviço genérico para consulta de CPF/CNPJ."""
    
    def __init__(self):
        """Inicializa o serviço e cria cache se necessário."""
        self._init_cache()
    
    def _init_cache(self):
        """Inicializa banco de cache SQLite."""
        try:
            conn = sqlite3.connect(CACHE_DB)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS consultas_cpf_cnpj (
                    cpf_cnpj TEXT PRIMARY KEY,
                    nome TEXT,
                    tipo TEXT,
                    situacao TEXT,
                    data_consulta TIMESTAMP,
                    data_validade TIMESTAMP,
                    dados_json TEXT
                )
            ''')
            conn.commit()
            conn.close()
            logger.info("✅ Cache de CPF/CNPJ inicializado")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar cache: {e}", exc_info=True)
    
    def consultar(self, cpf_cnpj: str, tipo: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Consulta CPF/CNPJ e retorna informações (nome, situação, etc.).
        
        Args:
            cpf_cnpj: CPF (11 dígitos) ou CNPJ (14 dígitos) sem formatação
            tipo: 'CPF' ou 'CNPJ' (opcional, detecta automaticamente se não fornecido)
        
        Returns:
            Dict com informações ou None se não encontrado:
            {
                'nome': str,
                'tipo': 'CPF' ou 'CNPJ',
                'situacao': str (para CNPJ),
                'cpf_cnpj': str (formatado),
                'fonte': str (nome da API usada)
            }
        """
        if not cpf_cnpj:
            return None
        
        # Limpar formatação
        cpf_cnpj_limpo = ''.join(filter(str.isdigit, cpf_cnpj))
        
        # Detectar tipo se não fornecido
        if not tipo:
            if len(cpf_cnpj_limpo) == 11:
                tipo = 'CPF'
            elif len(cpf_cnpj_limpo) == 14:
                tipo = 'CNPJ'
            else:
                logger.warning(f"⚠️ CPF/CNPJ inválido: {cpf_cnpj_limpo} (tamanho: {len(cpf_cnpj_limpo)})")
                return None
        
        # Verificar cache primeiro
        cache_result = self._buscar_cache(cpf_cnpj_limpo)
        if cache_result:
            logger.info(f"✅ CPF/CNPJ {cpf_cnpj_limpo} encontrado no cache")
            return cache_result
        
        # Consultar API
        try:
            if tipo == 'CNPJ':
                resultado = self._consultar_cnpj_receitaws(cpf_cnpj_limpo)
            else:
                # CPF - ReceitaWS não suporta CPF, mas podemos adicionar outras APIs no futuro
                logger.warning(f"⚠️ Consulta de CPF não implementada ainda: {cpf_cnpj_limpo}")
                return None
            
            # Salvar no cache se encontrado
            if resultado:
                self._salvar_cache(cpf_cnpj_limpo, resultado)
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro ao consultar {tipo} {cpf_cnpj_limpo}: {e}", exc_info=True)
            return None
    
    def _consultar_cnpj_receitaws(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """
        Consulta CNPJ na ReceitaWS (gratuita, sem cadastro).
        
        Args:
            cnpj: CNPJ sem formatação (14 dígitos)
        
        Returns:
            Dict com informações ou None
        """
        try:
            # ReceitaWS: https://www.receitaws.com.br/
            # API pública e gratuita, sem necessidade de cadastro
            # ⚠️ IMPORTANTE: Rate limiting - máximo 3 consultas por minuto
            url = f"https://www.receitaws.com.br/v1/cnpj/{cnpj}"
            
            logger.info(f"🔍 Consultando CNPJ {cnpj} na ReceitaWS...")
            response = requests.get(url, timeout=10)
            
            # ✅ Tratar rate limiting (HTTP 429)
            if response.status_code == 429:
                logger.warning(f"⚠️ Rate limit atingido na ReceitaWS para CNPJ {cnpj} (HTTP 429)")
                logger.warning(f"⚠️ ReceitaWS permite apenas 3 consultas por minuto (API gratuita)")
                logger.warning(f"⚠️ CNPJ será exibido sem nome (limite da API gratuita)")
                # Não tentar novamente - retornar None imediatamente
                return None
            
            # ✅ Tratar outros erros HTTP
            if response.status_code != 200:
                logger.warning(f"⚠️ Erro HTTP {response.status_code} ao consultar CNPJ {cnpj} na ReceitaWS")
                return None
            
            if response.status_code == 200:
                data = response.json()
                
                # Verificar se CNPJ é válido
                if data.get('status') == 'ERROR':
                    logger.warning(f"⚠️ CNPJ {cnpj} inválido ou não encontrado")
                    return None
                
                # Extrair informações
                nome = data.get('nome', '')
                situacao = data.get('situacao', '')
                abertura = data.get('abertura', '')
                natureza_juridica = data.get('natureza_juridica', '')
                logradouro = data.get('logradouro', '')
                numero = data.get('numero', '')
                bairro = data.get('bairro', '')
                municipio = data.get('municipio', '')
                uf = data.get('uf', '')
                cep = data.get('cep', '')
                
                # Formatar CNPJ
                cnpj_formatado = f"{cnpj[0:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
                
                resultado = {
                    'nome': nome,
                    'tipo': 'CNPJ',
                    'situacao': situacao,
                    'cpf_cnpj': cnpj_formatado,
                    'fonte': 'ReceitaWS',
                    'abertura': abertura,
                    'natureza_juridica': natureza_juridica,
                    'endereco': {
                        'logradouro': logradouro,
                        'numero': numero,
                        'bairro': bairro,
                        'municipio': municipio,
                        'uf': uf,
                        'cep': cep
                    },
                    'dados_completos': data  # Salvar dados completos para cache
                }
                
                logger.info(f"✅ CNPJ {cnpj} consultado com sucesso: {nome}")
                return resultado
            else:
                logger.warning(f"⚠️ Erro ao consultar CNPJ {cnpj}: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ Timeout ao consultar CNPJ {cnpj} na ReceitaWS")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao consultar CNPJ {cnpj} na ReceitaWS: {e}", exc_info=True)
            return None
    
    def _buscar_cache(self, cpf_cnpj: str) -> Optional[Dict[str, Any]]:
        """Busca resultado no cache."""
        try:
            conn = sqlite3.connect(CACHE_DB)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT nome, tipo, situacao, dados_json, data_validade
                FROM consultas_cpf_cnpj
                WHERE cpf_cnpj = ? AND data_validade > datetime('now')
            ''', (cpf_cnpj,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                import json
                dados = json.loads(row[3]) if row[3] else {}
                return {
                    'nome': row[0],
                    'tipo': row[1],
                    'situacao': row[2],
                    'cpf_cnpj': self._formatar_cpf_cnpj(cpf_cnpj, row[1]),
                    'fonte': 'Cache',
                    **dados
                }
            
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao buscar cache: {e}", exc_info=True)
            return None
    
    def _salvar_cache(self, cpf_cnpj: str, resultado: Dict[str, Any]):
        """Salva resultado no cache."""
        try:
            import json
            conn = sqlite3.connect(CACHE_DB)
            cursor = conn.cursor()
            
            data_consulta = datetime.now()
            data_validade = data_consulta + timedelta(days=CACHE_VALIDADE_DAYS)
            
            # Preparar dados para salvar
            dados_json = json.dumps({
                'abertura': resultado.get('abertura'),
                'natureza_juridica': resultado.get('natureza_juridica'),
                'endereco': resultado.get('endereco'),
                'fonte': resultado.get('fonte')
            })
            
            cursor.execute('''
                INSERT OR REPLACE INTO consultas_cpf_cnpj
                (cpf_cnpj, nome, tipo, situacao, data_consulta, data_validade, dados_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                cpf_cnpj,
                resultado.get('nome'),
                resultado.get('tipo'),
                resultado.get('situacao', ''),
                data_consulta.isoformat(),
                data_validade.isoformat(),
                dados_json
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"✅ CPF/CNPJ {cpf_cnpj} salvo no cache")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar cache: {e}", exc_info=True)
    
    def _formatar_cpf_cnpj(self, cpf_cnpj: str, tipo: str) -> str:
        """Formata CPF/CNPJ para exibição."""
        if tipo == 'CPF' and len(cpf_cnpj) == 11:
            return f"{cpf_cnpj[0:3]}.{cpf_cnpj[3:6]}.{cpf_cnpj[6:9]}-{cpf_cnpj[9:11]}"
        elif tipo == 'CNPJ' and len(cpf_cnpj) == 14:
            return f"{cpf_cnpj[0:2]}.{cpf_cnpj[2:5]}.{cpf_cnpj[5:8]}/{cpf_cnpj[8:12]}-{cpf_cnpj[12:14]}"
        return cpf_cnpj

