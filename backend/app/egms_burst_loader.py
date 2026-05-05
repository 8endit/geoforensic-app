"""Service: EGMS Burst Loader — download + parse + cache.

Stream-downloaded Sentinel-1-Burst-ZIP, extrahiert nur die PIDs die wir
brauchen (= die ~80 PSI im 500m-Radius einer Adresse), schreibt long-format
Time-Series-Rows in egms_timeseries. Burst-CSV wird verworfen.

Cache-Logic:
- egms_burst_loaded(burst_id, loaded_at, row_count, source_qid_hash) Tabelle
  wird per Migration angelegt
- Vor Download: SELECT — falls Burst schon geladen, skip
- Nach Download+Insert: INSERT in egms_burst_loaded

Auth analog egms_search: EGMS_API_TOKEN aus env. Wenn leer → graceful skip.
Cookie-basierte Auth wird nicht implementiert (siehe egms_search.py).
"""

from __future__ import annotations

import asyncio
import csv
import datetime as dt
import io
import logging
import os
import re
import time
import zipfile
from typing import Any

import httpx

from app.egms_search import _auth_headers, is_enabled, EGMS_BASE

logger = logging.getLogger(__name__)

DOWNLOAD_PATH_PREFIX = "/insar-api/archive/download/"
DOWNLOAD_TIMEOUT_S = 120.0  # ~110 MB Burst kann uber 4G/Cloud bis 60s ziehen

_DATE_HEADER_RE = re.compile(r"^(\d{8})[A-Z]?$")


async def _is_burst_loaded(conn, burst_id: str) -> bool:
    """SELECT in egms_burst_loaded — ist dieser Burst schon parse-cached?"""
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM egms_burst_loaded WHERE burst_id = %s LIMIT 1",
        (burst_id,),
    )
    return cur.fetchone() is not None


async def _mark_burst_loaded(
    conn, burst_id: str, row_count: int, qid_hash: int,
) -> None:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO egms_burst_loaded (burst_id, loaded_at, row_count, "
        "source_qid_hash) VALUES (%s, NOW(), %s, %s) "
        "ON CONFLICT (burst_id) DO UPDATE SET loaded_at = EXCLUDED.loaded_at, "
        "row_count = EXCLUDED.row_count, source_qid_hash = EXCLUDED.source_qid_hash",
        (burst_id, row_count, qid_hash),
    )


async def _download_burst_zip(
    burst_filename: str, qid: str, timeout: float = DOWNLOAD_TIMEOUT_S,
) -> bytes | None:
    """GET /insar-api/archive/download/<filename>.zip?id=<qid> mit Auth.

    Returns ZIP-Bytes oder None bei Fehler. Ruft is_enabled() — ohne Token
    null-return.
    """
    if not is_enabled():
        return None
    url = f"{EGMS_BASE}{DOWNLOAD_PATH_PREFIX}{burst_filename}?id={qid}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=_auth_headers())
            if resp.status_code == 401:
                logger.error(
                    "EGMS burst download 401 for %s — qid expired (rerun "
                    "search) or token invalid",
                    burst_filename,
                )
                return None
            resp.raise_for_status()
            data = resp.content
            # ZIP-Magic bestaetigen damit wir nicht versehentlich HTML
            # einer Error-Page parsen
            if not data.startswith(b"PK\x03\x04"):
                logger.warning(
                    "EGMS burst %s did not return ZIP (got %r...) — likely "
                    "auth or qid issue", burst_filename, data[:8],
                )
                return None
            return data
    except httpx.HTTPError as exc:
        logger.warning("EGMS burst download failed for %s: %s", burst_filename, exc)
        return None


