"""Очистка сырых данных (pandas) и загрузка в SQLite.

Запуск:  python -m seismic.etl
"""

import sqlite3

import numpy as np
import pandas as pd

from seismic import config, regions
from seismic.stats import haversine_km

DEPTH_BINS = [-np.inf, 70, 300, np.inf]
DEPTH_LABELS = ["мелкофокусное", "промежуточное", "глубокофокусное"]


def clean_usgs(raw: pd.DataFrame) -> pd.DataFrame:
    df = (
        raw.loc[raw["type"].eq("earthquake")]
        .drop_duplicates(subset="id")
        .dropna(subset=["mag", "latitude", "longitude"])
        .rename(columns={"id": "event_id", "depth": "depth_km", "magType": "mag_type"})
        .copy()
    )
    df["time_utc"] = pd.to_datetime(df["time"], utc=True, format="ISO8601")
    df["year"] = df["time_utc"].dt.year
    df["mag"] = df["mag"].round(1)
    df["mag_type"] = df["mag_type"].str.lower()
    df["depth_class"] = pd.cut(df["depth_km"], DEPTH_BINS, labels=DEPTH_LABELS).astype("string")

    # «12 km SSW of Kokopo, Papua New Guinea» → «Papua New Guinea»;
    # «southeast of the Loyalty Islands» → «Loyalty Islands»;
    # «2010 Maule, Chile Earthquake» → «Chile»
    area = df["place"].fillna("").str.split(",").str[-1].str.strip()
    area = area.str.replace(r"^\d+\s*km\s+\w+\s+of\s+", "", regex=True)
    area = area.str.replace(r"^\d{4}\s+", "", regex=True)
    area = area.str.replace(r"\s+(?:Earthquake|Aftershock|earthquake sequence)$", "", regex=True)
    # направления в USGS пишутся строчными, поэтому «South Sandwich Islands» не страдает
    area = area.str.replace(r"^(?:(?:north|south)?(?:east|west)?(?:ern)?|central|near the coast of|"
                            r"off the coast of)\s+(?:of\s+)?(?:the\s+)?", "", regex=True)
    area = area.str.replace(r"\s+region$", "", regex=True)
    df["area"] = area.replace("", pd.NA)

    df["zone_id"] = regions.assign_zone(df["latitude"].to_numpy(), df["longitude"].to_numpy())
    df = df.sort_values("time_utc").reset_index(drop=True)
    return df[["event_id", "time_utc", "year", "latitude", "longitude", "depth_km", "depth_class",
               "mag", "mag_type", "place", "area", "zone_id"]]


def _noaa_timestamp(df: pd.DataFrame) -> pd.Series:
    parts = pd.DataFrame({
        "year": df["year"],
        "month": df["month"].fillna(1),
        "day": df["day"].fillna(1),
        "hour": df["hour"].fillna(0),
        "minute": df["minute"].fillna(0),
        "second": df["second"].fillna(0).clip(upper=59.99),
    })
    return pd.to_datetime(parts, errors="coerce", utc=True)


