"""Единый стиль и функции построения графиков (matplotlib)."""

import json

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap

from seismic import config

# Палитра: категориальные цвета в фиксированном порядке, проверены на различимость
# при нарушениях цветового зрения; последовательная шкала — один тон (синий)
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_MUTED = "#52514e"
GRID = "#e4e3df"
LAND = "#ecebe7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
HIGHLIGHT = "#e34948"
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SEQUENTIAL = LinearSegmentedColormap.from_list("seq_blue", BLUE_RAMP)


def setup_style() -> None:
    mpl.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "figure.dpi": 110,
        "savefig.dpi": 160,
        "savefig.bbox": "tight",
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "text.color": TEXT,
        "axes.labelcolor": TEXT_MUTED,
        "axes.edgecolor": GRID,
        "axes.linewidth": 0.8,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 22,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "axes.prop_cycle": mpl.cycler(color=SERIES),
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.grid.axis": "y",
        "xtick.color": TEXT_MUTED,
        "ytick.color": TEXT_MUTED,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "legend.frameon": False,
        "lines.linewidth": 2,
    })


def save(fig: plt.Figure, name: str) -> None:
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(config.FIGURES_DIR / f"{name}.png")


def subtitle(ax: plt.Axes, text: str) -> None:
    """Пояснение под заголовком — мелким приглушённым шрифтом."""
    ax.text(0, 1.01, text, transform=ax.transAxes, fontsize=9, color=TEXT_MUTED, va="bottom")


def source_note(fig: plt.Figure, text: str = "Источник: USGS Earthquake Catalog, NOAA NCEI",
                y: float = -0.02) -> None:
    fig.text(0.01, y, text, fontsize=8, color=TEXT_MUTED, ha="left", va="top")


# Названия стран для подписей на графиках (в NOAA они на английском)
COUNTRY_RU = {
    "China": "Китай", "Indonesia": "Индонезия", "Haiti": "Гаити", "Japan": "Япония",
    "Turkey": "Турция", "Turkmenistan": "Туркменистан", "Italy": "Италия", "Pakistan": "Пакистан",
    "Peru": "Перу", "Iran": "Иран", "Chile": "Чили", "Nepal": "Непал", "India": "Индия",
    "Armenia": "Армения", "Guatemala": "Гватемала", "Sri Lanka": "Шри-Ланка",
}


# --- Карта -----------------------------------------------------------------

def _land_polygons() -> list[np.ndarray]:
    geo = json.loads((config.GEO_DIR / "ne_110m_land.geojson").read_text())
    polys = []
    for feature in geo["features"]:
        geom = feature["geometry"]
        rings = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        polys.extend(np.asarray(poly[0]) for poly in rings)
    return polys


def world_axes(ax: plt.Axes) -> plt.Axes:
    """Подложка-карта в равнопромежуточной проекции без внешних зависимостей."""
    ax.add_collection(PolyCollection(_land_polygons(), facecolor=LAND, edgecolor="none", zorder=0))
    ax.set_xlim(-180, 180)
    ax.set_ylim(-75, 85)
    ax.set_aspect("equal")
    ax.set_xticks(np.arange(-180, 181, 60))
    ax.set_yticks(np.arange(-60, 81, 30))
    ax.xaxis.set_major_formatter(lambda v, _: f"{abs(v):.0f}°{'в.д.' if v > 0 else 'з.д.' if v < 0 else ''}")
    ax.yaxis.set_major_formatter(lambda v, _: f"{abs(v):.0f}°{'с.ш.' if v > 0 else 'ю.ш.' if v < 0 else ''}")
    ax.grid(True, linewidth=0.4)
    for spine in ax.spines.values():
        spine.set_visible(False)
    return ax


def magnitude_size(mag: np.ndarray, base: float = 4.5) -> np.ndarray:
    """Площадь маркера ∝ высвобожденной энергии в сжатой шкале (≈10^(0.75ΔM))."""
    return 1.2 * 10 ** (0.75 * (np.asarray(mag) - base))
