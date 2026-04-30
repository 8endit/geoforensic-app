# GeoForensic Visualisierungen — Implementation Spec

**Status:** Bereit zur Umsetzung
**Zielgruppe:** Claude Code
**Bezug:** `geoforensic-app` Repository, Backend `full_report.py` / `html_report.py`, Frontend `bodenbericht.de`

---

## 1. Was gebaut wird

Sechs Visualisierungs-Komponenten, die im PDF-Bericht und auf der Webseite erscheinen. Sie sprechen ein einheitliches visuelles Vokabular und sollen Laien-Verständnis für komplexe Geodaten ermöglichen.

| # | Komponente | Tier | Free-Report | Premium-Report | Frontpage-Demo |
|---|---|---|---|---|---|
| 1 | Risiko-Dashboard | 1 | voll | voll | ja |
| 2 | Grundstück-im-Kontext (Karte) | 1 | voll | voll | ja |
| 3 | Velocity-Zeitreihe + Niederschlag | 1 | Teaser (verschwommen) | voll | ja |
| 4 | Bodenkontext-Stapel | 2 | Teaser (verschwommen) | voll | ja |
| 5 | Korrelations-Spinne | 2 | Teaser (verschwommen) | voll | ja |
| 6 | Nachbarschafts-Vergleich | 1 | Teaser (verschwommen) | voll | ja |

**Free-Report-Logik:** Dashboard und Karte voll sichtbar. Die anderen vier als verschwommene Vorschau mit Upgrade-Hinweis darüber. Das maximiert Conversion-Druck, ohne den Wert zu verstecken.

**Premium-Report:** Alle sechs voll sichtbar plus erweiterte Interpretationstexte.

**Frontpage-Demo:** Spielerischer Walkthrough mit Beispieladresse, in dem der Besucher Slider bewegt und sieht, wie sich die Grafiken anpassen.

---

## 2. Render-Strategie

### Backend (PDF-Bericht)

- **SVG-Templates mit Jinja2.** Eine Datei pro Komponente in `backend/templates/visuals/`.
- **Chrome Headless** rendert das HTML mit eingebetteten SVGs ins PDF (über bestehenden `pdf_renderer.py`).
- **WeasyPrint-Fallback:** Die SVGs müssen ohne JavaScript funktionieren und CSS-Variablen vermeiden — stattdessen Farben hartkodieren oder per Jinja injizieren.
- **Keine externen Abhängigkeiten** (keine CDN-Imports, keine Webfonts, die nicht eingebettet sind).
- **Schriften:** Sans-serif Standard. Wenn eine Custom-Font gewünscht ist, muss sie als Base64 ins SVG eingebettet werden.

### Frontend (Webseite und Demo)

- **React-Komponenten** in `frontend/src/components/visuals/`. Eine Komponente pro Visualisierung.
- **Selbe SVG-Struktur wie Backend**, aber als JSX. Props matchen die Felder im Daten-Kontrakt.
- **Interaktivität:** Hover-Effekte auf Datenpunkten, Tooltips mit Detailwerten. Bei Frontpage-Demo zusätzlich Slider zum Werte-Manipulieren.
- **Kein Zoom-Pan auf Karte in v1** — die Karte ist eine Schemaansicht, keine Slippy-Map. Falls eine echte Slippy-Map gewünscht wird, ist das ein Folge-Ticket mit MapLibre.

### Kritisch: Eine Quelle der Wahrheit

Die SVG-Markup-Struktur sollte zwischen Backend und Frontend so identisch wie möglich sein. Wenn ein Designer das Risiko-Dashboard im Backend ändert (z.B. neuer Schwellwert für Burland-Klasse), muss die Frontend-Variante mit minimalem Aufwand nachgezogen werden. **Empfehlung:** Eine geteilte Schema-Datei (z.B. `shared/visual_tokens.json`) mit Farben, Schriftgrößen, Schwellwerten, die beide Seiten lesen.

---

## 3. Visuelles Vokabular (verbindlich)

### Farbsystem

