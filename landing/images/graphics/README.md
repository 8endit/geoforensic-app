# Grafik-Set fuer bodenbericht.de &mdash; v3

Vier SVG-Grafiken plus zwei Fotos. **Noch nicht in die echte Landing
eingebaut** &mdash; reine Preview. Die Preview-Seite liegt unter
`landing/_preview-graphics.html` und rendert ueber
`rawcdn.githack.com` ohne FastAPI-Mount.

## Das Set

| Datei | Rolle | Format |
|---|---|---|
| Hero-Foto (Bamberg) | Hero-Hintergrund &mdash; historische Altstadt | JPG, siehe `../photos/README.md` |
| `B-insar-map.svg` | "Wir messen Ihr Haus" &mdash; ein Haus mit 4 Messpunkten | SVG |
| `A-timeseries.svg` | KPI-Story: &minus;22 mm Absenkung in 7 Jahren, Chart als Beleg | SVG |
| `C-ampel.svg` | Echte Verkehrsampel (stabil leuchtet), Stufen daneben | SVG |
| Datenquellen-Badges | Dezente Zeile im Footer-Bereich (nur HTML, kein SVG) | HTML |
| Waitlist-Foto (Sonnenuntergang) | Waitlist-Hintergrund | JPG, siehe `../photos/README.md` |

## Entwurfsgeschichte

- **v1** (commit 74a5c57): 4 SVGs 01-04, flach illustrativ
- **v2** (commit 0dde017): 4 SVGs 01-04, Groundsure-Style mit editorialer Zurueckhaltung
- **v3** (commit 28ebac4): 01, 03, 04 verworfen. 02 behalten (umbenannt zu `B-insar-map.svg`). Drei neue Daten-Grafiken (A, C, D), plus zwei Pexels-Fotos fuer Hero und Waitlist.
- **v4** (aktuell): A, B, C alle rework. D als SVG raus, ersetzt durch dezente HTML-Badge-Zeile.
  - A: Scatter-Zeitreihe &rarr; KPI-Story mit grosser Zahl &minus;22&nbsp;mm
  - B: abstrakte Stadtmitte &rarr; ein Haus im Zoom mit 4 Messpunkten drauf
  - C: Schema-Karte &rarr; echte Verkehrsampel-Metapher (stabil leuchtet)
  - D: Quellen-Stack-Grafik raus &rarr; dezente Badge-Zeile im Footer, keine Selbermach-Anleitung mehr

Grund fuer v4: v3-Set war technisch OK, aber Story pro SVG unklar
("nichtssagend") und D lud zum "das hol ich mir selbst"-Denken ein.

## Designprinzipien (gleich wie v2)

- **Editoriale Zurueckhaltung** &mdash; Whitespace, eine Hauptaussage pro Grafik
- **Erdige Palette** &mdash; Forest Green `#166534`, Warm Amber `#B45309`,
  Brick Red `#991B1B`, Cream `#F7F3EA`. Brand-Green `#22C55E` nur als
  CTA-Akzent
- **Serif-Akzente** &mdash; Georgia fuer editoriale Labels, Mono fuer Daten
- **Einheitlich 560 &times; 360** viewBox, `role="img"` + deutsches `aria-label`

## Detail-Notizen

- `A-timeseries.svg` &mdash; Scatter + Regressionsgerade, -10 bis +5 mm,
  Sentinel-1 Label, Trend-Annotation "-3,2 mm / Jahr", Schwellenwert-Banden
  in Gruen/Rot am Rand.
- `B-insar-map.svg` &mdash; Kartografisch, warmer Cream-Hintergrund, Fluss,
  Parks, Strassennetz, Gebaeude-Footprints, Grundstuecks-Polygon mit Pin.
  Massstabsleiste, Serif-Label "STADTMITTE / SEKTOR 3".
- `C-ampel.svg` &mdash; Drei Zeilen mit mm/a-Chips, Beschreibung und
  Beispiel-Dot-Cluster pro Stufe. Zeigt was man im eigenen Bericht zu
  sehen bekommt.
- `D-sources.svg` &mdash; Vier Quellen-Karten links, verbunden ueber feine
  Linien zu einem zentralen "Standort"-Pill. Serif-Caption zur Lizenzlage.

## Integration (wenn freigegeben)

- SVGs: `<img src="/images/graphics/A-timeseries.svg">` &mdash; kein Build noetig
- Fotos: siehe `../photos/README.md`. Vorher manuell runterladen (DSGVO).
- Die Preview-Seite `landing/_preview-graphics.html` ist preview-only und wird
  entweder auf lokale Foto-Pfade umgeschrieben oder geloescht, sobald das
  echte `landing/index.html` die Grafiken aufnimmt.
