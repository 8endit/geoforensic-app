"""Download DWD KOSTRA-DWD-2020 starkregen rasters and convert to GeoTIFF.

Source:    https://opendata.dwd.de/climate_environment/CDC/grids_germany/return_periods/precipitation/KOSTRA/KOSTRA_DWD_2020/asc/
License:   GeoNutzV (commercial use OK with source attribution)
DOI:       10.5676/DWD/KOSTRA-DWD-2020
Attribution: "Deutscher Wetterdienst, KOSTRA-DWD-2020"

DWD-Struktur:
- Pro Dauerstufe ein ZIP-File ``StatRR_KOSTRA-DWD-2020_D00060_ASC.zip``,
  jedes ZIP enthält ASCII-Grids für alle Wiederkehrintervalle (T=1a, T=2a,
  T=3a, T=5a, T=10a, T=20a, T=30a, T=50a, T=100a) als .asc + .prj Pärchen.
- Dauerstufen-Verzeichnis: 5/10/15/20/30/45/60/90/120/180/240/360/540/720/
  1080/1440/2880/4320/5760/7200/8640/10080 Minuten.

Usage from inside the backend container::

    # Was liegt auf dem Server?
    python -m scripts.download_kostra --list

    # Default-Set holen (60min + 24h × T1/T10/T100, deckt KOSTRA_SLOTS ab):
    python -m scripts.download_kostra --ensure-default-set

    # Spezifische Dauerstufen ZIP herunterladen + entpacken + konvertieren:
    python -m scripts.download_kostra --download --convert --tag D00060
    python -m scripts.download_kostra --download --convert --tag D01440

Common --tag values (Dauerstufe DXXXXX in 5-stelliger Padded-Notation):
    D00005, D00010, D00015, D00020, D00030, D00045, D00060, D00090,
    D00120, D00180, D00240, D00360, D00540, D00720, D01080, D01440,
    D02880, D04320, D05760, D07200, D08640, D10080  (Minuten)

The actual lookup module (``kostra_data.py``) consumes the resulting
``kostra_D60_T100a.tif``-style GeoTIFFs from
``RASTER_DIR/kostra_dwd_2020/``. KOSTRA_SLOTS dort definiert genau das
6er-Default-Set, das ``--ensure-default-set`` erzeugt.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

KOSTRA_BASE_URL = (
    "https://opendata.dwd.de/climate_environment/CDC/grids_germany/"
    "return_periods/precipitation/KOSTRA/KOSTRA_DWD_2020/asc/"
)
USER_AGENT = "Bodenbericht/1.0 (kontakt@geoforensic.de)"
DEFAULT_RASTER_DIR = os.getenv("RASTER_DIR", "/app/rasters")
KOSTRA_SUBDIR = "kostra_dwd_2020"

# Default-Set: 6 buyer-relevante Slots = 2 Dauerstufen × 3 Wiederkehrintervalle.
# Match dem KOSTRA_SLOTS-Set in app/kostra_data.py.
# Format: (DauerstufenZip-Tag, [WiederkehrIntervall-Pattern in extrahierten Files])
DEFAULT_SET_DAUERSTUFEN = ["D00060", "D01440"]
DEFAULT_SET_T_MIN_MAX = (1, 100)  # T1a bis T100a aus dem ZIP nutzen wir alle dazwischen
# Intern haben die extracted ASC-Files Namen wie 'StatRR_KOSTRA-DWD-2020_D00060_T100a.asc'
# Wir benennen sie nach Konvertierung um auf 'kostra_D60_T100a.tif' (kompakter Glob-Match).
_FILENAME_RE = re.compile(r"D0*(\d+)_T(\d+)a\.(asc|tif)$", re.IGNORECASE)


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
    """Convert each .asc + .prj pair in ``asc_dir`` (recursive) to a GeoTIFF.

    Uses rasterio (already a backend dependency). The .asc file alone
    is enough — the AAIGrid driver reads it directly. CRS kommt aus dem
    nebenliegenden .prj wenn vorhanden, sonst Warning.

    Output landet im selben Verzeichnis wie die .asc; UND, wenn der
    Filename dem KOSTRA-Pattern ``D0?\\d+_T\\d+a`` entspricht, wird
    eine zweite Kopie als ``kostra_D<duration>_T<rp>a.tif`` direkt im
    asc_dir-Root angelegt — das ist der Glob-Pattern, den
    ``app/kostra_data.py`` KOSTRA_SLOTS erwartet.
    """
    import rasterio  # local import — heavy

    written: list[Path] = []
    for asc in sorted(asc_dir.rglob("*.asc")):
        tif = asc.with_suffix(".tif")
        if tif.exists() and tif.stat().st_size > 0:
            logger.info("skip (exists): %s", tif)
        else:
            logger.info("convert %s -> %s", asc, tif)
            try:
                with rasterio.open(asc) as src:
                    profile = src.profile.copy()
                    # No tiled=True: KOSTRA grids are small (~ 800×900 px) and
                    # the AAIGrid dimensions aren't multiples of 16, which
                    # rasterio requires for tiled GeoTIFF block writes.
                    # Striped output is fine for point-sample lookups.
                    profile.update(driver="GTiff", compress="deflate")
                    if not src.crs:
                        logger.warning("no CRS detected for %s — output GeoTIFF will be unreferenced", asc)
                    with rasterio.open(tif, "w", **profile) as dst:
                        dst.write(src.read())
            except Exception:
                logger.exception("conversion failed for %s — leaving .asc in place", asc)
                continue
        written.append(tif)

        # Zusätzlich: kompakter Symlink-Name im asc_dir-Root für KOSTRA_SLOTS-Glob
        m = _FILENAME_RE.search(asc.name)
        if m:
            duration = int(m.group(1))  # e.g. 60 oder 1440 (von D00060 / D01440)
            rp = int(m.group(2))         # e.g. 100, 10, 1
            compact = asc_dir / f"kostra_D{duration}_T{rp}a.tif"
            if not compact.exists():
                try:
                    # Hardlink statt copy spart Plattenplatz; bei Cross-Device fallback auf copy
                    import shutil
                    try:
                        os.link(tif, compact)
                    except OSError:
                        shutil.copy2(tif, compact)
                    logger.info("aliased %s -> %s", tif.name, compact.name)
                except Exception:
                    logger.exception("alias failed for %s", tif)
    return written


def extract_zips_in_place(target_dir: Path) -> list[Path]:
    """Extract every .zip in ``target_dir`` into a sibling subdir of the same name.

    Returns the list of extraction directories. Idempotent: if the target
    sub-directory already contains files, the ZIP is skipped.
    """
    extracted_dirs: list[Path] = []
    for z in sorted(target_dir.glob("*.zip")):
        out_dir = target_dir / z.stem  # StatRR_KOSTRA-DWD-2020_D00060_ASC
        if out_dir.is_dir() and any(out_dir.iterdir()):
            logger.info("skip extract (exists): %s", out_dir)
            extracted_dirs.append(out_dir)
            continue
        logger.info("extract %s -> %s", z.name, out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(z) as zf:
                zf.extractall(out_dir)
            extracted_dirs.append(out_dir)
        except Exception:
            logger.exception("extract failed for %s", z)
    return extracted_dirs


def ensure_default_set(target_dir: Path, base_url: str) -> int:
    """Pull + extract + convert exactly the 6 buyer-relevant slots.

    Idempotent: existing files are not re-downloaded or re-converted.
    Returns count of compact-named .tif files present at the end
    (expected: 18 = 9 Wiederkehrintervalle × 2 Dauerstufen, but the
    KOSTRA_SLOTS in kostra_data.py only references 6 of them).
    """
    target_dir.mkdir(parents=True, exist_ok=True)

    # Default-ZIPs ziehen (eine pro Dauerstufe)
    zip_urls: list[str] = []
    for tag in DEFAULT_SET_DAUERSTUFEN:
        zip_name = f"StatRR_KOSTRA-DWD-2020_{tag}_ASC.zip"
        zip_urls.append(urljoin(base_url, zip_name))
    download_files(zip_urls, target_dir)

    # ZIPs entpacken
    extract_zips_in_place(target_dir)

    # Konvertieren (rekursiv, mit kompaktem Alias für KOSTRA-Glob)
    convert_asc_to_tif(target_dir)

    compact_tifs = list(target_dir.glob("kostra_D*_T*a.tif"))
    logger.info("default-set complete: %d compact .tif files in %s", len(compact_tifs), target_dir)
    return len(compact_tifs)


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
                        help="extract any ZIPs and convert .asc rasters to GeoTIFF")
    parser.add_argument("--ensure-default-set", action="store_true",
                        help="one-shot: download D00060 + D01440 ZIPs, extract, convert, alias to kostra_D*_T*a.tif (the 6 buyer-relevant slots)")
    parser.add_argument("--tag", default=None,
                        help="filter filenames by substring (e.g. D00060)")
    parser.add_argument("--raster-dir", default=DEFAULT_RASTER_DIR,
                        help="root for outputs (defaults to RASTER_DIR env var)")
    parser.add_argument("--base-url", default=KOSTRA_BASE_URL,
                        help="override the KOSTRA asc/ index URL")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not (args.list or args.download or args.convert or args.ensure_default_set):
        parser.print_help()
        return 1

    target_dir = Path(args.raster_dir) / KOSTRA_SUBDIR

    if args.ensure_default_set:
        ensure_default_set(target_dir, args.base_url)
        return 0

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
        # Falls Downloads ZIPs sind: erst entpacken, dann konvertieren
        extract_zips_in_place(target_dir)
        convert_asc_to_tif(target_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