```
Ampel (Velocity / Risiko):
  stabil       (0 bis ±0.5 mm/J)   #1D9E75   c-teal-600
  leicht       (±0.5 bis ±1.5)     #5DCAA5   c-teal-400
  sehr leicht  (am Rand)           #9FE1CB   c-teal-200
  moderat      (±1.5 bis ±3.0)     #EF9F27   c-amber-400
  auffällig    (>±3.0)             #E24B4A   c-red-500
  kritisch     (>±5.0)             #A32D2D   c-red-700

Akzent:
  Eigenes Grundstück / Hervorhebung   #185FA5   Blau

Strukturfarben:
  Bebauung              #5F5E5A
  Versiegelung          #888780
  Mutterboden / SOC     #FAC775
  Lehm/Schluff          #EF9F27
  Verwitterung          #888780
  Festgestein           #444441
  Grundwasser           #185FA5 gestrichelt
  Niederschlag          #B5D4F4
  Trendlinie            #A32D2D gestrichelt
  PSI-Bewegung          #534AB7
```

### Typografie

- Sans-serif systemnah (`-apple-system, "Segoe UI", "Helvetica Neue", sans-serif`)
- 14px für Labels und Werte (`th` = medium 500)
- 12px für Achsen, Hilfstexte (`ts` = regular 400)
- 18-22px für Titel auf einzelnen Komponenten
- 48-64px nur für die Burland-Klasse-Zahl im Dashboard
- Sentence case durchgängig, kein ALL CAPS

### Layout-Prinzipien

- ViewBox-Breite konsistent **680px** für alle Komponenten (passend zu den bestehenden Wireframes)
- Höhe variiert je nach Komponente: Dashboard 260, Karte 480, Zeitreihe 320, Stapel 420, Spinne 440, Histogramm 280
- Innenabstand 20px zu den Rändern
- Akzentfarbe (Blau) nur für "Ihr Grundstück" reserviert — niemals für andere semantische Zwecke

---

## 4. Komponenten-Spezifikation

Für jede Komponente: Quelle (Reference-SVG), Datenfelder (siehe `data_contract.json`), Akzeptanzkriterien.

### 4.1 Risiko-Dashboard (`risk_dashboard`)

- **Reference:** `reference_svgs/01_risk_dashboard.svg`
- **Position im Bericht:** Erste Seite nach Deckblatt, voll sichtbar in beiden Tiers
- **Komponenten:**
  - Linker großer Block: Burland-Klasse als 64px-Zahl mit Beschreibungstext
  - Mittlere Spalte: 4 kleinere Boxen mit Velocity, Trend, Datenqualität, PSI-Punktdichte
  - Rechter großer Block: Schufa-Note (A-E) als gefüllter Kreis
- **Akzeptanzkriterien:**
  - Burland-Klasse-Hintergrund passt zur Klassen-Farbe (Klasse 0-1 = grün, 2-3 = gelb/orange, 4-6 = rot)
  - Schufa-Note-Kreis nutzt Ampelfarbe entsprechend Gesamtbewertung
  - Bei fehlenden Daten: Box wird mit "—" gefüllt, niemals leer; bei kritischen Lücken (z.B. <3 PSI-Punkte) Datenqualität auf "niedrig" und Hinweistext

### 4.2 Grundstück-im-Kontext (`property_context_map`)

- **Reference:** `reference_svgs/02_property_context_map.svg`
- **Position im Bericht:** Zweite Seite, voll sichtbar in beiden Tiers
- **Komponenten:**
  - Quadratische Schemakarte mit 500m-Radius-Kreis
  - PSI-Punkte als farbcodierte Kreise nach Velocity-Klasse
  - Hausumriss aus LoD2 als blauer Akzent-Rahmen mit Diagonalen
  - Legende unten mit allen Velocity-Klassen
- **Akzeptanzkriterien:**
  - Punkte werden so positioniert, dass sie nicht überlappen (Mindestabstand 8px); bei Überlappung wird der jüngere Punkt minimal verschoben
  - Hausumriss immer in der Mitte zentriert, in echter Maßstabsrelation zum Radius
  - Bei <10 PSI-Punkten Hinweis "Sparse Data" eingeblendet
  - Norden-Pfeil unten rechts

### 4.3 Velocity-Zeitreihe + Niederschlag (`velocity_timeseries`)

- **Reference:** `reference_svgs/03_velocity_timeseries.svg`
- **Position im Bericht:** Im Free als Teaser, im Premium voll
- **Komponenten:**
  - X-Achse: Zeit, mind. 60 Monate
  - Y-Achse links: Setzung in mm
  - Säulen: monatlicher Niederschlag in DWD-blau
  - Linie: PSI-Mittelwert in violett mit Datenpunkten
  - Trendlinie gestrichelt rot mit Beschriftung