def _open_csv_from_zip(zip_bytes: bytes) -> tuple[io.StringIO, str] | None:
    """Open the CSV inside the burst ZIP. EGMS ZIPs contain exactly one CSV."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            logger.warning("Burst ZIP contains no CSV: %s", zf.namelist())
            return None
        with zf.open(csv_names[0]) as f:
            raw = f.read()
        # EGMS-CSVs sind UTF-8 mit ggf BOM, ';' oder ',' Separator
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                txt = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            logger.warning("Burst CSV cannot be decoded")
            return None
        return io.StringIO(txt), csv_names[0]


def _parse_and_filter(
    csv_text: io.StringIO, target_pids: set[str],
) -> list[tuple[str, dt.date, float]]:
    """Streamendes CSV-Parse: nur Rows mit pid in target_pids returnen.

    Wide-Format → Long-Format ((pid, date, displacement_mm) Tupel).
    Spart RAM weil wir nicht alle 600k Zeilen × 250 Datums vorhalten,
    sondern nur die ~80 PIDs die wir brauchen.
    """
    # Sniff delimiter
    sample = csv_text.read(2048)
    csv_text.seek(0)
    delim = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.reader(csv_text, delimiter=delim)
    header = next(reader)
    norm = [h.strip().lower() for h in header]
    try:
        pid_idx = norm.index("pid")
    except ValueError:
        logger.warning("Burst CSV has no pid column; header=%s", header[:6])
        return []
    date_cols: list[tuple[int, dt.date]] = []
    for i, h in enumerate(header):
        m = _DATE_HEADER_RE.match(h.strip())
        if m:
            ymd = m.group(1)
            try:
                date_cols.append(
                    (i, dt.date(int(ymd[0:4]), int(ymd[4:6]), int(ymd[6:8])))
                )
            except ValueError:
                pass
    if not date_cols:
        logger.warning("Burst CSV has no date columns; cannot extract time series")
        return []

    out: list[tuple[str, dt.date, float]] = []
    for row in reader:
        if len(row) <= pid_idx:
            continue
        pid = row[pid_idx].strip()
        if pid not in target_pids:
            continue
        for col_idx, d in date_cols:
            if col_idx >= len(row):
                continue
            raw = row[col_idx].strip()
            if not raw or raw.lower() in ("nan", "null", "n/a"):
                continue
            try:
                disp = float(raw)
            except ValueError:
                continue
            out.append((pid, d, disp))
    return out


async def ensure_bursts_loaded(
    conn,
    qid: str,
    bursts: list[dict[str, Any]],
    target_pids: set[str],
) -> dict[str, int]:
    """Fuer eine Liste von Bursts: download + parse + insert in egms_timeseries.

    Skips Bursts die schon geladen sind (egms_burst_loaded). Inserts sind
    idempotent (ON CONFLICT DO NOTHING auf egms_timeseries-PK).

    target_pids: Set der PSI-pids die wir extrahieren (= die ~80 PIDs der
    egms_points im 500m-Radius der Adresse). Andere PIDs werden NICHT in
    egms_timeseries geschrieben — wir parsen die CSV einmal komplett, aber
    persistieren nur was relevant ist. Spart Storage massiv (60GB+ DE bei
    Selektivitaet).

    Returns dict {burst_id: rows_inserted}.
    """
    if not is_enabled():
        logger.info("egms_burst_loader: EGMS_API_TOKEN not set, skipping")
        return {}
    qid_hash = abs(hash(qid)) % (2**31)
    out: dict[str, int] = {}
    # Sequentiell statt parallel — wir wollen die EGMS-Origin nicht mit
    # 5 simultanen 110-MB-Streams ueberfahren. Plus: pro Bericht nur
    # 2-3 Bursts, also ist parallel kein Gewinn.
    for tile in bursts:
        burst_id = tile.get("burstId") or tile.get("burst_id") or tile.get("filename", "")
        filename = tile.get("filename")
        if not filename:
            continue
        if await _is_burst_loaded(conn, burst_id):
            logger.info("burst already loaded, skipping: %s", burst_id)
            out[burst_id] = 0
            continue
        t0 = time.time()
        zip_bytes = await _download_burst_zip(filename, qid)
        if zip_bytes is None:
            continue
        logger.info(
            "downloaded burst %s (%.1f MB) in %.1fs",
            burst_id, len(zip_bytes) / (1024 * 1024), time.time() - t0,
        )
        opened = _open_csv_from_zip(zip_bytes)
        if opened is None:
            continue
        csv_text, _csv_name = opened
        rows = _parse_and_filter(csv_text, target_pids)
        if not rows:
            logger.info("burst %s: 0 matching pids, marking as loaded anyway", burst_id)
            await _mark_burst_loaded(conn, burst_id, 0, qid_hash)
            out[burst_id] = 0
            continue
        # Bulk-INSERT via psycopg2's copy_expert/staging-Pattern wie in
        # import_egms_l2_timeseries.py — wieder verwenden.
        from scripts.import_egms_l2_timeseries import _copy_timeseries_batch  # type: ignore
        # Wir brauchen hier pid → egms_points.id Mapping. Caller muss das
        # liefern oder wir machen einen on-the-fly-Lookup.
        # → Einfacher: wir lassen Caller (Pipeline) target_pids als
        # {egms_pid: egms_points.id}-Map liefern statt einer Set.
        # Diese Funktion ist Stub: wenn target_pids ein Set ist, machen
        # wir keinen Insert (Caller-Vertrag wird in Pipeline-Hook
        # angepasst).
        if not isinstance(target_pids, dict):
            logger.error(
                "ensure_bursts_loaded: target_pids must be dict {egms_pid: id}, "
                "got %s — refactor pipeline-stage to pass mapping",
                type(target_pids).__name__,
            )
            continue
        rows_with_id = [
            (target_pids[pid], d, disp) for (pid, d, disp) in rows if pid in target_pids
        ]
        inserted = _copy_timeseries_batch(conn, rows_with_id)
        conn.commit()
        await _mark_burst_loaded(conn, burst_id, inserted, qid_hash)
        out[burst_id] = inserted
        logger.info(
            "burst %s: %d timeseries rows inserted (out of %d matching pids)",
            burst_id, inserted, len(rows_with_id),
        )
    return out