def clean_noaa_earthquakes(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["time_utc"] = _noaa_timestamp(df)
    # Total-поля включают вторичные эффекты (цунами, пожары, оползни)
    for col in ["deaths", "injuries", "damageMillionsDollars", "housesDestroyed",
                "deathsAmountOrder", "damageAmountOrder"]:
        total = f"{col}Total"
        df[col] = df[total].combine_first(df[col]) if total in df else df.get(col)

    df = df.rename(columns={
        "id": "noaa_id", "eqDepth": "depth_km", "eqMagnitude": "mag", "locationName": "location",
        "deathsAmountOrder": "deaths_order", "damageMillionsDollars": "damage_musd",
        "damageAmountOrder": "damage_order", "housesDestroyed": "houses_destroyed",
        "tsunamiEventId": "tsunami_id",
    })
    df["location"] = df["location"].str.replace(r"\s+", " ", regex=True).str.strip()
    df["country"] = df["country"].str.title()
    df["zone_id"] = np.where(
        df["latitude"].notna(),
        regions.assign_zone(df["latitude"].fillna(0).to_numpy(), df["longitude"].fillna(0).to_numpy()),
        pd.NA,
    )
    cols = ["noaa_id", "time_utc", "year", "latitude", "longitude", "depth_km", "mag", "country",
            "location", "deaths", "deaths_order", "injuries", "damage_musd", "damage_order",
            "houses_destroyed", "intensity", "tsunami_id", "zone_id"]
    return df[cols].sort_values("time_utc").reset_index(drop=True)


def clean_noaa_tsunamis(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.loc[raw["causeCode"].eq(1)].copy()     # 1 = вызвано землетрясением
    df["deaths"] = df["deathsTotal"].combine_first(df.get("deaths"))
    df = df.rename(columns={
        "id": "tsunami_id", "locationName": "location", "eqMagnitude": "eq_mag",
        "eqDepth": "eq_depth_km", "maxWaterHeight": "max_water_height_m",
        "numRunups": "num_runups", "eventValidity": "validity", "earthquakeEventId": "noaa_eq_id",
    })
    df["country"] = df["country"].str.title()
    cols = ["tsunami_id", "year", "country", "location", "latitude", "longitude", "eq_mag",
            "eq_depth_km", "max_water_height_m", "num_runups", "deaths", "validity", "noaa_eq_id"]
    return df[cols]


def link_noaa_to_usgs(significant: pd.DataFrame, events: pd.DataFrame,
                      max_seconds: int = 90, max_km: float = 150, max_dmag: float = 0.8) -> pd.Series:
    """Сопоставление событий NOAA с каталогом USGS.

    merge_asof находит ближайшее по времени событие USGS, затем пара
    отбраковывается по расстоянию между эпицентрами и разнице магнитуд.
    """
    left = significant.dropna(subset=["time_utc"]).loc[lambda d: d["year"] >= config.USGS_START_YEAR]
    left = left[["noaa_id", "time_utc", "latitude", "longitude", "mag"]].sort_values("time_utc")
    right = events[["event_id", "time_utc", "latitude", "longitude", "mag"]].sort_values("time_utc")
    # ключи merge_asof должны иметь одинаковое разрешение времени
    left["time_utc"] = left["time_utc"].astype("datetime64[ns, UTC]")
    right = right.assign(time_utc=right["time_utc"].astype("datetime64[ns, UTC]"))

    pairs = pd.merge_asof(left, right, on="time_utc", direction="nearest",
                          tolerance=pd.Timedelta(seconds=max_seconds), suffixes=("", "_usgs"))
    distance = haversine_km(pairs["latitude"], pairs["longitude"],
                            pairs["latitude_usgs"], pairs["longitude_usgs"])
    ok = (distance <= max_km) & ((pairs["mag"] - pairs["mag_usgs"]).abs().fillna(0) <= max_dmag)
    matched = pairs.loc[ok, ["noaa_id", "event_id"]].drop_duplicates("event_id")
    return significant["noaa_id"].map(matched.set_index("noaa_id")["event_id"])


def _to_sql_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.select_dtypes(include=["datetimetz", "datetime"]).columns:
        out[col] = out[col].dt.strftime("%Y-%m-%dT%H:%M:%S")
    return out


def build_database() -> None:
    events = clean_usgs(pd.read_csv(config.RAW_DIR / "usgs_catalog.csv.gz"))
    significant = clean_noaa_earthquakes(pd.read_csv(config.RAW_DIR / "noaa_earthquakes.csv"))
    tsunamis = clean_noaa_tsunamis(pd.read_csv(config.RAW_DIR / "noaa_tsunamis.csv"))
    significant["usgs_event_id"] = link_noaa_to_usgs(significant, events)
    # оставляем только ссылки на землетрясения, присутствующие в significant
    tsunamis.loc[~tsunamis["noaa_eq_id"].isin(significant["noaa_id"]), "noaa_eq_id"] = pd.NA

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    config.DB_PATH.unlink(missing_ok=True)
    with sqlite3.connect(config.DB_PATH) as con:
        con.executescript((config.SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
        regions.zones_frame().to_sql("zones", con, if_exists="append", index=False)
        _to_sql_frame(events).to_sql("events", con, if_exists="append", index=False, chunksize=20_000)
        _to_sql_frame(significant).to_sql("significant", con, if_exists="append", index=False)
        tsunamis.to_sql("tsunamis", con, if_exists="append", index=False)
        con.execute("ANALYZE")

    linked = significant["usgs_event_id"].notna().sum()
    print(f"events: {len(events):,} | significant: {len(significant):,} "
          f"(связано с USGS: {linked:,}) | tsunamis: {len(tsunamis):,}")
    print(f"База: {config.DB_PATH}")


if __name__ == "__main__":
    build_database()