- **Akzeptanzkriterien:**
  - Y-Achse zoomt automatisch auf Datenrange, mit 0-Linie immer sichtbar
  - Trendlinie wird per linearer Regression aus PSI-Werten berechnet
  - Wenn Niederschlagsdaten fehlen: Säulen weglassen, nur Linienplot zeigen, Hinweis im Footer
  - Korrelations-Koeffizient r wird im Footer angezeigt, falls beide Datenreihen vollständig

### 4.4 Bodenkontext-Stapel (`soil_context_stack`)

- **Reference:** `reference_svgs/04_soil_context_stack.svg`
- **Position im Bericht:** Premium voll, Free als Teaser
- **Komponenten:**
  - Vertikaler Querschnitt: Bebauung → Versiegelung → Mutterboden → Bodenart → Verwitterung → Festgestein
  - Tiefenachse links (0m bis -5m)
  - Grundwasserlinie als gestrichelte blaue Linie quer durch
  - Beschriftungen rechts mit Datenquelle in kleiner Schrift
- **Akzeptanzkriterien:**
  - Schichthöhen sind proportional zur tatsächlichen Tiefe
  - Bebauung-Block nur sichtbar wenn LoD2 verfügbar; sonst weglassen, andere Schichten skalieren
  - Grundwasserlinie kann fehlen — dann nicht zeichnen, Footer-Hinweis "Grundwasserstand nicht verfügbar"

### 4.5 Korrelations-Spinne (`correlation_radar`)

- **Reference:** `reference_svgs/05_correlation_radar.svg`
- **Position im Bericht:** Premium voll, Free als Teaser
- **Komponenten:**
  - 6-Achsen-Radar: Velocity, Niederschlag, Versiegelung, Quelltonanteil, Hangneigung, Grundwasser
  - 5 konzentrische Hexagons als Skala 0-5
  - Befüllte violette Fläche = Risikoprofil
  - Datenpunkte auf den Achsen mit Werten
  - Footer-Box mit interpretativem Text und r-Wert
- **Akzeptanzkriterien:**
  - Achsenwerte sind normiert auf 0-5 (Normierungsfunktion pro Achse in Code dokumentiert)
  - Stärkster Treiber wird im Footer namentlich genannt
  - Bei fehlender Achse (z.B. kein Quelltondaten): Achse zeigen aber mit "n/a" beschriften, kein Polygon-Punkt setzen

### 4.6 Nachbarschafts-Vergleich (`neighborhood_histogram`)

- **Reference:** `reference_svgs/06_neighborhood_histogram.svg`
- **Position im Bericht:** Premium voll, Free als Teaser
- **Komponenten:**
  - Histogramm der Velocity-Verteilung im 500m-Radius
  - X-Achse: Velocity in mm/Jahr (-5 bis +5)
  - Säulen-Höhe: Anzahl PSI-Punkte je Bin (1mm-Bins)
  - Marker für eigenes Grundstück mit Beschriftung
  - Footer-Text mit Perzentil-Einordnung
- **Akzeptanzkriterien:**
  - Säulenfarben folgen Ampel je nach Velocity-Wert
  - Eigenes-Grundstück-Marker steht über Histogramm, mit gestrichelter vertikaler Linie
  - Bei <20 PSI-Punkten in Umgebung: Hinweis "Stichprobe klein"

---

## 5. Free-Report Teaser-Logik

Für die vier Komponenten, die im Free-Report nur als Teaser erscheinen:

- SVG normal rendern, aber CSS-Filter `blur(8px)` plus reduzierte Opacity 60%
- Über die verschwommene Grafik einen halbtransparenten Layer mit Schloss-Icon und Text "Premium-Inhalt — Bericht freischalten für vollen Einblick"
- Klick auf Layer triggert Premium-Upgrade-Flow

Im PDF: gleicher Effekt mit SVG-Filter `feGaussianBlur`, kein interaktiver Klick aber Verweis-Text auf Upgrade-URL.

---

## 6. Frontpage-Demo (Spielerischer Walkthrough)

**Konzept:** Ein einseitiger interaktiver Bereich auf der Startseite, der Besuchern in 60-90 Sekunden zeigt, was sie bekommen.

**Beispieladresse:** Schulstraße 12, 76571 Gaggenau (vorgefertigt, statisch). Es ist klar als Demo gekennzeichnet.

