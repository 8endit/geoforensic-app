"""Download DWD KOSTRA-DWD-2020 starkregen rasters and convert to GeoTIFF.

Source:    https://opendata.dwd.de/climate_environment/CDC/grids_germany/return_periods/precipitation/KOSTRA/KOSTRA_DWD_2020/
License:   GeoNutzV (commercial use OK with source attribution)
DOI:       10.5676/DWD/KOSTRA-DWD-2020
Attribution: "Deutscher Wetterdienst, KOSTRA-DWD-2020"

KOSTRA-DWD-2020 ships per duration/return-period combination as ASCII
GRID rasters (``.asc`` + ``.prj``) on the DWD CDC OpenData server.
This script:

1. lists what is available on the server (--list)
2. downloads a configurable subset (--download)
3. converts each ``.asc`` to GeoTIFF in-place (--convert)
4. drops the result into RASTER_DIR so the existing raster-loader
   pattern in ``app/soil_data.py`` can consume it later

The actual lookup module (``kostra_data.py``) is intentionally NOT
written yet — first establish the data flow, then wire to the report
once the file naming / grid CRS is verified against a real download.

Usage from inside the backend container::

    python -m scripts.download_kostra --list
    python -m scripts.download_kostra --download --tag D60_T100
    python -m scripts.download_kostra --convert

Or in one shot::

    python -m scripts.download_kostra --download --convert --tag D60_T100

Common --tag values (Dauerstufe Dxx, Wiederkehrintervall Tyy):
    D5, D10, D15, D20, D30, D45, D60, D90, D120, D180, D240, D360,
    D540, D720, D1080, D1440, D2880, D4320  (minutes)
    T1, T2, T3, T5, T10, T20, T30, T50, T100  (years)

If --tag matches none of the listed files (e.g. naming differs from
expectation), --list shows what's actually there. Naming convention
must be confirmed against the live server before locking in.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

KOSTRA_BASE_URL = (
    "https://opendata.dwd.de/climate_environment/CDC/grids_germany/"
    "return_periods/precipitation/KOSTRA/KOSTRA_DWD_2020/"
)
USER_AGENT = "Bodenbericht/1.0 (kontakt@geoforensic.de)"
DEFAULT_RASTER_DIR = os.getenv("RASTER_DIR", "/app/rasters")
KOSTRA_SUBDIR = "kostra_dwd_2020"


class _LinkExtractor(HTMLParser):
    """Pull href values out of the apache-style directory index page."""

    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.hrefs.append(value)


def _http_get(url: str, *, timeout: float = 30.0) -> bytes:
    import httpx  # local import — script may run outside the API runtime
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        return resp.content


def list_remote_files(url: str) -> list[str]:
    """Return the list of file names under the given index URL.

    Walks one level deep; if entries are sub-directories the names will
    end in ``/`` and the caller can recurse.
    """
    html = _http_get(url).decode("utf-8", errors="replace")
    parser = _LinkExtractor()
    parser.feed(html)
    out: list[str] = []
    for href in parser.hrefs:
        if href.startswith("?") or href.startswith("/") or href.startswith(".."):
            continue
        out.append(href)
    return out


def download_files(
    urls: list[str], target_dir: Path, *, skip_if_exists: bool = True
) -> list[Path]:
    """Download each URL into ``target_dir``. Returns paths written."""
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for url in urls:
        name = url.rsplit("/", 1)[-1]
        out_path = target_dir / name
        if skip_if_exists and out_path.exists() and out_path.stat().st_size > 0:
            logger.info("skip (exists): %s", out_path)
            written.append(out_path)
            continue
        logger.info("download %s -> %s", url, out_path)
        content = _http_get(url, timeout=120.0)
        out_path.write_bytes(content)
        written.append(out_path)
    return written


def convert_asc_to_tif(asc_dir: Path) -> list[Path]:
    """Convert each .asc + .prj pair in ``asc_dir`` to a GeoTIFF in-place.

    Uses rasterio (already a backend dependency). The .asc file alone
    is enough — the AAIGrid driver reads it directly. We carry over
    the CRS from the .prj if present, otherwise we leave it unset and
    log a warning so the operator notices.
    """
    import rasterio  # local import — heavy

    written: list[Path] = []
    for asc in sorted(asc_dir.glob("*.asc")):
        tif = asc.with_suffix(".tif")
        if tif.exists() and tif.stat().st_size > 0:
            logger.info("skip (exists): %s", tif)
            written.append(tif)
            continue
        logger.info("convert %s -> %s", asc, tif)
        try:
            with rasterio.open(asc) as src:
                profile = src.profile.copy()
                profile.update(driver="GTiff", compress="deflate", tiled=True)
                if not src.crs:
                    logger.warning("no CRS detected for %s — output GeoTIFF will be unreferenced", asc)
                with rasterio.open(tif, "w", **profile) as dst:
                    dst.write(src.read())
            written.append(tif)
        except Exception:
            logger.exception("conversion failed for %s — leaving .asc in place", asc)
    return written


def _filter_by_tag(files: list[str], tag: str | None) -> list[str]:
    if not tag:
        return files
    pat = re.compile(re.escape(tag), re.IGNORECASE)
    return [f for f in files if pat.search(f)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--list", action="store_true",
                        help="list available files on the DWD server")
    parser.add_argument("--download", action="store_true",
                        help="download files into RASTER_DIR/kostra_dwd_2020/")
    parser.add_argument("--convert", action="store_true",
                        help="convert downloaded .asc rasters to GeoTIFF")
    parser.add_argument("--tag", default=None,
                        help="filter filenames by substring (e.g. D60_T100)")
    parser.add_argument("--raster-dir", default=DEFAULT_RASTER_DIR,
                        help="root for outputs (defaults to RASTER_DIR env var)")
    parser.add_argument("--base-url", default=KOSTRA_BASE_URL,
                        help="override the KOSTRA index URL")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not (args.list or args.download or args.convert):
        parser.print_help()
        return 1

    target_dir = Path(args.raster_dir) / KOSTRA_SUBDIR

    if args.list:
        try:
            files = list_remote_files(args.base_url)
        except Exception as exc:
            logger.error("listing %s failed: %s", args.base_url, exc)
            return 2
        filtered = _filter_by_tag(files, args.tag)
        print(f"# {len(filtered)} file(s) under {args.base_url}")
        for f in filtered:
            print(f)

    if args.download:
        try:
            files = list_remote_files(args.base_url)
        except Exception as exc:
            logger.error("listing %s failed: %s", args.base_url, exc)
            return 2
        # Subdirectories show up with trailing "/" — flatten one level
        # if the index is one tier above the actual rasters.
        wanted: list[str] = []
        for entry in _filter_by_tag(files, args.tag):
            if entry.endswith("/"):
                # one level deeper
                try:
                    sub = list_remote_files(urljoin(args.base_url, entry))
                except Exception as exc:
                    logger.warning("listing %s failed: %s", entry, exc)
                    continue
                for sf in _filter_by_tag(sub, args.tag):
                    if sf.endswith("/"):
                        continue
                    wanted.append(urljoin(urljoin(args.base_url, entry), sf))
            else:
                wanted.append(urljoin(args.base_url, entry))

        if not wanted:
            logger.warning("no files matched tag=%r — try --list first", args.tag)
            return 0
        logger.info("downloading %d file(s) into %s", len(wanted), target_dir)
        download_files(wanted, target_dir)

    if args.convert:
        if not target_dir.exists():
            logger.error("convert target dir does not exist: %s", target_dir)
            return 2
        convert_asc_to_tif(target_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
