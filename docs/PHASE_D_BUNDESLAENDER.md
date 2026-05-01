# PHASE_D_BUNDESLAENDER.md — Bundesländer-Vollabdeckung DE

**Stand:** 2026-05-01, nach Phase A+B+B.3 + KOSTRA/ESDAC-Deploy.
**Bezug:** Aktueller Vollbericht hat eine bundesweit gleiche Datenbasis für Hochwasser, Starkregen, Bodenbewegung, Bodenchemie, Pestizide, Geländeprofil, EU-Bodenrichtlinie. Die Lücken sind bundesländer-spezifische Layer wo wir aktuell nur 1 von 16 BL abdecken oder gar keinen.

**Wann angehen:** Nach Visuals-Sprint (`VISUALS_ROLLOUT_PLAN.md`). Phase D macht keine Visualisierungen, sondern Daten-Tiefe pro BL.

---

## 1. Aktuelle BL-Coverage-Matrix

| Datenquelle | Aktuelle Coverage | Was fehlt |
|---|---|---|
| BfG Hochwasser HWRM | **alle 16 BL** ✓ | nichts |
| DWD KOSTRA Starkregen | **alle 16 BL** ✓ | nichts |
| LUCAS Schwermetalle (DE-Punkte, IDW) | **alle 16 BL** ✓ | nichts |
| EGMS Bodenbewegung | **alle 16 BL** ✓ | nichts |
| SoilGrids / CORINE / HRL Imperviousness | **alle 16 BL** ✓ | nichts |
| Pestizide LUCAS NUTS2 | **alle NUTS2-Regionen** ✓ | nichts |
| **Bergbauberechtigungen** | **NUR NRW** | 15 BL fehlen |
| **Radon-Vorsorgegebiete** | **0 BL implementiert** (Sachsen verifiziert, Modul fehlt) | 5+ BL fehlen |
| **Erdbebenzonen** | **0 BL implementiert** | DIN-Lizenz blockiert |
| **Altlastenkataster** | **DE = nur CORINE-Proxy** | INSPIRE-geschützt, kein Open-Data |

---

## 2. Phase-D-Sprint-Plan

### D.1 — Bergbau für 6+ Bundesländer

**Aktuell:** `mining_nrw.py` hat nur Bezirksregierung Arnsberg WMS.

**Aufgabe:** Pro BL eigenes Modul oder ein gemeinsames `mining_data.py` mit Country-Routing.

| BL | Behörde | Datendienst |
|---|---|---|
| Bayern | StMWi (Bergbehörde) | WMS unklar — Recherche nötig |
| Niedersachsen | LBEG (Landesamt für Bergbau, Energie und Geologie) | LBEG-WMS, lbeg.niedersachsen.de |
| Sachsen | LfULG (Landesamt für Umwelt, Landwirtschaft und Geologie) | Geoportal Sachsen |
| Sachsen-Anhalt | LAGB (Landesamt für Geologie und Bergwesen) | lvermgeo.sachsen-anhalt.de |
| Thüringen | TLUBN (Landesamt für Umwelt, Bergbau und Naturschutz) | Geoportal Thüringen |
| Baden-Württemberg | LGRB (Landesamt für Geologie, Rohstoffe und Bergbau) | rips-gdi.lubw |
| Rheinland-Pfalz | LGB (Landesamt für Geologie und Bergbau) | mapclient.lgb-rlp.de |
| Saarland, Hessen, Berlin, Brandenburg, etc. | weniger relevant — wenig aktiver Bergbau | zurückstellbar |

**Implementation:** Pro BL ein async-Query in `mining_data.py`, BL aus Coordinate ableiten via NUTS-Code oder Bbox-Heuristik. Jede BL liefert in dasselbe `ContaminatedSite`-ähnliche Datenformat.

**Akzeptanz:** Vollbericht zeigt für Adressen in den 7 Top-Bergbau-BL (NRW, NI, SN, BW, BY, RP, ST) echte Berechtigungs-Daten; Rest sagt sachlich „kein öffentlicher Dienst integriert, Anfrage beim zuständigen Landesamt".

---

### D.2 — Radon-Vorsorgegebiete

**Aktuell:** kein Modul.

**Datenquellen-Stand (siehe `docs/DATA_SOURCES_VERIFIED.md` Layer 2):**

