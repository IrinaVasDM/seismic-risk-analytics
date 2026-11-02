"""Пути и параметры проекта, общие для всех модулей."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
GEO_DIR = DATA_DIR / "geo"
SQL_DIR = ROOT / "sql"
FIGURES_DIR = ROOT / "figures"

DB_PATH = PROCESSED_DIR / "seismic.db"

# Каталог USGS: с 1973 года глобальная сеть стабильно фиксирует события M≥4.5
USGS_START_YEAR = 1973
USGS_END_YEAR = 2025
USGS_MIN_MAG = 4.5

# Каталог значимых землетрясений NOAA: берём XX–XXI века
NOAA_START_YEAR = 1900
NOAA_END_YEAR = 2025

USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
NOAA_EQ_URL = "https://www.ngdc.noaa.gov/hazel/hazard-service/api/v1/earthquakes"
NOAA_TSUNAMI_URL = "https://www.ngdc.noaa.gov/hazel/hazard-service/api/v1/tsunamis/events"
LAND_GEOJSON_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_110m_land.geojson"
)
