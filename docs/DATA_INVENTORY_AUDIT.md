# Daten-Inventur Audit — April 2026

**Kontext:** Stand-Aufnahme vor Phase-1-Integration. Welche Raster auf
`F:\jarvis-eye-data\geoforensic-rasters\` sind wirklich nutzbar, welche sind
kaputt, welche bringen nur DE-Coverage und müssen für NL ergänzt werden.

**Test-Methode:** Jeder Raster an drei Referenz-Koordinaten gesampelt
(Marienplatz München, Berlin Mitte, Rotterdam) und auf CRS, Bounds, Werte
geprüft.

---

## Ergebnis-Tabelle

| Datei | Status | Marienplatz | Berlin | Rotterdam | Notiz |
|---|---|---|---|---|---|
| `corine_2024_100m.tif` | ❌ **KAPUTT** | – | – | – | Kein CRS, keine Geotransform, nur RGB-Bild (4 Kanäle uint8) ohne Georeferenz. **Muss neu besorgt werden.** |
| `hrl_imperviousness_20m.tif` | ✅ DE-only | 100 (versiegelt) | 100 (versiegelt) | außerhalb | Bounds 5.8–15.1°E, 45.4–57.0°N — deckt nur DE ab. Für NL separate Quelle nötig. |
| `soilhydro_awc_0-30cm.tif` | ✅ DE-only | 18 mm | 7 mm | außerhalb | Bounds 5.8–15.1°E, 47.2–55.2°N — DE-only. |
| `soilgrids_*_0-30cm.tif` (DE) | ⚠️ veraltet? | 0 (→ Nachbar-Fallback) | 0 | außerhalb | Alte DE-only-Version. Neue `_nlde`-Version wird bevorzugt geladen, falls vorhanden. **Zu prüfen ob alte Version weg kann.** |
| `soilgrids_*_0-30cm_nlde.tif` | ✅ DE+NL | — (nicht separat getestet, aber im Produktiv-Report genutzt) | — | sollte vorhanden | Die aktiv genutzte Version im Report. |
| `lucas_soil_de.csv` | ✅ | — | — | — | CSV mit ~3000 DE-Punkten, im Report integriert. |
| `lucas_pesticides_nuts2.xlsx` | ⚠️ nicht integriert | — | — | — | 118 Substanzen auf NUTS2-Ebene, liegt unangerührt. |

---

## Kritische Erkenntnis: CORINE-Datei ist kein CORINE

Die Datei `corine_2024_100m.tif` ist **kein Geo-Raster**, sondern ein normales
RGB-Bild im TIFF-Format:

```
CRS: None
Bounds: (0, 4000) bis (3000, 0)  ← Pixel-Koordinaten, nicht WGS84
Resolution: (1.0, 1.0)           ← 1 Pixel pro Einheit
Shape: (4000, 3000)
Bands: 4 × uint8                 ← RGB + Alpha
Dominant value: 253              ← Hintergrund-Grau
Tags: (leer)
```

**Wahrscheinliche Ursache:** Jemand hat ein Screenshot / PNG als GeoTIFF
exportiert ohne Geoinformation. Die Datei ist ~5 MB groß, was viel zu klein
wäre für ein echtes CORINE-Raster DE bei 100m-Auflösung (sollte ~50-100 MB sein).

**Auswirkung:** Die CORINE-Klassifizierung in `backend/app/soil_data.py`
(Zeilen 41-58, `CLC_LABELS` + `CLC_RISK_CODES`) ist **reines Wunschdenken** —
sie liest aus einer Datei die keine gültigen Landnutzungs-Codes enthält.

**Gut zu wissen:** Die Funktion wird aktuell im Report **nicht** aufgerufen —
kein Bug im Produktiv-System, nur ungenutzter Code. Wenn CORINE echt integriert
werden soll, muss die Datei neu besorgt werden.

---

## Wie echtes CORINE besorgen

Da CLC2024 erst **Mitte 2026 released** wird (Copernicus-Timeline), nutze
**CLC2018** als aktuelle valide Version.

**Bezugsquellen:**
1. **Copernicus Land Monitoring Service (offiziell):**
   `https://land.copernicus.eu/en/products/corine-land-cover/clc2018`
   Registrierung kostenlos, Download als GeoTIFF-Raster oder Shapefile.
   Lizenz: CC-BY 4.0, kommerziell OK.

2. **EEA Data Hub:**
   `https://www.eea.europa.eu/data-and-maps/data/copernicus-land-monitoring-service-corine`
   Gleiche Datei, ggf. einfachere Registrierung.

**Dateigröße erwarten:** ~500 MB für EU-weit bei 100m Auflösung, nach Clip auf
DE+NL Extent ~50-80 MB.

**Integrations-Aufwand:** 2-4 Stunden (Download + Clip + Test am selben
Pattern wie SoilGrids).

