"""Проверка оценщиков на синтетических данных с известными параметрами."""

import numpy as np
import pytest

from seismic import regions, stats


def synthetic_gr(b: float, mc: float, n: int, seed: int = 0) -> np.ndarray:
    """Магнитуды по закону Г–Р: M - Mc ~ Exp(β = b·ln10), округление до 0.1."""
    rng = np.random.default_rng(seed)
    continuous = (mc - 0.05) + rng.exponential(1 / (b * np.log(10)), n)
    return np.round(continuous, 1)


def synthetic_omori(K: float, c: float, p: float, t_end: float, seed: int = 0) -> np.ndarray:
    """Времена афтершоков методом обратной функции распределения."""
    rng = np.random.default_rng(seed)
    total = K * ((t_end + c) ** (1 - p) - c ** (1 - p)) / (1 - p)
    n = rng.poisson(total)
    u = rng.uniform(size=n)
    base = c ** (1 - p) + u * ((t_end + c) ** (1 - p) - c ** (1 - p))
    return np.sort(base ** (1 / (1 - p)) - c)


@pytest.mark.parametrize("true_b", [0.8, 1.0, 1.2])
def test_b_value_recovers_truth(true_b):
    mags = synthetic_gr(true_b, mc=5.0, n=20_000)
    assert stats.b_value_mle(mags, mc=5.0) == pytest.approx(true_b, abs=0.03)


def test_completeness_detects_rolloff():
    rng = np.random.default_rng(1)
    complete = synthetic_gr(1.0, mc=5.0, n=10_000)
    # ниже Mc сеть «теряет» часть событий
    partial = synthetic_gr(1.0, mc=4.0, n=40_000)
    partial = partial[(partial < 5.0) & (rng.uniform(size=partial.size) < (partial - 3.9) / 1.4)]
    mc = stats.magnitude_of_completeness(np.concatenate([complete, partial]), correction=0.0)
    assert 4.6 <= mc <= 5.1


def test_omori_fit_recovers_p():
    t = synthetic_omori(K=200, c=0.05, p=1.1, t_end=365)
    fit = stats.fit_omori(t, t_end=365)
    assert fit["p"] == pytest.approx(1.1, abs=0.08)


def test_poisson_exceedance_bounds():
    p = stats.poisson_exceedance(np.array([0.0, 0.1, 10.0]), years=10)
    assert p[0] == 0 and 0.6 < p[1] < 0.65 and p[2] == pytest.approx(1.0)


def test_haversine_quarter_meridian():
    assert stats.haversine_km(0, 0, 90, 0) == pytest.approx(np.pi * 6371 / 2, rel=1e-6)


def test_wilson_contains_point_estimate():
    p, lo, hi = stats.wilson_interval(np.array([3, 50]), np.array([10, 100]))
    assert np.all(lo <= p) and np.all(p <= hi)


def test_assign_zone_examples():
    # Токио, Сантьяго, Тонга, середина Атлантики
    zones = regions.assign_zone(np.array([35.7, -33.4, -21.1, 0.0]), np.array([139.7, -70.6, -175.2, -30.0]))
    assert zones.tolist() == [1, 8, 7, 99]
