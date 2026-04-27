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

**Status:** TEILWEISE VERIFIZIERT — integriert mit Env-Var-Override
für Layer-Namen, Live-Capabilities-Test bleibt empfohlen

| Feld | Wert |
|---|---|
| Portal-URL | `https://geoportal.bafg.de/karten/HWRM_Aktuell/` |
| WMS-Endpunkt | `https://geoportal.bafg.de/arcgis1/rest/services/INSPIRE/NZ/MapServer/exts/InspireView/service` |
| INSPIRE-Theme | NZ (Natural Risk Zones), nicht AM wie zuvor angenommen |
| Layer-Namen (best-guess) | `HQ_haeufig` (T=5–20a), `HQ100` (T=100a), `HQ_extrem` (≈ 1.5×HQ100) |
| Format | WMS 1.3.0 (ArcGIS InspireView) |
| Granularität | Polygone, bundesweit aus Länder-Meldungen aggregiert |
| **Lizenz** | **Datenlizenz Deutschland — Zero — Version 2.0 (DL-DE/Zero-2.0)** — keine Attribution-Pflicht, kein Copyleft, kommerziell OK |
| Lizenz-URL 1 | `https://www.govdata.de/dl-de/zero-2-0` (Lizenztext) |
| Lizenz-URL 2 | GovData-Eintrag „Überflutungsflächen-DE (HWRM-RL 2. Zyklus 2016-2021)" |
| Kommerziell OK | **ja** — DL-DE/Zero-2.0 erlaubt jede Nutzung ohne Bedingungen |
| Attribution | freiwillig (Empfehlung: „Datengrundlage: Bundesanstalt für Gewässerkunde (BfG), HWRM-RL 2. Zyklus 2016-2021, DL-DE/Zero-2.0") |

**Caveats:**
- ArcGIS-Endpunkt antwortet bei automatisierten Requests aus der
  Cloud-Sandbox mit 403. Vom VPS oder lokal aus QGIS funktioniert er.
- Die exakten WMS-`<Name>`-Strings sind nicht aus einem live abgerufenen
  Capabilities-XML bestätigt — Best-Guess aus 3 Sekundärquellen
  (LfU Bayern, klima-sicher-bauen.de, GovData). Override via Env-Vars
  `BFG_FLOOD_LAYER_HAEUFIG`, `BFG_FLOOD_LAYER_HQ100`,
  `BFG_FLOOD_LAYER_EXTREM`, falls die Live-Verifizierung andere
  Strings ergibt.
- Höhere Auflösung gibt es bei den Länder-Geoportalen (NRW
  ELWAS-WEB, Bayern IÜG, BW hochwasser.baden-wuerttemberg.de) — der
  BfG-Aggregat-Layer reicht für ein nationales Käufer-PDF.

**TODO nach Deploy:**
- [ ] Capabilities-XML vom VPS aus mit `curl -A "Mozilla/5.0"` ziehen
      und Layer-Namen verifizieren — siehe §6 unten
- [ ] Falls Layer-Namen abweichen: Env-Vars setzen, Backend neu
      starten (kein Code-Change)

---

## Layer 2 — Radon-Vorsorgegebiete

**Status:** **TEILWEISE VERIFIZIERT** — Sachsen ist VERIFIZIERT,
andere 4 Bundesländer brauchen noch Klärung

### Pro Bundesland

| BL | Status | Lizenz | WMS-/Daten-Endpunkt |
|---|---|---|---|
| **Sachsen** | **VERIFIZIERT** | dl-de/by-2.0 (explizit zitiert) | MetaVer-Eintrag `8ad390b7-2b7e-4322-a188-c87f303ad8be` (WMS) |
| Niedersachsen | NICHT VERIFIZIERT | unklar | kein WMS — 4 Gemeinden bekannt (Goslar, Clausthal-Zellerfeld, Braunlage), AGS-Workaround mit BKG VG250 möglich |
| Bayern | TEILWEISE | dl-de/by-2.0 vermutet, nicht aus Metadaten | LfU-Index `lfu.bayern.de/umweltdaten/geodatendienste/index_wms.htm` — WMS-URL aus Index zu ziehen |
| Sachsen-Anhalt | TEILWEISE | dl-de/by-2.0 vermutet | GeoWebDienste-Index `lvermgeo.sachsen-anhalt.de/de/geowebdienste-lsa/wms-dienste.html` |
| Thüringen | TEILWEISE | dl-de/by-2.0 vermutet | Geoportal-Th Download-Index, oder AGS-Workaround |
| BfS Bundes-Aggregat | TEILWEISE | unklar — BfS sagt selbst „nur Übersicht ohne Rechtskraft" | `https://www.imis.bfs.de/cgi-public/wms_geoportal?...` |

### Sachsen-Detail (verifiziert)

| Feld | Wert |
|---|---|
| MetaVer-WMS-Eintrag | `https://metaver.de/trefferanzeige?docuuid=8ad390b7-2b7e-4322-a188-c87f303ad8be` |
| MetaVer-WFS-Eintrag | `https://metaver.de/trefferanzeige?docuuid=127e7da5-9904-4f9c-97e4-a377bfb81091` |
| Verordnungs-Status | Sächsisches Amtsblatt 03.12.2020, in Kraft seit 31.12.2020 |
| Lizenz wörtlich | „Datenlizenz Deutschland – Namensnennung – Version 2.0 (dl-de/by-2-0)" |
| Attribution | „Sächsisches Landesamt für Umwelt, Landwirtschaft und Geologie" |
| Granularität | Gemeinde-Polygon |

**Empfehlung:** Phase-2 — Sachsen kann morgen ingestet werden, Pattern
für ein Modul `radon_data.py` mit Per-State-Dispatcher steht. NI-AGS-
Workaround als zweiter Schritt. BY/ST/TH brauchen je 30–60min
Geoportal-Klick-Klärung. Für **diese Session noch nicht integriert** —
zu schmaler ROI für nur ein Bundesland im ersten Wurf.

---

## Layer 3 — Erdbebenzonen DIN EN 1998-1/NA

**Status:** NICHT VERIFIZIERT — **doppelt bestätigt verschoben**

| Feld | Wert |
|---|---|
| Korrekte Quelle | **GFZ Potsdam**, nicht BGR |
| GFZ-Web-Form (alt, NA:2011-01) | `https://www.gfz.de/en/din4149-erdbebenzonenabfrage` |
| GFZ-Web-Form (NA:2023-11) | `https://koordb.gfz-potsdam.de/Koordinatenabfrage_DIN_html.php` |
| GFZ-Erdbebenzonen + Untergrundklassen | `https://ebz.gfz-potsdam.de/index_ug_cms.php` |
| Format | **NUR Web-Form Adress-Lookup, KEIN WMS/WFS/Download** |
| Regional verfeinert | LGRB Baden-Württemberg (`geoportal.lgrb-bw.de`) |
| BGR macht | nur **GERSEIS** (Erdbeben-Ereigniskatalog), NICHT die DIN-Zonen |
| Lizenz | unbekannt — GFZ ist Helmholtz-Einrichtung |
| GFZ-Disclaimer | „GFZ assumes no guarantee and liability" — kein Lizenz-Statement |
| Urheberrecht | DIN-Norm! Wörtlich: „reproduction of standards documents is only permitted for authorized persons for scientific and non-commercial use" |

**Konsequenzen aus zweiter Recherche-Runde 2026-04-27:**
- Es gibt **keine maschinenlesbare Datenschnittstelle** bei GFZ —
  nur drei Web-Forms für Adress-Lookups.
- DIN-Urheberrecht ist real und plausibel relevant: die Zonenkarte
  ist Anhang einer Norm, deren Reproduktion explizit eingeschränkt
  ist. Ohne schriftliche Klärung beim GFZ und/oder DIN-Verlag ist
  Ingest ein Rechtsrisiko.
- Wie kommerzielle Statik-Tools (Dlubal etc.) das gelöst haben, ist
  aus öffentlichen Quellen nicht ersichtlich — vermutlich
  Direkt-Lizenzvertrag.

**Empfehlung:** **Verschoben**. Mail-Anfrage parallel zu BBSR/BGR-BBD
rausschicken (Vorlage: `docs/MAIL_GFZ_ERDBEBEN.md`). Antwort kann ggf.
„kostenpflichtig per DIN-Verlag" sein — dann technisch nicht in dieses
Produkt integrierbar, in dem Fall im Bericht als „Hinweis-Layer" mit
Link auf das GFZ-Webtool führen.

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

| # | Layer | Status | Code-Stand | Empfehlung |
|---|---|---|---|---|
| 5 | NRW Bergbau | VERIFIZIERT | **integriert** (`mining_nrw.py` + Sektion 3) | Smoke-Test vom VPS |
| 1 | BfG HWRM | TEILW. (Lizenz DL-DE/Zero-2.0, beste denkbare) | **integriert** (`flood_data.py` + Sektion 4) | Layer-Namen vom VPS verifizieren, ggf. Env-Vars setzen |
| 4 | DWD KOSTRA | TEILW. (Lizenz grün, kein WMS) | **Pull-Script + Lookup-Modul integriert**, Daten ausstehend | `download_kostra.py` vom VPS laufen lassen, Filename-Schema verifizieren |
| 2a | Radon Sachsen | VERIFIZIERT (dl-de/by-2.0) | nicht integriert | Phase-2 Modul `radon_data.py` mit Per-State-Dispatcher |
| 2b | Radon BY/NI/ST/TH | TEILW. | nicht integriert | je BL 30–60min Klärung, NI per AGS-Workaround machbar |
| 3 | GFZ Erdbeben | NICHT VERIFIZIERT — DIN-Urheberrecht-Risiko | nicht integriert | Mail an GFZ + ggf. DIN-Verlag (Vorlage `MAIL_GFZ_ERDBEBEN.md`) |

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
