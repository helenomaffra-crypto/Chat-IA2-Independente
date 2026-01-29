import logging
from datetime import date, datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def remover_acentos(texto: str) -> str:
    if not texto:
        return texto
    import unicodedata

    nfd = unicodedata.normalize("NFD", texto)
    return "".join(char for char in nfd if unicodedata.category(char) != "Mn")


def parse_data_desembaraco_para_date(valor: str) -> Optional[date]:
    """Converte diferentes formatos de timestamp em date(), retornando None se falhar."""
    if not valor:
        return None

    data_limpa = str(valor).replace("Z", "").replace("+00:00", "").strip()
    if "." in data_limpa:
        data_limpa = data_limpa.split(".")[0]

    dt_desembaraco: Optional[datetime] = None
    if "T" in data_limpa:
        try:
            dt_desembaraco = datetime.fromisoformat(data_limpa)
        except Exception:
            dt_desembaraco = None

    if not dt_desembaraco:
        formatos = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
        for fmt in formatos:
            try:
                dt_desembaraco = datetime.strptime(data_limpa, fmt)
                break
            except Exception:
                continue

    if not dt_desembaraco:
        return None

    return dt_desembaraco.date()


def corresponde_filtro_data_desembaraco(data_desembaraco_date: date, filtro_data_desembaraco: str) -> bool:
    """Aplica filtro humano (hoje/ontem/semana/mes/data específica) sobre a data de desembaraço."""
    filtro_lower = (filtro_data_desembaraco or "").lower().strip()
    hoje = date.today()

    if filtro_lower == "hoje":
        return data_desembaraco_date == hoje
    if filtro_lower == "ontem":
        return data_desembaraco_date == (hoje - timedelta(days=1))
    if filtro_lower in ("semana", "esta semana", "nesta semana"):
        dias_ate_segunda = hoje.weekday()
        segunda_semana = hoje - timedelta(days=dias_ate_segunda)
        domingo_semana = segunda_semana + timedelta(days=6)
        return segunda_semana <= data_desembaraco_date <= domingo_semana
    if filtro_lower in ("mes", "este mes", "neste mes"):
        primeiro_dia = date(hoje.year, hoje.month, 1)
        if hoje.month == 12:
            ultimo_dia = date(hoje.year + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo_dia = date(hoje.year, hoje.month + 1, 1) - timedelta(days=1)
        return primeiro_dia <= data_desembaraco_date <= ultimo_dia

    # Data específica DD/MM/AAAA
    try:
        data_especifica = datetime.strptime(filtro_data_desembaraco, "%d/%m/%Y").date()
        return data_desembaraco_date == data_especifica
    except Exception:
        # comportamento legado: se não entendeu filtro, não filtrar
        return True

