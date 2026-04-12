# Report Design Brief — für Cozy

## Kontext

Das aktuelle PDF sieht aus wie ein Steuerformular. Weißer Hintergrund, Arial, klobige Tabelle.
Wir brauchen etwas das Leute öffnen und denken: "oh, das ist professionell."

Nicht überladen. Nicht Powerpoint. Eher: Bloomberg-Terminal trifft Copernicus-Satellitenbild.
Dein Design System, aber auf A4 Papier.

## Design System Referenz (aus CLAUDE.md)

- Background: `#000000` → für PDF: `#0A0A0A` (reines Schwarz druckt schlecht)
- Primary: `#22C55E` (Lime Green)
- Border: `#424242`
- Font Display: Sentient
- Font Mono: Geist Mono
- Farbige Elemente sparsam — das Grün soll leuchten, nicht schreien

## PDF-Aufbau — 3 Seiten

### Seite 1: Der Überblick ("Was ist das Ergebnis?")

```
┌──────────────────────────────────────────────┐
│                                              │
│  GEOFORENSIC              Standortauskunft   │
│  ──────────────── (grüne Linie) ──────────── │
│                                              │
│  ┌─────────────────────────────────────────┐ │
│  │                                         │ │
│  │         [ STATISCHE KARTE ]             │ │
│  │                                         │ │
│  │    Adress-Pin in der Mitte              │ │
│  │    500m Radius-Kreis                    │ │
│  │    Messpunkte als farbige Dots          │ │
│  │    (grün/gelb/rot je nach velocity)     │ │
│  │                                         │ │
│  └─────────────────────────────────────────┘ │
│                                              │
│  Musterstraße 5, 2801 JG Gouda, Nederland    │
│  52.0115° N  4.7105° E  ·  Radius 500m      │
│  12. April 2026                              │
│                                              │
│  ┌──────────┐  ┌────────┐  ┌──────────────┐ │
│  │          │  │        │  │              │ │
│  │   ████   │  │   78   │  │   -2.3       │ │
│  │   GELB   │  │ PUNKTE │  │   mm/Jahr    │ │
│  │          │  │        │  │  max. Absenkung│
│  └──────────┘  └────────┘  └──────────────┘ │
│                                              │
│  GeoScore: 68 / 100                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░  (Balken)  │
│                                              │
│  Bewertung: Auffällig — im Untersuchungs-    │
│  radius wurden erhöhte Bodenbewegungen       │
│  gemessen. Eine fachliche Einschätzung       │
│  wird empfohlen.                             │
│                                              │
└──────────────────────────────────────────────┘
```

**Elemente:**
- **Karte**: Statisches Kartenbild (OpenStreetMap-Tiles, generiert als PNG). Adress-Pin mittig, 500m-Kreis als grüne Umrandung, Messpunkte als farbige Punkte (Größe = Velocity). Das ist der Eye-Catcher.
- **Ampel-Badge**: Groß, farbig, links. Nicht "GRUEN" schreiben sondern "UNAUFFÄLLIG" / "AUFFÄLLIG" / "KRITISCH"
- **KPI-Karten**: 3 Karten nebeneinander — Messpunkte, Max. Absenkung, GeoScore
- **GeoScore-Balken**: Horizontaler Progress-Bar, grün→gelb→rot Gradient
- **Bewertungstext**: 2-3 Sätze, automatisch generiert basierend auf Ampel

**Wenn keine Daten (0 Punkte):**
- Karte trotzdem zeigen (nur Pin + Radius, keine Dots)
- Ampel: Grauer Badge "KEINE MESSDATEN"
- KPI-Karten: "—" statt Zahlen
- Text: "Für diesen Standort liegen im EGMS-Datensatz keine Messpunkte vor. Dies kann auf geringe Bebauungsdichte oder eingeschränkte Satellitenabdeckung zurückzuführen sein."

### Seite 2: Die Analyse ("Was sagen die Daten?")

```
┌──────────────────────────────────────────────┐
│                                              │
│  Geschwindigkeitsverteilung                  │
│                                              │
│  ┌─────────────────────────────────────────┐ │
│  │                                         │ │
│  │   ██████████████████████  38  (0-2)     │ │
│  │   ████████████           21  (2-5)      │ │
│  │   ██████                 11  (5-8)      │ │
│  │   ███                     6  (8-12)     │ │
│  │   █                       2  (12+)      │ │
│  │                                         │ │
│  │   Horizontales Balkendiagramm           │ │
│  │   Farben: grün → gelb → orange → rot    │ │
│  │   X-Achse: Anzahl Messpunkte            │ │
│  │   Y-Achse: Geschwindigkeitsklasse mm/a  │ │
│  │                                         │ │
│  └─────────────────────────────────────────┘ │
│                                              │
│  Statistik                                   │
│  ┌────────────┬────────────┬───────────────┐ │
│  │  Mittelwert│   Median   │  Gewichtet    │ │
│  │  1.8 mm/a  │  1.4 mm/a  │  2.3 mm/a    │ │
│  └────────────┴────────────┴───────────────┘ │
│                                              │
│  Standortvergleich                           │
│  ┌─────────────────────────────────────────┐ │
│  │                                         │ │
│  │  Ihr Standort  ▼ 2.3 mm/a              │ │
│  │  ──────────────────────────────────     │ │
│  │  Stadtdurchschnitt  ▼ 1.1 mm/a         │ │
│  │  ──────────────────────────────────     │ │
│  │  Landesweit  ▼ 0.8 mm/a                │ │
│  │                                         │ │
│  │  Einfacher Vergleichsbalken             │ │
│  │  "Ihr Standort liegt über dem           │ │
│  │   Durchschnitt der Stadt"               │ │
│  └─────────────────────────────────────────┘ │
│                                              │
│  Datenquelle & Methodik (klein, unten)       │
│  EGMS Ortho L3, Sentinel-1, 2019-2023       │
│  Vertikale Komponente, PSI-Verfahren        │
│                                              │
└──────────────────────────────────────────────┘
```

