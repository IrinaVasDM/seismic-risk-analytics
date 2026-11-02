"""Загрузка исходных данных из открытых API USGS и NOAA.

Запуск:  python -m seismic.download
Файлы сохраняются в data/raw/ и в git не попадают (см. .gitignore).
"""

import io
import json
import time
import urllib.parse
import urllib.request

import pandas as pd

from seismic import config

USGS_COLUMNS = ["time", "latitude", "longitude", "depth", "mag", "magType", "place", "type", "id"]


def _get(url: str, params: dict | None = None, retries: int = 3) -> bytes:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                return resp.read()
        except OSError:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def download_usgs(start_year: int = config.USGS_START_YEAR,
                  end_year: int = config.USGS_END_YEAR,
                  min_mag: float = config.USGS_MIN_MAG) -> pd.DataFrame:
    """Каталог USGS по годам: API отдаёт не больше 20 000 событий за запрос."""
    frames = []
    for year in range(start_year, end_year + 1):
        raw = _get(config.USGS_URL, {
            "format": "csv",
            "starttime": f"{year}-01-01",
            "endtime": f"{year + 1}-01-01",
            "minmagnitude": min_mag,
            "orderby": "time-asc",
        })
        df = pd.read_csv(io.BytesIO(raw), usecols=USGS_COLUMNS)
        frames.append(df)
        print(f"  USGS {year}: {len(df):>6} событий")
    return pd.concat(frames, ignore_index=True)


def download_noaa(url: str, start_year: int = config.NOAA_START_YEAR,
                  end_year: int = config.NOAA_END_YEAR) -> pd.DataFrame:
    """Постраничная выгрузка из NOAA Hazard Service (200 записей на страницу)."""
    items, page = [], 1
    while True:
        payload = json.loads(_get(url, {"minYear": start_year, "maxYear": end_year, "page": page}))
        items.extend(payload["items"])
        if page >= payload["totalPages"]:
            break
        page += 1
    return pd.DataFrame(items)


def download_land() -> None:
    target = config.GEO_DIR / "ne_110m_land.geojson"
    if not target.exists():
        target.write_bytes(_get(config.LAND_GEOJSON_URL))


def main() -> None:
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    config.GEO_DIR.mkdir(parents=True, exist_ok=True)

    print("Каталог USGS…")
    download_usgs().to_csv(config.RAW_DIR / "usgs_catalog.csv.gz", index=False)

    print("Значимые землетрясения NOAA…")
    eq = download_noaa(config.NOAA_EQ_URL)
    eq.to_csv(config.RAW_DIR / "noaa_earthquakes.csv", index=False)
    print(f"  {len(eq)} записей")

    print("Цунами NOAA…")
    ts = download_noaa(config.NOAA_TSUNAMI_URL)
    ts.to_csv(config.RAW_DIR / "noaa_tsunamis.csv", index=False)
    print(f"  {len(ts)} записей")

    download_land()
    print("Готово.")


if __name__ == "__main__":
    main()
