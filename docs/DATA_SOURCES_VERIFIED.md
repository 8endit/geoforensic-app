# DATA_SOURCES_VERIFIED.md — Layer-Katalog mit Verifizierungs-Stand

**Stand:** 2026-04-27. Live-Verifizierung durch Web-Recherche-Agent
+ Cloud-curl-Versuche (eingeschränkt durch Sandbox-Allowlist).

**Zweck:** Einziges Dokument, dem wir bei der Layer-Integration vertrauen.
Pauschal-Annahmen aus früheren Docs (`PLAN_GEOFORENSIC_DE.md`,
`DATA_SOURCES_GROUNDSURE_PARITY.md`, `MARKET_REALITY_DE_2026.md`) sind
**ungültig**, sobald sie diesem Doc widersprechen.

**Verifizierungs-Skala:**
- **VERIFIZIERT** — Endpunkt + Layer-Name + Lizenz aus mindestens zwei
  unabhängigen Quellen bestätigt
- **TEILWEISE VERIFIZIERT** — Quelle existiert nachweislich, aber
  Lizenztext oder Capabilities-XML nicht direkt gelesen (z. B. wegen
  HTTP-403 bei automatisiertem Fetch)
- **NICHT VERIFIZIERT** — Quelle nicht klar, oder ursprüngliche
  Annahme falsch

**Sandbox-Hinweis:** Die hiesige Cloud-Umgebung hat eine
Host-Allowlist für ausgehende Requests. Deutsche Geoportale
(`geoportal.bafg.de`, `services.bgr.de`, `wms.nrw.de`,
`opendata.dwd.de` etc.) sind nicht drin. Live-Capabilities-Checks
müssen **vom VPS** oder von einem lokalen PC aus laufen — Anleitung
unten in §6.

---

## Layer 1 — BfG Hochwassergefahren-/Risikokarten (HWRM)

**Status:** TEILWEISE VERIFIZIERT — Live-Capabilities-Test offen

| Feld | Wert |
|---|---|
| Portal-URL | `https://geoportal.bafg.de/karten/HWRM_Aktuell/` |
| WMS-Basis (vermutet) | `https://geoportal.bafg.de/arcgis/services/INSPIRE/AM/MapServer/WMSServer` |
| Layer-Namen | unbekannt — Capabilities nicht direkt gelesen |
| Format | WMS 1.3.0 (ArcGIS) |
| Granularität | Polygone, bundesweit aggregiert aus Länder-Meldungen |
| Lizenz | GeoNutzV (nur Sekundärquelle) |
| Lizenz-URL 1 | `https://www.gesetze-im-internet.de/geonutzv/` (Verordnungstext) |
| Lizenz-URL 2 | gispoint.de Sekundärzitat: „BfG provides geodata under GeoNutzV — free of charge for commercial and non-commercial use" |
| Kommerziell OK | ja (laut Sekundärquelle) — **direkt aus AccessConstraints des Capabilities-XML noch nicht bestätigt** |
| Attribution | „© BfG, GeoNutzV" — exakter Wortlaut noch nicht verifiziert |

**Caveats:**
- WasserBLIcK-Hinweis: einzelne Länder schränken Detail-Daten ein.
  Bundesweite Vollständigkeit nicht garantiert.
- ArcGIS-Endpunkt antwortet bei automatisierten Requests mit 403,
  auch mit Browser-User-Agent. Manueller Browser-Aufruf vom VPS oder
  lokalen PC nötig.

**TODO vor Ingest:**
- [ ] Capabilities-XML manuell ziehen (curl mit Cookie/Browser-Header
      vom VPS oder lokalem PC) und Layer-Namen + AccessConstraints
      lesen
- [ ] GeoNutzV-Wortlaut auf gesetze-im-internet.de selbst gegenlesen

---

## Layer 2 — BfS Radon-Vorsorgegebiete

**Status:** NICHT VERIFIZIERT — fragmentiert über Bundesländer

| Feld | Wert |
|---|---|
| BfS-Geoportal | `https://www.bfs.de/DE/themen/ion/umwelt/luft-boden/geoportal/geoportal_node.html` |
| BfS-Aussage | „nur die offiziellen Bekanntmachungen der Länder sind verbindlich, die Karte hat keine Rechtskraft" |
| Rechtsverbindlich | 16 separate Landesverordnungen (§121 StrlSchG) |
| Bekannte Landes-Quellen | LfU Bayern, LFU Sachsen-Anhalt, sachsen.de, ggf. Niedersachsen, Thüringen |
| Lizenz | uneinheitlich — pro Bundesland separat zu prüfen |

**Konsequenz:**
- Eine BfS-Pauschalintegration ist **rechtlich nicht haltbar**.
- Für eine kommerzielle Integration müssten 5 Landes-WMS gepflegt
  werden (BY, NI, SN, ST, TH), je mit eigener Lizenz und Attribution.
