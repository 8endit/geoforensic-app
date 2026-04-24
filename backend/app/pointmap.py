"""Raster pointmap for the teaser PDF — OSM basemap + coloured EGMS points.

Replaces the bare SVG scatter with a proper cartographic map: OSM tiles
underneath, a dashed circle marking the 500 m screening radius, dots
coloured by Ampel classification, and an address marker in the centre.

Returns a base64 PNG data URI so it embeds directly in the HTML that
becomes the PDF. Empty string on any failure (network, contextily
missing, tile service error) — the HTML template keeps a fallback path
that renders the older SVG scatter, so a bad tile fetch never breaks
PDF generation.

Paywall stays intact: no numeric mm/a values are written to the map,
only colour classes.
"""
from __future__ import annotations

import base64
import io
import logging
import math

logger = logging.getLogger(__name__)

_GREEN = "#5B9A6F"
_YELLOW = "#C4A94D"
_RED = "#B85450"
_ADDRESS = "#1E3352"


def render_address_pin(
    center_lat: float,
    center_lon: float,
    half_extent_m: float = 180.0,
    width_in: float = 4.3,
    height_in: float = 2.7,
    dpi: int = 160,
) -> str:
    """Render a small OSM basemap with a centered address pin.

    Drop-in replacement for the flaky staticmap.openstreetmap.de call in
    ``app.static_map.fetch_static_map``. Same CartoDB Positron tile source
    the pointmap uses, so both maps share one provider. Empty string on
    any failure (network, tile error, missing deps) — the report template
    renders a grey coord-fallback in that case.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import contextily as cx
        import pyproj
    except ImportError as exc:
        logger.warning("address pin deps missing: %s", exc)
        return ""

    try:
        transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        cx_m, cy_m = transformer.transform(center_lon, center_lat)

        xmin, xmax = cx_m - half_extent_m, cx_m + half_extent_m
        ymin, ymax = cy_m - half_extent_m, cy_m + half_extent_m

        fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_aspect("equal")
        ax.set_axis_off()

        try:
            cx.add_basemap(
                ax,
                source=cx.providers.CartoDB.Positron,
                crs="EPSG:3857",
                reset_extent=False,
                zoom=17,
                attribution_size=5,
            )
        except Exception as exc:
            logger.warning("address pin basemap fetch failed: %s: %s", type(exc).__name__, exc)
            return ""

        # Two-layer pin: red outer ring + white centre dot
        ax.scatter([cx_m], [cy_m], s=340, c="#B85450", marker="o",
                   edgecolors="white", linewidths=2.5, zorder=10)
        ax.scatter([cx_m], [cy_m], s=70, c="white", marker="o",
                   edgecolors="#B85450", linewidths=1.0, zorder=11)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                    pad_inches=0.02, facecolor="white")
        plt.close(fig)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception as exc:
        logger.warning("address pin render failed: %s: %s", type(exc).__name__, exc)
        return ""


def render_pointmap(
    center_lat: float,
    center_lon: float,
    radius_m: int,
    points: list,
    threshold_mm_yr: float,
    width_in: float = 6.4,
    height_in: float = 4.4,
    dpi: int = 150,
) -> str:
    if not points:
        return ""

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Circle
        from matplotlib.patheffects import withStroke
        import contextily as cx
        import pyproj
    except ImportError as exc:
        logger.warning("pointmap deps missing: %s — falling back to SVG scatter", exc)
        return ""

    try:
        transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        cx_m, cy_m = transformer.transform(center_lon, center_lat)

        half_extent = radius_m * 1.25
        xmin, xmax = cx_m - half_extent, cx_m + half_extent
        ymin, ymax = cy_m - half_extent, cy_m + half_extent

        fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=dpi)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_aspect("equal")
        ax.set_axis_off()

        try:
            cx.add_basemap(
                ax,
                source=cx.providers.CartoDB.Positron,
                crs="EPSG:3857",
                reset_extent=False,
                zoom=16,
                attribution_size=6,
            )
        except Exception as exc:
            logger.warning("basemap tile fetch failed: %s: %s", type(exc).__name__, exc)
            return ""

        ax.add_patch(
            Circle(
                (cx_m, cy_m), radius_m,
                fill=False, edgecolor=_ADDRESS, linewidth=1.4,
                linestyle=(0, (6, 4)), alpha=0.75, zorder=3,
            )
        )

        counts = {"gruen": 0, "gelb": 0, "rot": 0}
        xs_g, ys_g, ss_g = [], [], []
        xs_y, ys_y, ss_y = [], [], []
        xs_r, ys_r, ss_r = [], [], []
        for p in points:
            try:
                p_lat = float(p["lat"])
                p_lon = float(p["lon"])
                v_abs = abs(float(p["mean_velocity_mm_yr"]))
            except (KeyError, TypeError, ValueError):
                continue
            px, py = transformer.transform(p_lon, p_lat)
            # Scale dot size by velocity magnitude — clamped so a single
            # outlier does not dominate the map visually.
            size = 22 + min(v_abs, 8.0) * 7.0
            if v_abs < threshold_mm_yr:
                xs_g.append(px); ys_g.append(py); ss_g.append(size); counts["gruen"] += 1
            elif v_abs <= 5.0:
                xs_y.append(px); ys_y.append(py); ss_y.append(size); counts["gelb"] += 1
            else:
                xs_r.append(px); ys_r.append(py); ss_r.append(size); counts["rot"] += 1

        for xs, ys, ss, color in (
            (xs_g, ys_g, ss_g, _GREEN),
            (xs_y, ys_y, ss_y, _YELLOW),
            (xs_r, ys_r, ss_r, _RED),
        ):
            if xs:
                ax.scatter(xs, ys, s=ss, c=color, alpha=0.88,
                           edgecolors="white", linewidths=0.9, zorder=5)

        ax.scatter([cx_m], [cy_m], s=240, c=_ADDRESS, marker="o",
                   edgecolors="white", linewidths=2.2, zorder=10)
        ax.annotate(
            "Adresse", (cx_m, cy_m), xytext=(0, 12), textcoords="offset points",
            ha="center", fontsize=9, fontweight="bold", color=_ADDRESS,
            path_effects=[withStroke(linewidth=3, foreground="white")],
            zorder=11,
        )

        legend_items = [
            (_GREEN, f"< {threshold_mm_yr:g} mm/a", counts["gruen"]),
            (_YELLOW, f"{threshold_mm_yr:g}–5 mm/a", counts["gelb"]),
            (_RED, "> 5 mm/a", counts["rot"]),
        ]
        legend_handles = [
            plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=col,
                       markeredgecolor="white", markersize=9,
                       label=f"{lbl}  ({n})")
            for col, lbl, n in legend_items
        ]
        leg = ax.legend(
            handles=legend_handles, loc="upper right",
            frameon=True, framealpha=0.92, edgecolor="#cbd5e1",
            fontsize=8, borderpad=0.6, handlelength=1.2,
        )
        leg.set_zorder(20)

        # Scale bar: 100 m for a 500 m radius map
        scale_m = 100 if radius_m >= 300 else 50
        sb_y = ymin + (ymax - ymin) * 0.06
        sb_x0 = xmin + (xmax - xmin) * 0.06
        sb_x1 = sb_x0 + scale_m
        ax.plot([sb_x0, sb_x1], [sb_y, sb_y], color="#1e293b", linewidth=2, zorder=15)
        ax.plot([sb_x0, sb_x0], [sb_y - 4, sb_y + 4], color="#1e293b", linewidth=2, zorder=15)
        ax.plot([sb_x1, sb_x1], [sb_y - 4, sb_y + 4], color="#1e293b", linewidth=2, zorder=15)
        ax.text(
            (sb_x0 + sb_x1) / 2, sb_y + 6, f"{scale_m} m",
            ha="center", va="bottom", fontsize=8, color="#1e293b", zorder=15,
            path_effects=[withStroke(linewidth=3, foreground="white")],
        )

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                    pad_inches=0.1, facecolor="white")
        plt.close(fig)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception as exc:
        logger.warning("pointmap render failed: %s: %s", type(exc).__name__, exc)
        return ""