**Elemente:**
- **Histogram**: Horizontale Balken, Cozy-Farben (Primary Green → Gelb → Rot)
- **Statistik-Box**: Drei KPIs nebeneinander, Mono-Font, clean
- **Standortvergleich**: "Ihr Standort vs. Stadt vs. Land" — gibt dem Report einen Kontext. Die Vergleichswerte berechnen wir aus allen EGMS-Punkten in der jeweiligen Region
- **Methodik-Box**: Klein am unteren Rand, Mono-Font, gedämpfte Farbe

**Wenn keine Daten:** Diese Seite komplett weglassen. Report ist dann 2 Seiten.

### Seite 3: Die Messpunkte ("Die Rohdaten")

```
┌──────────────────────────────────────────────┐
│                                              │
│  Messpunkte im Untersuchungsradius           │
│  78 Punkte · sortiert nach Entfernung        │
│                                              │
│  ┌─────┬────────┬────────┬────────┬────────┐ │
│  │  #  │  Entf. │ Geschw.│  ●     │ Richt. │ │
│  ├─────┼────────┼────────┼────────┼────────┤ │
│  │  1  │  23m   │ -3.2   │  ██    │  ↓     │ │
│  │  2  │  45m   │ -1.8   │  █     │  ↓     │ │
│  │  3  │  67m   │ +0.3   │  ░     │  ↑     │ │
│  │  4  │  112m  │ -4.1   │  ███   │  ↓     │ │
│  │  ... │       │        │        │        │ │
│  └─────┴────────┴────────┴────────┴────────┘ │
│                                              │
│  ● Inline-Balken zeigt relative Stärke       │
│  ↓ = Absenkung  ↑ = Hebung                  │
│  Farbe des Balkens = Ampel-Farbe             │
│                                              │
│  ──────────────────────────────────────────  │
│                                              │
│  Hinweis: Diese Standortauskunft ist ein     │
│  automatisiertes Datenscreening [...]        │
│                                              │
│  Copernicus Attribution                      │
│  © GeoForensic 2026                          │
│                                              │
└──────────────────────────────────────────────┘
```

**Elemente:**
- **Tabelle**: Cleaner als jetzt — kein lat/lon (irrelevant für Käufer), stattdessen Entfernung + Geschwindigkeit + visueller Balken + Richtungspfeil
- **Inline-Balken**: Mini-Bargraph in jeder Zeile, zeigt relative Stärke
- **Richtung**: ↓ Absenkung (negativ), ↑ Hebung (positiv)
- **Max 30 Punkte** in der Tabelle, Rest als "und X weitere Punkte (siehe CSV-Export)"

**Wenn keine Daten:** Diese Seite weglassen.

---

## Farbschema für Ampel-Stufen

| Stufe | Farbe | Label (DE) | Label (NL) |
|-------|-------|------------|------------|
| Grün | `#22C55E` | Unauffällig | Geen bijzonderheden |
| Gelb | `#EAB308` | Auffällig | Let op |
| Rot | `#EF4444` | Kritisch | Significant risico |
| Grau | `#6B7280` | Keine Messdaten | Geen meetdata |

## Was es NICHT braucht

- Keine Koordinaten-Tabelle (lat/lon sagt einem Käufer nichts)
- Keine Coherence-Spalte (technisch, irrelevant für Endkunde)
- Keine JSON-Dumps
- Kein weißer Hintergrund (dunkles Theme = professioneller, hebt sich ab)
- Keine Logos von Copernicus/ESA (die Attribution reicht als Text)

## Technische Umsetzung

Der Report wird serverseitig als HTML → PDF generiert (WeasyPrint).
Cozy designt das HTML/CSS, Cursor baut die Daten-Logik ein.

Die Karte ist der schwierigste Teil — Optionen:
1. **Statische Karte via API**: Mapbox Static Images oder Stadia Maps (kostenlos bis 200k/mo)
2. **Matplotlib + contextily**: Python-generierte Karte mit OSM-Tiles als Background
3. **Leaflet Screenshot**: Headless Browser rendert Leaflet-Karte als PNG

Option 2 ist am einfachsten serverseitig ohne API-Key.

## Dateien die Cozy bekommt

- Dieses Briefing (`docs/REPORT_DESIGN_BRIEF.md`)
- Das aktuelle PDF zum Vergleich (was wir verbessern)
- Die CLAUDE.md mit dem Design System
- Freiheit beim Layout, aber die Sektionen-Reihenfolge beibehalten

## Was der Report bewirken soll

Ein Käufer der gerade "Label C" bekommen hat, öffnet das PDF und denkt:

1. Sekunde 1-3: "Oh, das sieht professionell aus" (Karte, dunkles Design)
2. Sekunde 3-5: "Okay, GELB — auffällig aber nicht dramatisch" (Ampel-Badge)
3. Sekunde 5-10: "78 Messpunkte, max -2.3 mm/Jahr" (KPI-Karten)
4. Sekunde 10-20: "Mein Standort ist über dem Durchschnitt" (Vergleich)
5. Danach: "Die Daten sehen solide aus, ich zeig das meinem Makler"

Das ist der Flow. Nicht mehr, nicht weniger.