---

## NL-Coverage — was fehlt

Drei Raster decken aktuell **nur DE** ab:

| Datei | NL-Status | Alternative für NL |
|---|---|---|
| `hrl_imperviousness_20m.tif` | außerhalb | Copernicus HRL ist EU-weit verfügbar — muss nur für NL-Extent neu gezogen werden. Gleiche Quelle: CLMS HRL 2018 (IMD) oder 2021. |
| `soilhydro_awc_0-30cm.tif` | außerhalb | ESDAC European Soil Hydrology ist EU-weit, aber geliefert wurde anscheinend nur ein DE-Clip. Nachbesorgen. |
| `soilgrids_*_0-30cm.tif` | redundant | Hier haben wir bereits die `_nlde.tif`-Version — die alte DE-only-Version ist obsolet und kann nach Test gelöscht werden. |

**Empfehlung:** NL-Coverage für HRL + AWC nachziehen **bevor** Niederlande-Marketing
startet. Sonst zeigen NL-Reports Lücken.

---

## Funktionsfähige LUCAS-Pestizide (Integration ausstehend)

Die `lucas_pesticides_nuts2.xlsx` (207 KB, liegt seit 16.04. ungenutzt) enthält:

- 118 chemische Substanzen (Herbizide, Fungizide, Insektizide)
- Aggregation auf NUTS2-Ebene (Regionalebene, in DE sind das die
  Regierungsbezirke bzw. Bundesländer ohne RB)
- Basis: ESDAC LUCAS 2018 Pesticide Survey

**NUTS2 = grobe Auflösung.** Ein Wert pro z.B. "Oberbayern" oder "Ruhrgebiet".
Sagt nichts über einzelnes Grundstück, aber als **regionale Kontext-Indikation**
ist das brauchbar ("Ihre Region liegt im oberen Drittel der DE-Pestizid-
Belastung").

**Integrations-Aufwand:** 4-6 Stunden. Excel → Postgres-Tabelle,
NUTS2-Code-Lookup über Geocoder-Response oder eigener NUTS2-Geojson.

---

## Was als nächstes zu tun ist (priorisiert)

### Sofort (vor jedem Integration-Start)
1. **Echtes CORINE CLC2018 herunterladen und in `F:\jarvis-eye-data\geoforensic-rasters\`
   ablegen.** Alte kaputte `corine_2024_100m.tif` umbenennen zu
   `corine_2024_100m.tif.BROKEN` oder löschen.
2. **Dateiname-Konvention klären:** Soll echtes CLC2018 als `corine_2018_100m.tif`
   abgelegt werden? Code in `soil_data.py:210` hardcodet aktuell
   `"corine_2024_100m.tif"`.

### Phase 1a (Quick Wins, 1-2 Tage Gesamtaufwand)
3. **HRL Imperviousness im Report ausspielen** — neue Report-Sektion "Bebauungsgrad",
   Wert 0-100 als Prozent anzeigen. DE funktioniert, NL zeigt "außerhalb Coverage".
4. **SoilHydro AWC ergänzen** im bestehenden "Bodenqualität"-Abschnitt —
   zusätzliche Kennzahl "Wasserspeicherfähigkeit (mm)".
5. **LUCAS Pestizide integrieren** — Excel → SQLAlchemy-Tabelle,
   Nominatim-Antwort hat oft NUTS2 schon bei, sonst eigener Lookup.

### Phase 1b (Externe Quellen, 1-2 Wochen)
6. **Radon (BfS WMS)** — siehe `PHASE1_DATA_SOURCES_VERIFIED.md`
7. **Hochwasser (BfG HWRM)** — siehe gleiche Datei

### Parkplatz
- CORINE-Integration verschiebt sich nach hinten (braucht gesunde Datei zuerst)
- NL-Coverage für HRL+AWC: vor NL-Launch

---

## Offene Fragen

1. **Wer hatte die `corine_2024_100m.tif` ursprünglich erstellt?** Eventuell
   lag da schon ein Missverständnis zwischen "CLC2024" (= Version 2024, noch nicht
   released) und "Datei von 2024" (= Zeitpunkt des Downloads). Wenn wir Kontext
   haben warum die Datei so aussieht wie sie aussieht, ist der Replace
   einfacher.
2. **ISRIC SoilGrids — Lizenz-Attribution:** Im aktuellen Report als
   "ISRIC SoilGrids" attribuiert. Bei weiteren Datenquellen wird die
   Attribution-Liste länger — irgendwann sauber gruppieren statt Komma-Wüste.
3. **Alte DE-only SoilGrids-Dateien löschen?** Die `_nlde.tif`-Versionen werden
   bevorzugt geladen. Die alten DE-only-Dateien belegen ~50 MB ohne Nutzen.
   Aufräum-Entscheidung.