**Ablauf:**
1. Besucher kommt auf die Seite, scrollt zur Demo-Sektion
2. Sieht Risiko-Dashboard mit Werten der Beispieladresse, daneben kurzer Erklärtext
3. Scrollt weiter, sieht Karte aufblühen mit Animation der Punkte
4. Bei Velocity-Zeitreihe: ein Slider erlaubt es, "was wäre wenn die Bewegung stärker wäre" durchzuspielen — die Linie verschiebt sich, die Burland-Klasse oben passt sich an
5. Bei Bodenkontext-Stapel: Hover über Schichten zeigt Detailtexte
6. Bei Korrelations-Spinne: ein Slider für Niederschlagsmenge, das Polygon verformt sich
7. Am Ende: "So sehen die Daten für Ihr Grundstück aus — Adresse eingeben"

**Technisch:**
- React-Komponenten, die State über Context teilen
- Animationen mit Framer Motion oder CSS-Transitions
- Keine echte Datenbank-Anbindung in der Demo, nur statische Beispieldaten
- Mobile-tauglich (alle Komponenten skalieren, Slider funktionieren auf Touch)

**Akzeptanzkriterien:**
- Demo lädt in <2 Sekunden auf 4G
- Funktioniert ohne JavaScript-Crash auf iOS Safari, Chrome Android, Firefox Desktop
- Slider sind erkennbar und beschriftet
- Demo-Charakter ist klar (Wasserzeichen "Demo" oder Banner "Beispiel-Grundstück")

---

## 7. Fehlerverhalten und Edge Cases

| Situation | Verhalten |
|---|---|
| Keine PSI-Punkte im Radius | Karte zeigt nur Hausumriss + Hinweis "Keine InSAR-Daten in diesem Gebiet". Andere Komponenten je nach Datenlage. |
| Weniger als 3 PSI-Punkte | Datenqualität "niedrig", Trend nicht berechnen, im Dashboard markieren. |
| Keine Niederschlagsdaten | Zeitreihe ohne Säulen, nur Linie. Korrelation nicht berechnen. |
| Keine Bodenkarten-Daten | Bodenkontext-Stapel weglassen, Hinweis im Bericht. |
| Geocoding fehlschlägt | Vor allen Visualisierungen abbrechen, Fehlermeldung an User. |
| Velocity > +5 mm/J (Hebung) | Eigene Farbe (z.B. lila), nicht in normales Ampelsystem zwängen. |

---

## 8. Reihenfolge der Umsetzung

1. **Geteilte Tokens-Datei** (`shared/visual_tokens.json`) — Farben, Schwellwerte, Schriftgrößen
2. **Backend-Templates** für Tier-1-Komponenten (Dashboard, Karte) zuerst — die müssen im Free-Report sofort funktionieren
3. **Backend-Teaser-Wrapper** (Blur + Overlay) für die anderen vier
4. **Backend-Templates** für Tier-2-Komponenten
5. **Frontend-Komponenten** parallel, sobald Tokens stehen
6. **Frontpage-Demo** als letzter Schritt, nutzt fertige Frontend-Komponenten

---

## 9. Spielraum für eigene Entscheidungen

Folgendes ist explizit Claude Codes Entscheidung:

- Welches Jinja-Pattern (Includes, Macros, Inheritance) am besten passt
- Wie die geteilten Tokens technisch realisiert sind (JSON, YAML, TS-Modul)
- Genaue Animation-Bibliothek für die Demo (Framer Motion, GSAP, oder CSS-only)
- Wie PSI-Punkte auf der Karte projiziert werden (Web Mercator, lokale Tangente, Schema-Layout)
- Component-State-Management im Frontend (Context, Zustand, lokal)
- Test-Strategie (Snapshot-Tests, Visual Regression, beides)

Folgendes ist nicht verhandelbar:

- Die sechs Komponenten existieren wie spezifiziert
- Farbcodes und Akzentfarben wie in Abschnitt 3
- Tier-1-vs-Tier-2-Trennung im Free-Report
- Datenfelder wie in `data_contract.json` definiert
- ViewBox-Breite 680px für PDF-Konsistenz

---

## 10. Anhänge

- `data_contract.json` — Schema pro Komponente
- `reference_svgs/01_risk_dashboard.svg` bis `06_neighborhood_histogram.svg` — Design-Source-of-Truth
- (Optional, falls zur Verfügung gestellt) Bestehende Wireframes als PNG für Designer-Review
