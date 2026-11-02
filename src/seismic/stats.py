"""Статистическая сейсмология на NumPy.

Реализовано:
- магнитуда полноты каталога Mc (метод максимальной кривизны);
- b-value закона Гутенберга–Рихтера (оценка максимального правдоподобия Аки–Уцу);
- бутстрэп-доверительные интервалы;
- пуассоновская вероятность сильного события за T лет;
- окна Гарднера–Кнопова для отбора афтершоков;
- подгонка модифицированного закона Омори–Уцу методом максимального правдоподобия;
- доверительный интервал Уилсона для долей.
"""

import numpy as np

EARTH_RADIUS_KM = 6371.0


# --- Закон Гутенберга–Рихтера ---------------------------------------------

def magnitude_of_completeness(mags: np.ndarray, bin_width: float = 0.1,
                              correction: float = 0.2) -> float:
    """Mc методом максимальной кривизны (Wiemer & Wyss, 2000).

    Mc — бин с наибольшим числом событий; поправка +0.2 компенсирует
    известную склонность метода занижать Mc.
    """
    mags = np.asarray(mags, dtype=float)
    binned = np.round(mags / bin_width) * bin_width
    values, counts = np.unique(np.round(binned, 1), return_counts=True)
    return float(values[np.argmax(counts)] + correction)


def b_value_mle(mags: np.ndarray, mc: float, bin_width: float = 0.1) -> float:
    """b-value по Аки (1965) с поправкой Уцу на дискретность магнитуд.

    b = log10(e) / (mean(M) - (Mc - ΔM/2)),  M ≥ Mc
    """
    m = np.asarray(mags, dtype=float)
    m = m[m >= mc - 1e-9]
    return float(np.log10(np.e) / (m.mean() - (mc - bin_width / 2)))


def b_value_shi_bolt_error(mags: np.ndarray, mc: float, b: float) -> float:
    """Стандартная ошибка b-value по Shi & Bolt (1982)."""
    m = np.asarray(mags, dtype=float)
    m = m[m >= mc - 1e-9]
    n = m.size
    return float(2.3 * b ** 2 * np.sqrt(((m - m.mean()) ** 2).sum() / (n * (n - 1))))


def a_value(mags: np.ndarray, mc: float, b: float, years: float) -> float:
    """a-value в годовой нормировке: log10 N(≥Mc)/год = a - b·Mc."""
    n = np.count_nonzero(np.asarray(mags) >= mc - 1e-9)
    return float(np.log10(n / years) + b * mc)


def frequency_magnitude(mags: np.ndarray, bin_width: float = 0.1):
    """Некумулятивное и кумулятивное распределение «магнитуда–частота».

    Возвращает (центры бинов, число в бине, число событий с M ≥ бина).
    """
    mags = np.asarray(mags, dtype=float)
    edges = np.arange(np.floor(mags.min() * 10) / 10,
                      mags.max() + 2 * bin_width, bin_width) - bin_width / 2
    counts, edges = np.histogram(mags, bins=edges)
    centers = np.round(edges[:-1] + bin_width / 2, 2)
    cumulative = counts[::-1].cumsum()[::-1]
    return centers, counts, cumulative


def bootstrap(values: np.ndarray, statistic, n_boot: int = 2000,
              ci: float = 0.95, seed: int = 42):
    """Перцентильный бутстрэп: (оценка, нижняя граница, верхняя граница)."""
    rng = np.random.default_rng(seed)
    values = np.asarray(values)
    idx = rng.integers(0, values.size, size=(n_boot, values.size))
    samples = np.array([statistic(values[row]) for row in idx])
    alpha = (1 - ci) / 2
    lo, hi = np.quantile(samples, [alpha, 1 - alpha])
    return float(statistic(values)), float(lo), float(hi)


# --- Повторяемость --------------------------------------------------------

def poisson_exceedance(rate_per_year: np.ndarray | float, years: float) -> np.ndarray:
    """Вероятность хотя бы одного события за T лет: 1 - exp(-λT)."""
    return 1.0 - np.exp(-np.asarray(rate_per_year, dtype=float) * years)


def gr_return_period(a: float, b: float, magnitude: float) -> float:
    """Средний период повторяемости (лет) события с M ≥ magnitude по закону Г–Р."""
    return float(10 ** (b * magnitude - a))


