# Grafik-Entwurf fuer bodenbericht.de — v2

Vier SVG-Grafiken, neu gezeichnet nach Groundsure-Benchmark. **Noch nicht in
die Landing eingebaut** — reine Preview. Tap auf die `.svg`-Dateien in der
GitHub-App rendert sie inline.

## Designprinzipien (aus Recherche)

- **Editoriale Zurueckhaltung** — Whitespace, eine Hauptaussage pro Grafik,
  keine Icon-Cluster.
- **Erdige, gedeckte Palette** — Forest Green `#166534`, Warm Amber `#B45309`,
  Brick Red `#991B1B` statt gesaettigter Web-Primaries. `#22C55E` nur als
  CTA-Akzent (Scan-Strahl, Orbit-Highlight).
- **Kartografische Anmutung** — echte Strassen, Fluesse, Gebaeude-Polygone
  mit OS-artigem cremefarbenem Kartenhintergrund (`#F7F3EA`), nicht
  abstrakte Bloecke.
- **Konsistente Linienfuehrung** — 1.2-1.6px, 4px Rundungen, zwei Toene je
  Grafik.
- **Serif-Akzente** — Georgia fuer kleine editoriale Labels und Report-Titel
  (signalisiert Professional Services, nicht SaaS-Startup).

## Uebersicht

| Datei | Gedachter Einsatz | Hintergrund |
|---|---|---|
| `01-hero-satellite.svg` | Hero (neben/ueber der Headline) | **dunkel** (Navy Hero) |
| `02-insar-velocity-map.svg` | Feature-Karte "Bodenbewegungs-Screening" | weiss/cremefarben |
| `03-data-pipeline.svg` | "Automatische Datenanalyse"-Schritt | weiss |
| `04-waitlist-earth.svg` | Premium-Warteliste-Sektion | weiss / hellgruen |

Detail-Notizen:
- `01` hat topographische Konturlinien statt Raster, drei varierte
  Haeuser-Typen (freistehend, freistehend-Ziel, Mehrfamilien-Block),
  Sentinel-1 mit C-Band-Antenne und detaillierten Solarpanelen,
  Monospace-Caption "SENTINEL-1 · C-BAND · 2019-2023".
- `02` ist echt kartografisch: warmer Cream-Hintergrund, Fluss, Parks,
  Strassennetz, Gebaeude-Footprints unterschiedlicher Groesse, Grundstuecks-
  Polygon mit Pin in Forest Green. Massstabsleiste und Serif-Label
  "STADTMITTE · SEKTOR 3".
- `03` ist ein editorialer One-Shot: Satellit oben, elegante Datenlinie mit
  Paket-Markern, Serif-Caption "Copernicus · LUCAS · SoilGrids · Nominatim",
  dann ein detailreicher PDF-Mockup mit Navy-Header "BODENBERICHT", GeoScore-
  Gauge (85), Daten-Zeilen und Ampel-Chip.
- `04` ist atmosphaerisch: Erde mit Farbverlauf, Breitengrad- und Laengen-
  Konturen, pulsierende Staedte-Punkte (keine Haeuser mehr), Satellit auf
  Fade-Orbit, Serif-Label "Premium · in Entwicklung".

## Wenn Freigabe

Jede Grafik braucht nur ein `<img src="/images/graphics/XX.svg">` an der
gewuenschten Stelle. Kein Build, kein Tailwind-Change, kein Backend-Rebuild.
