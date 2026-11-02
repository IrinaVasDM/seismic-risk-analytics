"""Доступ к SQLite: выполнение именованных запросов из sql/queries/."""

import sqlite3
from contextlib import closing

import pandas as pd

from seismic import config


def connect() -> sqlite3.Connection:
    if not config.DB_PATH.exists():
        raise FileNotFoundError(
            f"{config.DB_PATH} не найден — запустите `python -m seismic.download` и `python -m seismic.etl`"
        )
    return sqlite3.connect(config.DB_PATH)


def read_query(name: str) -> str:
    """Текст запроса по имени файла без расширения, например '02_zone_activity'."""
    return (config.SQL_DIR / "queries" / f"{name}.sql").read_text(encoding="utf-8")


def query(name_or_sql: str, params: dict | None = None) -> pd.DataFrame:
    """Выполнить запрос из файла (по имени) или произвольный SQL."""
    sql = name_or_sql if " " in name_or_sql.strip() else read_query(name_or_sql)
    with closing(connect()) as con:
        return pd.read_sql_query(sql, con, params=params or {})
