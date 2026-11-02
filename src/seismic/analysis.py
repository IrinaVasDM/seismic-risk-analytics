"""Аналитические сценарии поверх базы: связывают pandas, SQL и stats."""

import numpy as np
import pandas as pd

from seismic import db, stats

# Крупные события для анализа афтершоков: (подпись, идентификатор USGS)
MAINSHOCKS = {
    "Суматра, 2004 (M9.1)": "official20041226005853450_30",
    "Чили, 2010 (M8.8)": "official20100227063411530_30",
    "Тохоку, 2011 (M9.1)": "official20110311054624120_30",
    "Непал, 2015 (M7.8)": "us20002926",
    "Турция, 2023 (M7.8)": "us6000jllz",
    "Камчатка, 2025 (M8.8)": "us6000qw60",
}


def load_events(min_mag: float = 4.5) -> pd.DataFrame:
    df = db.query("SELECT * FROM events WHERE mag >= :m", {"m": min_mag})
    df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True)
    return df


def gutenberg_richter_by_zone(events: pd.DataFrame, mc_floor: float = 5.0, min_events: int = 300,
                              n_boot: int = 1000) -> pd.DataFrame:
    """b-value, a-value и периоды повторяемости для каждой зоны.

    Mc оценивается отдельно для каждой зоны (полнота зависит от плотности
    станций), но не ниже mc_floor — порога полноты каталога в 1973–1994 гг.
    """
    years = events["year"].max() - events["year"].min() + 1
    zones = db.query("SELECT zone_id, name FROM zones").set_index("zone_id")["name"]
    rows = []
    for zone_id, grp in events.groupby("zone_id"):
        mags = grp["mag"].to_numpy()
        mc = max(stats.magnitude_of_completeness(mags), mc_floor)
        above = mags[mags >= mc - 1e-9]
        if above.size < min_events:
            continue
        b, lo, hi = stats.bootstrap(above, lambda m: stats.b_value_mle(m, mc), n_boot=n_boot)
        a = stats.a_value(mags, mc, b, years)
        rate_m7_observed = np.count_nonzero(mags >= 7.0) / years
        rows.append({
            "zone_id": zone_id, "zone": zones[zone_id], "n": above.size, "mc": mc,
            "b": b, "b_lo": lo, "b_hi": hi, "a": a,
            "return_m7_gr": stats.gr_return_period(a, b, 7.0),
            "return_m8_gr": stats.gr_return_period(a, b, 8.0),
            "m7_per_year_obs": rate_m7_observed,
            "p_m7_10y": float(stats.poisson_exceedance(10 ** (a - b * 7.0), 10)),
        })
    return pd.DataFrame(rows).sort_values("b").reset_index(drop=True)


def aftershock_sequence(events: pd.DataFrame, mainshock_id: str, days: float = 365,
                        min_mag: float = 5.0) -> tuple[pd.Series, pd.DataFrame]:
    """Афтершоки главного толчка в пространственно-временном окне.

    Радиус — максимум из окна Гарднера–Кнопова и длины разрыва по
    Wells & Coppersmith; порог min_mag выше глобального Mc, потому что
    в первые дни после сильного толчка слабые события теряются в коде волн.
    Возвращает (главный толчок, афтершоки с колонками t_days и dist_km).
    """
    main = events.loc[events["event_id"].eq(mainshock_id)].iloc[0]
    radius_km = max(stats.gardner_knopoff_window(main["mag"])[0], stats.rupture_length_km(main["mag"]))

    t_days = (events["time_utc"] - main["time_utc"]).dt.total_seconds() / 86_400
    candidates = events.loc[(t_days > 0) & (t_days <= days) & (events["mag"] >= min_mag)].copy()
    candidates["t_days"] = t_days[candidates.index]
    candidates["dist_km"] = stats.haversine_km(main["latitude"], main["longitude"],
                                               candidates["latitude"], candidates["longitude"])
    after = candidates.loc[candidates["dist_km"] <= radius_km].reset_index(drop=True)
    after.attrs["radius_km"] = radius_km
    return main, after


def omori_table(events: pd.DataFrame, days: float = 365, t_start: float = 0.05,
                n_boot: int = 200, seed: int = 7) -> tuple[pd.DataFrame, dict]:
    """Подгонка закона Омори–Уцу для всех главных толчков из MAINSHOCKS.

    t_start отсекает первые ~1.2 часа, когда каталог заведомо неполон.
    Для недавних событий окно обрезается концом каталога. Неопределённость
    p оценивается бутстрэпом по временам афтершоков.
    """
    rng = np.random.default_rng(seed)
    catalog_end = events["time_utc"].max()
    rows, sequences = [], {}
    for label, event_id in MAINSHOCKS.items():
        if not events["event_id"].eq(event_id).any():
            continue
        main, after = aftershock_sequence(events, event_id, days=days)
        t_end = min(days, (catalog_end - main["time_utc"]).total_seconds() / 86_400)
        after = after.loc[after["t_days"] <= t_end]
        t = after["t_days"].to_numpy()
        fit = stats.fit_omori(t, t_start=t_start, t_end=t_end)
        boot_p = [stats.fit_omori(rng.choice(t, t.size), t_start=t_start, t_end=t_end)["p"]
                  for _ in range(n_boot)]
        p_lo, p_hi = np.quantile(boot_p, [0.025, 0.975])
        rows.append({
            "event": label, "mag": main["mag"], "radius_km": after.attrs["radius_km"],
            "days": t_end, "n_aftershocks": len(after), "max_aftershock": after["mag"].max(),
            "bath_delta": main["mag"] - after["mag"].max(),
            "K": fit["K"], "c_days": fit["c"], "p": fit["p"], "p_lo": p_lo, "p_hi": p_hi,
        })
        sequences[label] = (main, after, fit)
    return pd.DataFrame(rows), sequences
