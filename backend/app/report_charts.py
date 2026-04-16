"""Generate chart images (PNG bytes) for the Bodenbericht PDF.

Uses matplotlib with a dark/clean style matching the Bodenbericht brand.
Each function returns PNG bytes that can be embedded via pdf.image().
"""

import io
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np


# ── Brand colors ────────────────────────────────────────────────────
C_GREEN = "#22C55E"
C_YELLOW = "#EAB308"
C_ORANGE = "#F97316"
C_RED = "#EF4444"
C_NAVY = "#0F2040"
C_GRAY = "#E5E7EB"
C_BG = "#FAFAFA"


def _fig_to_png(fig, dpi: int = 150) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def geoscore_gauge(score: int | None, ampel: str = "gruen") -> bytes:
    """Half-circle gauge showing the GeoScore 0-100."""
    if score is None:
        score = 0

    fig, ax = plt.subplots(figsize=(4, 2.2), facecolor=C_BG)
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-0.3, 1.2)
    ax.set_aspect("equal")
    ax.axis("off")

    # Background arc (gray)
    theta = np.linspace(np.pi, 0, 100)
    ax.plot(np.cos(theta), np.sin(theta), color=C_GRAY, linewidth=18, solid_capstyle="round")

    # Score arc (colored)
    pct = min(max(score / 100, 0), 1)
    theta_score = np.linspace(np.pi, np.pi - pct * np.pi, 100)
    color = C_GREEN if score >= 70 else C_YELLOW if score >= 40 else C_RED
    ax.plot(np.cos(theta_score), np.sin(theta_score), color=color, linewidth=18, solid_capstyle="round")

    # Score text
    ax.text(0, 0.35, str(score), fontsize=36, fontweight="bold", ha="center", va="center", color=C_NAVY)
    ax.text(0, 0.05, "von 100", fontsize=10, ha="center", va="center", color="#999")
    ax.text(0, -0.2, "GeoScore", fontsize=11, fontweight="bold", ha="center", va="center", color=C_NAVY)

    return _fig_to_png(fig)


def metals_chart(metals: dict, thresholds: dict) -> bytes:
    """Horizontal bar chart: measured metal values vs. BBodSchV thresholds."""
    if not metals:
        return b""

    names = list(metals.keys())
    values = [metals[n] for n in names]
    thresh = [thresholds.get(n, 999) for n in names]

    fig, ax = plt.subplots(figsize=(5.5, 2.8), facecolor=C_BG)

    y = np.arange(len(names))
    colors = []
    for v, t in zip(values, thresh):
        if v < t:
            colors.append(C_GREEN)
        elif v < t * 1.5:
            colors.append(C_YELLOW)
        else:
            colors.append(C_RED)

    # Threshold markers
    ax.barh(y, thresh, height=0.5, color=C_GRAY, alpha=0.5, label="Vorsorgewert")
    # Measured values
    ax.barh(y, values, height=0.5, color=colors, alpha=0.9, label="Messwert")

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9, fontweight="bold")
    ax.set_xlabel("mg/kg", fontsize=8, color="#666")
    ax.legend(fontsize=7, loc="lower right", framealpha=0.8)
    ax.set_title("Schwermetalle vs. BBodSchV Vorsorgewerte", fontsize=10, fontweight="bold", color=C_NAVY, pad=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", labelsize=8)
    fig.tight_layout()

    return _fig_to_png(fig)


def soil_texture_pie(clay: float, sand: float, silt: float) -> bytes:
    """Pie chart showing soil texture composition."""
    fig, ax = plt.subplots(figsize=(2.8, 2.8), facecolor=C_BG)

    sizes = [clay, sand, silt]
    labels = [f"Ton\n{clay:.0f}%", f"Sand\n{sand:.0f}%", f"Schluff\n{silt:.0f}%"]
    colors_pie = ["#8B5E3C", "#E8D5B7", "#B8A88A"]

    wedges, texts = ax.pie(sizes, labels=labels, colors=colors_pie, startangle=90,
                           textprops={"fontsize": 8, "fontweight": "bold"})
    ax.set_title("Bodenart", fontsize=10, fontweight="bold", color=C_NAVY, pad=8)

    return _fig_to_png(fig)


def soil_quality_bars(soilgrids: dict) -> bytes:
    """Horizontal indicator bars for soil properties with reference ranges."""
    props = {
        "phh2o": {"label": "pH-Wert", "min": 3, "max": 9, "good_min": 5.5, "good_max": 7.5},
        "soc": {"label": "Org. Kohlenstoff", "min": 0, "max": 100, "good_min": 20, "good_max": 80},
        "bdod": {"label": "Lagerungsdichte", "min": 0.5, "max": 2.0, "good_min": 0.8, "good_max": 1.5},
    }

    active = {k: v for k, v in props.items() if soilgrids.get(k) is not None}
    if not active:
        return b""

    fig, axes = plt.subplots(len(active), 1, figsize=(5.5, len(active) * 0.9 + 0.5), facecolor=C_BG)
    if len(active) == 1:
        axes = [axes]

    for ax, (key, meta) in zip(axes, active.items()):
        val = soilgrids[key]
        vmin, vmax = meta["min"], meta["max"]
        gmin, gmax = meta["good_min"], meta["good_max"]

        # Background
        ax.barh(0, vmax - vmin, left=vmin, height=0.6, color=C_GRAY, alpha=0.3)
        # Good range
        ax.barh(0, gmax - gmin, left=gmin, height=0.6, color=C_GREEN, alpha=0.2)
        # Value marker
        color = C_GREEN if gmin <= val <= gmax else C_YELLOW if abs(val - (gmin + gmax) / 2) < (gmax - gmin) else C_RED
        ax.plot(val, 0, "o", color=color, markersize=12, markeredgecolor="white", markeredgewidth=2, zorder=5)
        ax.text(val, 0.45, f"{val:.1f}", fontsize=8, ha="center", fontweight="bold", color=C_NAVY)

        ax.set_xlim(vmin, vmax)
        ax.set_ylim(-0.5, 0.7)
        ax.set_yticks([])
        ax.set_ylabel(meta["label"], fontsize=8, fontweight="bold", rotation=0, labelpad=80, va="center")
        ax.tick_params(axis="x", labelsize=7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)

    fig.suptitle("Bodenqualitaet", fontsize=10, fontweight="bold", color=C_NAVY, y=1.02)
    fig.tight_layout()
    return _fig_to_png(fig)
