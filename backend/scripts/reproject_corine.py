"""Reproject + clip CORINE 2018 from EPSG:3035 (LAEA Europe) to EPSG:4326,
DE+NL bbox. Writes pixel-indexed raster (1-44); the CLC code mapping lives
in soil_data.py.

Source : ESRI raster from CLC2018 v2020_20u1, 100 m, codes 1-44 + NoData -128
Target : EPSG:4326, bbox 3.3..15.1 E / 47.2..55.2 N, ~0.001° step (≈100 m)
Resampling: nearest (categorical raster — never bilinear)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject

SRC = Path(
    r"F:/jarvis-eye-data/geoforensic-rasters/corine_extract/"
    r"u2018_clc2018_v2020_20u1_raster100m/DATA/U2018_CLC2018_V2020_20u1.tif"
)
DST = Path(r"F:/jarvis-eye-data/geoforensic-rasters/corine_2018_clc_100m_de_nl.tif")

DST_BBOX = (3.3, 47.2, 15.1, 55.2)  # lon_min, lat_min, lon_max, lat_max
PIXEL_DEG = 0.001  # ≈ 100 m at 51°N


def main() -> int:
    if not SRC.exists():
        print(f"Source missing: {SRC}", file=sys.stderr)
        return 1

    width = int(round((DST_BBOX[2] - DST_BBOX[0]) / PIXEL_DEG))
    height = int(round((DST_BBOX[3] - DST_BBOX[1]) / PIXEL_DEG))
    dst_transform = from_bounds(*DST_BBOX, width, height)

    with rasterio.open(SRC) as src:
        dst_profile = src.profile.copy()
        dst_profile.update(
            crs="EPSG:4326",
            transform=dst_transform,
            width=width,
            height=height,
            compress="deflate",
            predictor=2,
            tiled=True,
            blockxsize=512,
            blockysize=512,
        )
        dst_arr = np.full((height, width), src.nodata or -128, dtype=src.dtypes[0])
        reproject(
            source=rasterio.band(src, 1),
            destination=dst_arr,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs="EPSG:4326",
            resampling=Resampling.nearest,
        )

        valid = dst_arr[dst_arr != (src.nodata or -128)]
        print(
            f"Reprojected {width}×{height} px to {DST.name}. "
            f"Valid pixels: {valid.size:,} ({100*valid.size/dst_arr.size:.1f}%). "
            f"Unique indices: {sorted(np.unique(valid).tolist())[:15]}..."
        )

        with rasterio.open(DST, "w", **dst_profile) as dst:
            dst.write(dst_arr, 1)

    print(f"Wrote {DST} ({DST.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