def coefficient_of_variation(inter_event_times: np.ndarray) -> float:
    """CV межсобытийных интервалов: ≈1 у процесса Пуассона, >1 при кластеризации."""
    t = np.asarray(inter_event_times, dtype=float)
    return float(t.std(ddof=1) / t.mean())


# --- Геометрия ------------------------------------------------------------

def haversine_km(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Расстояние по дуге большого круга, векторизовано."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    h = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(h))


# --- Афтершоки ------------------------------------------------------------

def gardner_knopoff_window(magnitude: float) -> tuple[float, float]:
    """Пространственно-временное окно афтершоков (Gardner & Knopoff, 1974).

    Возвращает (радиус, км; длительность, сут.). Коэффициенты — аппроксимация
    из van Stiphout et al. (2012), CORSSA.
    """
    distance = 10 ** (0.1238 * magnitude + 0.983)
    if magnitude >= 6.5:
        duration = 10 ** (0.032 * magnitude + 2.7389)
    else:
        duration = 10 ** (0.5409 * magnitude - 0.547)
    return float(distance), float(duration)


def rupture_length_km(magnitude: float) -> float:
    """Длина разрыва по регрессии Wells & Coppersmith (1994): log10 L = -2.44 + 0.59·M.

    Для великих землетрясений (M≥8.5) окно Гарднера–Кнопова (~130 км) много
    меньше длины разрыва (у Суматры-2004 — около 1300 км), поэтому радиус
    поиска афтершоков берётся как максимум из двух оценок.
    """
    return float(10 ** (-2.44 + 0.59 * magnitude))


def _omori_integral(c: np.ndarray, p: np.ndarray, t_start: float, t_end: float) -> np.ndarray:
    """∫ (t+c)^-p dt на [t_start, t_end] для сетки (c, p); при p≈1 — логарифм."""
    near_one = np.isclose(p, 1.0)
    p_safe = np.where(near_one, 1.0 + 1e-9, p)
    general = ((t_end + c) ** (1 - p_safe) - (t_start + c) ** (1 - p_safe)) / (1 - p_safe)
    log_case = np.log((t_end + c) / (t_start + c))
    return np.where(near_one, log_case, general)


def fit_omori(times_days: np.ndarray, t_start: float = 0.0, t_end: float | None = None,
              c_grid: np.ndarray | None = None, p_grid: np.ndarray | None = None) -> dict:
    """ММП-оценка закона Омори–Уцу  n(t) = K / (t + c)^p  (Ogata, 1983).

    Логарифм правдоподобия неоднородного пуассоновского процесса:
        lnL = N·lnK - p·Σ ln(t_i + c) - K·∫ (t+c)^-p dt
    При фиксированных (c, p) оптимальное K = N / ∫, поэтому достаточно
    перебора по двумерной сетке — он целиком векторизован через broadcasting.
    """
    t = np.asarray(times_days, dtype=float)
    upper = np.inf if t_end is None else t_end
    t = t[(t >= t_start) & (t <= upper)]
    t_end = float(t.max()) if t_end is None else t_end
    n = t.size

    c_grid = np.logspace(-3, 0.5, 120) if c_grid is None else c_grid
    p_grid = np.linspace(0.5, 2.5, 201) if p_grid is None else p_grid
    C, P = np.meshgrid(c_grid, p_grid, indexing="ij")          # (nc, np)

    # Σ ln(t_i + c) для каждого c: (nc,) → broadcast на ось p
    sum_log = np.log(t[None, :] + c_grid[:, None]).sum(axis=1)[:, None]
    integral = _omori_integral(C, P, t_start, t_end)
    K = n / integral
    loglik = n * np.log(K) - P * sum_log - n

    i, j = np.unravel_index(np.argmax(loglik), loglik.shape)
    return {
        "K": float(K[i, j]), "c": float(c_grid[i]), "p": float(p_grid[j]),
        "n": int(n), "loglik": float(loglik[i, j]),
        "t_start": t_start, "t_end": t_end,
    }


def omori_rate(t: np.ndarray, K: float, c: float, p: float) -> np.ndarray:
    return K / (np.asarray(t, dtype=float) + c) ** p


# --- Доли -----------------------------------------------------------------

def wilson_interval(successes, totals, z: float = 1.96):
    """95% доверительный интервал Уилсона для доли (корректен при малых n)."""
    k = np.asarray(successes, dtype=float)
    n = np.asarray(totals, dtype=float)
    p = np.divide(k, n, out=np.zeros_like(k), where=n > 0)
    denom = 1 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return p, center - half, center + half
