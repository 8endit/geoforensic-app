# Grafik-Set fuer bodenbericht.de &mdash; v3

Vier SVG-Grafiken plus zwei Fotos. **Noch nicht in die echte Landing
eingebaut** &mdash; reine Preview. Die Preview-Seite liegt unter
`landing/_preview-graphics.html` und rendert ueber
`rawcdn.githack.com` ohne FastAPI-Mount.

## Das Set

| Datei | Rolle | Format |
|---|---|---|
| Hero-Foto (Bamberg) | Hero-Hintergrund &mdash; historische Altstadt | JPG, siehe `../photos/README.md` |
| `B-insar-map.svg` | Feature-Karte "Jeder Punkt einzeln gemessen" | SVG |
| `A-timeseries.svg` | Zeitreihen-Chart, 7 Jahre Bewegung an einem Punkt | SVG |
| `C-ampel.svg` | Dreistufige Klassifikation stabil / auffaellig / signifikant | SVG |
| `D-sources.svg` | Datenquellen-Stack (Copernicus, SoilGrids, LUCAS, OSM) | SVG |
| Waitlist-Foto (Sonnenuntergang) | Waitlist-Hintergrund | JPG, siehe `../photos/README.md` |

## Entwurfsgeschichte

- **v1** (commit 74a5c57): 4 SVGs 01-04, flach illustrativ
- **v2** (commit 0dde017): 4 SVGs 01-04, Groundsure-Style mit editorialer Zurueckhaltung
- **v3** (aktuell): 01, 03, 04 verworfen. 02 behalten (umbenannt zu `B-insar-map.svg`). Drei neue Daten-Grafiken (A, C, D), plus zwei Pexels-Fotos fuer Hero und Waitlist.

Grund fuer v3: v2-SVGs waren technisch sauber, aber das Set erzeugte insgesamt
zu viel SVG-Look. Echte Fotos an Hero + Waitlist erden das Ganze, die vier
SVGs dazwischen machen nur noch Daten-Arbeit.

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
