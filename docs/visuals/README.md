# GeoForensic Visualisierungen — Übergabe-Paket

Dieses Verzeichnis enthält alles, was du brauchst, um die sechs GeoForensic-Visualisierungs-Komponenten zu implementieren — sowohl im PDF-Bericht (Backend) als auch auf der Webseite (Frontend) inklusive einer interaktiven Frontpage-Demo.

## Reihenfolge zum Lesen

1. **`SPEC_VISUALS.md`** — die vollständige Spec. Architektur, Tier-Logik, Akzeptanzkriterien, Spielraum-Bereiche.
2. **`data_contract.json`** — JSON-Schema. Welche Felder erwartet jede Komponente, was passiert bei fehlenden Daten.
3. **`example_payload.json`** — ausgefüllter Datenkontrakt für die Beispieladresse "Schulstraße 12, 76571 Gaggenau". Direkt zum Testen brauchbar.
4. **`reference_svgs/01_..._.svg` bis `06_..._.svg`** — die Design-Source-of-Truth. Eine SVG-Datei pro Komponente, mit Beispieldaten gefüllt. Genau so soll's aussehen.

## Was als Erstes umsetzen

In der Reihenfolge:

1. Eine geteilte Tokens-Datei (`shared/visual_tokens.json` oder `.ts`) — Farben und Schwellwerte aus Abschnitt 3 der Spec
2. Backend-Templates für die zwei Tier-1-Komponenten, die im Free-Report voll erscheinen: `risk_dashboard` und `property_context_map`
3. Backend-Teaser-Wrapper (Blur + Overlay) für die anderen vier
4. Backend-Templates für die vier Tier-2-Komponenten
5. Frontend-Komponenten parallel
6. Frontpage-Demo

## Bekannte Stolperfallen

- **WeasyPrint-Kompatibilität:** Die SVGs müssen ohne externe CSS-Variablen und ohne JavaScript funktionieren. Farben werden direkt im SVG hartkodiert oder per Jinja injiziert.
- **PSI-Punkt-Projektion:** Die Karte ist eine Schemaansicht, keine echte Slippy-Map. Echte Lat/Lon-Koordinaten müssen auf das ViewBox-Koordinatensystem projiziert werden. Vorschlag: einfache lokale Tangentialprojektion um den Adress-Centroid.
- **Daten-Lücken sind die Norm, nicht die Ausnahme.** Erwarte, dass für jeden zweiten Bericht mindestens eine Datenquelle fehlt. Die Akzeptanzkriterien in der Spec beschreiben das gewünschte Fehlerverhalten.

## Spielraum

Du entscheidest selbst über:
- Jinja-Pattern (Macros, Includes, Inheritance — was am besten passt)
- Genaues Format der Tokens-Datei
- React-State-Management
- Animation-Bibliothek für die Demo
- Test-Strategie

Du entscheidest **nicht** über:
- Die sechs Komponenten als solche
- Farbcodes und Akzentfarben
- Tier-Logik im Free-Report
- ViewBox-Breite 680px
- Datenkontrakt-Felder

## Bei Unklarheiten

Wenn etwas in der Spec mehrdeutig ist, lieber eine Annahme treffen, klar dokumentieren und weitermachen, als blockiert zu sein. Annahmen werden im Pull-Request-Beschreibungstext festgehalten und beim Review entschieden.
