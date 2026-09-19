"""
Shared plotting conventions: consistent style, explicit labels and units,
and a single place where every figure is written to visualizations/.

Colours assigned to AQI bands below are a display convention chosen for this
project so that the same band always looks the same across charts. They are
not official regulatory colour codes.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

try:
    from . import config as C
except ImportError:  # pragma: no cover
    import config as C

# Single source of truth is config.AQI_COLORS, so the figures and the Power BI
# colour scheme documented in dashboard/ can never drift apart.
AQI_COLORS = C.AQI_COLORS

PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
           "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]


def style() -> None:
    """Readable, presentation-safe defaults: no 3D, no clipped labels."""
    plt.rcParams.update({
        "figure.dpi": 100,
        "savefig.dpi": C.FIG_DPI,
        "savefig.bbox": "tight",
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "font.size": 10,
        "figure.autolayout": False,
    })


def unit(col: str) -> str:
    """Axis unit taken from config, so units are always stated."""
    return C.UNIT_LABELS.get(col, "value as supplied")


def path_for(name: str, subdir: str | None = None) -> Path:
    target = C.VIZ_DIR if subdir is None else C.VIZ_DIR / subdir
    target.mkdir(parents=True, exist_ok=True)
    return target / name


def savefig(fig_or_none, name: str, subdir: str | None = None,
            close: bool = True) -> Path:
    """Persist the current (or given) figure under visualizations/."""
    fig = plt.gcf() if fig_or_none is None else fig_or_none
    out = path_for(name, subdir)
    fig.savefig(out)
    if close:
        plt.close(fig)
    return out


def label_axes(ax, title: str, xlabel: str, ylabel: str, legend: bool = False):
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if legend:
        ax.legend(ncol=min(3, max(1, len(ax.get_lines()) or 1)))
    return ax


def trend_line(ax, x, y, color: str = "red", label: str | None = None, **kw):
    """Ordinary-least-squares trend line fitted with numpy.polyfit."""
    x = np.asarray(x, dtype="float64")
    y = np.asarray(y, dtype="float64")
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 3:
        return None
    slope, intercept = np.polyfit(x[mask], y[mask], 1)
    xs = x[mask]
    return ax.plot(xs, intercept + slope * xs, linestyle="--", lw=2, color=color,
                   label=label or f"linear trend (slope={slope:+.4f} / step)", **kw)
