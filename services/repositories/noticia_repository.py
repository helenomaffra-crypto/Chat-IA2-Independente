"""
Repository para operações com notícias do Siscomex.
Seguindo padrão de refatoração: extraído do db_manager.py.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class NoticiaRepository:
    """Repository para consultar notícias do Siscomex"""
    
    def listar_noticias(
        self,
        fonte: Optional[str] = None,
        limite: int = 20,
        dias_retroativos: Optional[int] = None,
        apenas_nao_lidas: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Lista notícias do Siscomex.
        
        Args:
            fonte: Fonte da notícia ('siscomex_importacao' ou 'siscomex_sistemas') ou None para todas
            limite: Número máximo de notícias a retornar (padrão: 20)
            dias_retroativos: Número de dias para buscar (None = todas)
            apenas_nao_lidas: Se True, retorna apenas notícias não notificadas (padrão: False)
        
        Returns:
            Lista de notícias com estrutura:
            {
                'id': int,
                'guid': str,
                'titulo': str,
                'descricao': str,
                'link': str,
                'data_publicacao': str (ISO),
                'fonte': str,
                'notificada': bool,
                'criado_em': str (ISO)
            }
        """
        try:
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Construir query dinamicamente
            where_clauses = []
            params = []
            
            if fonte:
                where_clauses.append("fonte = ?")
                params.append(fonte)
            
            if dias_retroativos:
                data_limite = datetime.now() - timedelta(days=dias_retroativos)
                where_clauses.append("data_publicacao >= ?")
                params.append(data_limite.isoformat())
            
            if apenas_nao_lidas:
                where_clauses.append("notificada = 0")
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f'''
                SELECT id, guid, titulo, descricao, link, data_publicacao, fonte, notificada, criado_em
                FROM noticias_siscomex
                WHERE {where_sql}
                ORDER BY data_publicacao DESC, criado_em DESC
                LIMIT ?
            '''
            
            params.append(limite)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            noticias = []
            for row in rows:
                noticia = {
                    'id': row[0],
                    'guid': row[1],
                    'titulo': row[2],
                    'descricao': row[3] or '',
                    'link': row[4],
                    'data_publicacao': row[5],
                    'fonte': row[6],
                    'notificada': bool(row[7]),
                    'criado_em': row[8]
                }
                noticias.append(noticia)
            
            logger.info(f"✅ Listadas {len(noticias)} notícias (fonte={fonte}, limite={limite})")
            return noticias
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar notícias: {e}", exc_info=True)
            return []
    
    def buscar_noticia_por_guid(self, guid: str) -> Optional[Dict[str, Any]]:
        """
        Busca uma notícia específica por GUID.
        
        Args:
            guid: GUID único da notícia
        
        Returns:
            Dict com dados da notícia ou None se não encontrada
        """
        try:
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, guid, titulo, descricao, link, data_publicacao, fonte, notificada, criado_em
                FROM noticias_siscomex
                WHERE guid = ?
            ''', (guid,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'guid': row[1],
                'titulo': row[2],
                'descricao': row[3] or '',
                'link': row[4],
                'data_publicacao': row[5],
                'fonte': row[6],
                'notificada': bool(row[7]),
                'criado_em': row[8]
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar notícia por GUID: {e}", exc_info=True)
            return None
    
    def contar_noticias(
        self,
        fonte: Optional[str] = None,
        dias_retroativos: Optional[int] = None
    ) -> int:
        """
        Conta total de notícias.
        
        Args:
            fonte: Fonte da notícia ou None para todas
            dias_retroativos: Número de dias para buscar (None = todas)
        
        Returns:
            Número total de notícias
        """
        try:
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            where_clauses = []
            params = []
            
            if fonte:
                where_clauses.append("fonte = ?")
                params.append(fonte)
            
            if dias_retroativos:
                data_limite = datetime.now() - timedelta(days=dias_retroativos)
                where_clauses.append("data_publicacao >= ?")
                params.append(data_limite.isoformat())
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f'SELECT COUNT(*) FROM noticias_siscomex WHERE {where_sql}'
            
            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            conn.close()
            
            return count
            
        except Exception as e:
            logger.error(f"❌ Erro ao contar notícias: {e}", exc_info=True)
            return 0