| BL | Status | Endpunkt / Quelle |
|---|---|---|
| Sachsen | **VERIFIZIERT** dl-de/by-2.0 | MetaVer-WMS `8ad390b7-2b7e-4322-a188-c87f303ad8be` |
| Niedersachsen | NICHT VERIFIZIERT | kein WMS — 4 Gemeinden bekannt (Goslar, Clausthal, Braunlage), AGS-Workaround |
| Bayern | TEILWEISE | LfU-Index `lfu.bayern.de/umweltdaten/geodatendienste/` |
| Sachsen-Anhalt | TEILWEISE | GeoWebDienste-Index `lvermgeo.sachsen-anhalt.de/de/geowebdienste-lsa/` |
| Thüringen | TEILWEISE | Geoportal-Th Download-Index oder AGS-Workaround |
| BfS Bundes-Aggregat | TEILWEISE — „nur Übersicht ohne Rechtskraft" | `imis.bfs.de/cgi-public/wms_geoportal` |

**Implementation:** `radon_data.py` mit Per-State-Dispatcher. Sachsen kann sofort gehen (verifiziert), Pattern für NI-AGS-Workaround als zweiter Schritt, BY/ST/TH brauchen je 30–60 min Geoportal-Klick-Klärung.

**Akzeptanz:** Sachsen-Adressen sehen echten Radon-Status; andere BL: ehrlich „nicht öffentlich abrufbar, Auskunft beim Landesumweltamt".

---

### D.3 — Erdbebenzonen DIN EN 1998-1/NA

**Status:** **DIN-Urheberrecht blockiert** (siehe `docs/DATA_SOURCES_VERIFIED.md` Layer 3).

GFZ Potsdam hat keine maschinenlesbare API, nur Web-Form Adress-Lookups. DIN-Norm ist als Lizenz-Anhang geschützt: „reproduction is only permitted for authorized persons for scientific and non-commercial use".

**Aktion:** Mail-Anfrage `MAIL_GFZ_ERDBEBEN.md` an GFZ → ggf. an DIN-Verlag. Antwort kann „kostenpflichtig per DIN-Verlag" sein → dann technisch nicht in dieses Produkt integrierbar.

**Fallback:** Im Bericht als „Hinweis-Layer" mit Link auf das GFZ-Webtool führen — nicht als integrierter Wert.

---

### D.4 — Altlastenkataster pro BL

**Status:** **INSPIRE Art 13(1)(f) geschützt** (personenbezogen).

LUBW ALTIS (BW) und LANUV FIS AlBo (NRW) haben **keine** öffentlichen WFS — Anfrage nur per Behördenmail. Gleich für alle anderen BL.

**Bestehende Lösung im Code:** `altlasten_data.py` liefert für DE einen CORINE-Land-Use-Proxy (Codes 121/122/123/124/131/132/133 als Industrie-/Bergbau-/Deponie-Indikator) plus den PDF-Hinweis-Block „Rechtsverbindliche Behördenauskunft anfordern → altlasten@geoforensic.de".

**Phase-D-Aktion:** Kein neues Modul, sondern **Behörden-Vermittlungs-Service als Add-On** aufbauen — siehe Memory-Notiz „User-Idee 30.4.: Altlasten-Auskunft auf Anfrage". Eigener Geschäftsmodell-Sprint, nicht Daten-Sprint.

---

## 3. Reihenfolge

1. **D.1 Bergbau (priorisiert):** NRW läuft → BY/NI/SN/BW erweitern (4 große Bergbau-BL)
2. **D.2 Radon Sachsen** als ersten Pilot (verifizierte Quelle, schnell)
3. **D.2 Radon BY/NI/ST/TH** wenn D.1 stabil läuft
4. **D.3 Erdbeben:** Mail-Anfrage starten, dann je nach Antwort
5. **D.4 Altlasten-Vermittlungs-Service:** eigener Geschäftsmodell-Sprint, nicht hier

---

## 4. Was NICHT in Phase D gehört

- Visualisierungen — die kommen aus `VISUALS_ROLLOUT_PLAN.md`
- NL-i18n — eigene Phase
- Klimaprojektion 2050 (CMIP6 / ESDAC `Rfactor_2050_GPR.zip`) — Phase E falls relevant
- Stripe-Integration für Premium-Bestellung — Geschäftsmodell-Sprint

---

## 5. Aufwand-Klasse

Phase D ist **mehrere Wochen Engineering**, kein einzelner Sprint:
- D.1 Bergbau: pro BL 1–2 Tage Recherche + Modul-Erweiterung × 7 BL = 1–2 Wochen
- D.2 Radon Sachsen: 1 Tag, dann pro weiterer BL ähnlich
- D.3 Erdbeben: extern blockiert, kein eigener Aufwand
- D.4 Vermittlungs-Service: eigener Sprint, Vollmacht-Workflow + Bauamt-Beziehungen

Sinnvoll **nach Visuals-Sprint** zu starten — bringt Premium-Wert in der Tiefe und hebt das Konkurrenz-Argument gegen docestate (Behörden-Vermittlung) und gegen die regionalen Bauamt-Direktlösungen.