- Aufwand-Schätzung: mehrere Tage pro Bundesland für sauberes
  Lizenz-Setup.

**Empfehlung:**
- Für Phase 1 verschieben.
- Alternative: Hinweistext im Bericht („Radon-Vorsorgegebiete sind
  in DE pro Bundesland geregelt — bitte beim zuständigen Landesamt
  prüfen") + Link auf BfS-Übersicht.

---

## Layer 3 — Erdbebenzonen DIN EN 1998-1/NA

**Status:** NICHT VERIFIZIERT — ursprüngliche Quelle (BGR) war falsch

| Feld | Wert |
|---|---|
| Korrekte Quelle | **GFZ Potsdam**, nicht BGR |
| GFZ-URL | `https://www.gfz.de/en/din4149-erdbebenzonenabfrage` |
| Regional verfeinert | LGRB Baden-Württemberg |
| BGR macht | nur **GERSEIS** (Erdbeben-Ereigniskatalog), NICHT die DIN-Zonen |
| Lizenz | unbekannt — GFZ ist Helmholtz-Einrichtung, eigene Bedingungen |
| Urheberrecht | Karte ist Teil einer DIN-Norm — DIN-Verlag-Lizenz möglich |

**Caveats:**
- Vor Ingest: GFZ schreiben (Lizenz-Anfrage analog BBSR/BBD) oder
  DIN-Verlag konsultieren.
- Mindestens 1 Tag Klärungsaufwand.

**Empfehlung:**
- Für Phase 1 verschieben.
- Bei NL-Adressen ohnehin nicht relevant (NL hat nur sehr lokale
  Beben in Groningen — eigenes KNMI-Thema).

---

## Layer 4 — DWD KOSTRA-DWD-2020 (Starkregen)

**Status:** TEILWEISE VERIFIZIERT — Lizenz grün, kein WMS

| Feld | Wert |
|---|---|
| Endpunkt | `https://opendata.dwd.de/climate_environment/CDC/grids_germany/return_periods/precipitation/KOSTRA/KOSTRA_DWD_2020/` |
| DOI-Landing | `https://opendata.dwd.de/climate_environment/CDC/help/landing_pages/doi_landingpage_KOSTRA_DWD_2020-de.html` |
| Format | Download (ASCII-Raster `.asc`, Tabellen `.tab`, PDF) — **kein WMS** |
| Granularität | Raster auf Indexgittern, Dauerstufen 5 min – 72 h, Wiederkehr T = 1, 2, 5, 10, 20, 30, 50, 100 a |
| Lizenz | GeoNutzV (kommerziell OK mit Quellenangabe) |
| Lizenz-URL 1 | `https://opendata.dwd.de/climate_environment/CDC/Nutzungsbedingungen_German.pdf` (PDF, nicht direkt geöffnet) |
| Lizenz-URL 2 | DWD-Datenpolitik-Seite: pauschal GeoNutzV für DWD-Daten |
| Attribution | „Deutscher Wetterdienst, KOSTRA-DWD-2020, DOI 10.5676/DWD/KOSTRA-DWD-2020" |
| DOI | `10.5676/DWD/KOSTRA-DWD-2020` |

**Engineering-Pfad:**
- Pattern A (Raster auf Server) — ASCII-Raster konvertieren zu
  GeoTIFF (mit `gdal_translate`), in `RASTER_DIR` legen, neuen
  Eintrag in `soil_data.py` (oder besser: neues Modul `kostra_data.py`)
- Pro Adresse: Punkt → Index → Niederschlagshöhe für Dauerstufe x
  Wiederkehr-Intervall

**Aufwand:** 1–2 Tage Engineering. Lizenz blockiert nicht.

---

## Layer 5 — NRW Bergbauberechtigungen

**Status:** **VERIFIZIERT** — höchstes Vertrauen aller fünf Layer

| Feld | Wert |
|---|---|
| Endpunkt | `https://www.wms.nrw.de/wms/wms_nw_inspire-bergbauberechtigungen` |
| Capabilities | `?REQUEST=GetCapabilities&SERVICE=WMS` (Standard) |
| Layer | gültige + erloschene Bergbauberechtigungen mit Feldname, Größe, Bodenschatz, Berechtigungsart, Berechtigtem, Befristungen |
| Format | WMS (INSPIRE-konform) + ATOM-Feed mit Shapefile/GML/GeoJSON |
| Granularität | Polygone auf Grubenfeld-Ebene |
| Lizenz | **dl-de/by-2.0** |
| Lizenz-URL 1 | `https://www.wms.nrw.de/rssfeeds/content/geoportal/html/1030.html` (RSS-News „Bergbauberechtigungen NRW jetzt Open Data") |
| Lizenz-URL 2 | `https://www.opengeodata.nrw.de/produkte/geologie/bergbau/bebu/` (Open.NRW Produktseite) |
| Lizenz-URL 3 | INSPIRE-Geoportal: `e121fccc-ca2a-4681-a727-6aed0568b487` |
| Kommerziell OK | ja |
| Attribution | „Bezirksregierung Arnsberg, dl-de/by-2.0" (Wortlaut ungefähr) |

**Caveats:**
- Nur NRW. Bundesweit gibt es keine einheitliche Bergbau-Quelle —
  pro Land separates Amt (Bayern: StMWi, Niedersachsen: LBEG etc.).
- Phase 1: NRW reicht als regionaler Add-on. Andere BL als Phase-2.

**Engineering-Pfad:**
- Pattern C (WMS-live) — neues Modul `mining_nrw.py` mit
  GetFeatureInfo-Aufruf, in den Full-Bericht für NRW-Adressen
  integrieren
- Bei Nicht-NRW-Adressen: Layer-Sektion ausblenden oder „nicht
  relevant für Ihren Standort"

**Aufwand:** 1 Tag.

---

## Zusammenfassung & Empfehlung

| # | Layer | Status | Sofort startbar | Empfehlung |
|---|---|---|---|---|
| 5 | NRW Bergbau | VERIFIZIERT | ja | **Sofort starten** |
| 4 | DWD KOSTRA | TEILW. VERIFIZIERT (Lizenz grün, Engineering klar) | ja, nach Capabilities-Lese vom VPS | Engineering kann beginnen |
| 1 | BfG HWRM | TEILW. VERIFIZIERT (Live-Capabilities offen) | nein, erst Capabilities-Test vom VPS | Verify dann starten |
| 2 | BfS Radon | NICHT VERIFIZIERT — Patchwork | nein | **Verschoben** |
| 3 | GFZ Erdbeben | NICHT VERIFIZIERT — Quelle korrigiert | nein | **Verschoben**, Mail an GFZ |

---

## §6 — Live-Capabilities-Test vom VPS oder lokal

Folgende Befehle vom VPS (`185.218.124.158`) oder von deinem lokalen
PC ausführen, um die offenen Punkte zu verifizieren:

### BfG HWRM — Capabilities + Layer-Namen + AccessConstraints

```bash
curl -A "Mozilla/5.0 geoforensic.de research" \
  "https://geoportal.bafg.de/arcgis/services/INSPIRE/AM/MapServer/WMSServer?REQUEST=GetCapabilities&SERVICE=WMS&VERSION=1.3.0" \
  -o bfg_caps.xml
# Layer-Namen und AccessConstraints aus dem XML extrahieren:
grep -E "<Name>|<AccessConstraints>" bfg_caps.xml | head -40
```

Falls 403: vom Browser-Tab des Portals aus die Capabilities-URL als
zweite Tab-URL aufrufen (Cookie wird übernommen) und das XML
herunterladen. Wenn das auch nicht geht: Mail an
`info@geoportal.bafg.de` mit Frage nach offizieller WMS-URL.

### NRW Bergbau — Capabilities verifizieren

```bash
curl "https://www.wms.nrw.de/wms/wms_nw_inspire-bergbauberechtigungen?REQUEST=GetCapabilities&SERVICE=WMS" \
  -o nrw_bergbau_caps.xml
grep -E "<Name>|<AccessConstraints>" nrw_bergbau_caps.xml | head -40
```

### DWD KOSTRA — Index-File + ein Raster ziehen

```bash
# Verzeichnis-Index
curl -s "https://opendata.dwd.de/climate_environment/CDC/grids_germany/return_periods/precipitation/KOSTRA/KOSTRA_DWD_2020/" | head -100
# Lizenz-PDF
curl -O "https://opendata.dwd.de/climate_environment/CDC/Nutzungsbedingungen_German.pdf"
```

### Geoforensic-Sandbox-Hinweis

Falls du diese Calls hier in der Cloud-Session machen willst, geht's
nicht — Host-Allowlist blockt deutsche Behörden-Domains. **Vom VPS
aus oder lokal vom PC** funktioniert es ohne diese Beschränkung.

---

## Disziplin-Regel für künftige Layer

Bevor wir einen Layer in den Code einbauen, **muss** er in diesem
Doc als VERIFIZIERT stehen. Heißt konkret:

- [ ] Capabilities-XML wirklich gelesen (vom VPS oder lokal)
- [ ] Lizenztext aus zwei unabhängigen Quellen wörtlich zitiert
- [ ] Granularität und Layer-Namen dokumentiert
- [ ] Attribution-Wortlaut festgehalten (kommt 1:1 in den Bericht-Footer)

Wir haben uns einmal mit BBSR vertan — das soll nicht wieder
passieren.
