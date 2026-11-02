-- Схема базы seismic.db (SQLite)
--
--   zones ─┬─< events >── significant >── tsunamis
--          │     (USGS)      (NOAA)        (NOAA)
--
-- events      — инструментальный каталог USGS, M ≥ 4.5, 1973–2025
-- significant — значимые землетрясения NOAA (с жертвами/ущербом), 1900–2025;
--               usgs_event_id связывает их с каталогом USGS (с 1973 г.)
-- tsunamis    — события цунами NOAA, вызванные землетрясениями

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS tsunamis;
DROP TABLE IF EXISTS significant;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS zones;

CREATE TABLE zones (
    zone_id        INTEGER PRIMARY KEY,
    name           TEXT    NOT NULL UNIQUE,
    boundary_type  TEXT    NOT NULL           -- субдукция / коллизия / трансформная
);

CREATE TABLE events (
    event_id     TEXT    PRIMARY KEY,         -- идентификатор USGS
    time_utc     TEXT    NOT NULL,            -- ISO 8601
    year         INTEGER NOT NULL,
    latitude     REAL    NOT NULL,
    longitude    REAL    NOT NULL,
    depth_km     REAL,
    depth_class  TEXT    CHECK (depth_class IN ('мелкофокусное', 'промежуточное', 'глубокофокусное')),
    mag          REAL    NOT NULL,
    mag_type     TEXT,
    place        TEXT,
    area         TEXT,                        -- страна / акватория, извлечённая из place
    zone_id      INTEGER NOT NULL REFERENCES zones(zone_id)
);

CREATE INDEX idx_events_time ON events(time_utc);
CREATE INDEX idx_events_zone_mag ON events(zone_id, mag);

CREATE TABLE significant (
    noaa_id           INTEGER PRIMARY KEY,
    time_utc          TEXT,
    year              INTEGER NOT NULL,
    latitude          REAL,
    longitude         REAL,
    depth_km          REAL,
    mag               REAL,
    country           TEXT,
    location          TEXT,
    deaths            INTEGER,                -- с учётом вторичных эффектов (цунами, пожары)
    deaths_order      INTEGER,                -- шкала NOAA 1–4, если точное число неизвестно
    injuries          INTEGER,
    damage_musd       REAL,                   -- ущерб, млн долларов (номинал)
    damage_order      INTEGER,
    houses_destroyed  INTEGER,
    intensity         INTEGER,                -- Модифицированная шкала Меркалли
    tsunami_id        INTEGER,
    zone_id           INTEGER REFERENCES zones(zone_id),
    usgs_event_id     TEXT    REFERENCES events(event_id)
);

CREATE INDEX idx_significant_year ON significant(year);

CREATE TABLE tsunamis (
    tsunami_id         INTEGER PRIMARY KEY,
    year               INTEGER NOT NULL,
    country            TEXT,
    location           TEXT,
    latitude           REAL,
    longitude          REAL,
    eq_mag             REAL,
    eq_depth_km        REAL,
    max_water_height_m REAL,
    num_runups         INTEGER,
    deaths             INTEGER,
    validity           INTEGER,               -- 4 = достоверное цунами
    noaa_eq_id         INTEGER REFERENCES significant(noaa_id)
);
