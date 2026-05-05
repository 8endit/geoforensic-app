# AUDIT — Vollbericht-PDF (2026-05-05, Mac-Session-Nacht)

**TL;DR:** Vollbericht ist aktuell nicht verkaufbar. Drei Klassen Probleme:
1. Daten-Bugs (kritisch) — Vollbericht widerspricht eigenem Teaser
2. Layout-Bugs (mittel) — 19 Seiten für ~10-Seiten-Inhalt, Block-Trennseiten verschwendet
3. Designsprache-Drift — Vollbericht und Teaser sehen aus wie zwei Produkte

Stockphotos sind im Repo nicht vorhanden, waren mal angedacht (Pexels), wurden im April-Cleanup wieder rausgeworfen.

---

## 1. Reproduktion / Test-Material

| | |
|---|---|
| Test-Lead-ID | `98a6b2b9-6e66-4d89-802d-404b365e5fa0` |
| Adresse | `Schulstraße 12, 76571 Gaggenau` (BW, Landkreis Rastatt) |
| Lat/Lon | `48.80436, 8.31568` |
| Vollbericht-Report-ID | `e13f5e68-bbef-4186-8d01-5f70750246cb` |
| Teaser-Report-ID | `ab87b5b5-3131-43b8-902c-478db2c56ea3` |
| Trigger | Mock-Mode Stripe-Checkout via `POST /api/payments/checkout-from-lead` |
| Mock-Lauf-Log-Excerpt | `app.routers.leads: Lead report sent ... (gruen, 76 pts, source=stripe, teaser=False, report_id=e13f5e68-...)` |

**PDFs liegen in der DB** (`reports.pdf_bytes`, bytea). Pull-Befehl:

```bash
ssh root@185.218.124.158 "cd /opt/bodenbericht && docker compose exec -T db \
  psql -U postgres -d geoforensic -tAc \
  \"SELECT encode(pdf_bytes, 'base64') FROM reports WHERE id = '<UUID>';\"" \
  > /tmp/report.b64
base64 -D -i /tmp/report.b64 -o /tmp/report.pdf
```

---

## 2. 🔴 Daten-Bugs (kritisch)

**Symptom:** Same address, same lead, same minute — Teaser und Vollbericht erzählen unterschiedliche Geschichten.

| Wert | Teaser sagt | Vollbericht sagt | Realität |
|---|---|---|---|
| EGMS Streupunkte (500 m) | **76 Punkte** | **0 Punkte** ("Sparse Data") | 76 (siehe Lead-Log) |
| Bewertung | grün · GeoScore 88/100 · "Unauffällig" | "—, nicht bewertbar, Datenlage zu dünn" | grün |
| Bewegungsverlauf | (im Teaser nicht im Detail) | "Keine Zeitreihe verfügbar — zu wenige Datenpunkte" | sollte 76 PSI haben → echte Zeitreihe |
| Hochwasser BfG | (im Teaser nur als Vollbericht-Teaser angekündigt) | "Hochwasserdaten am Standort nicht verfügbar. Wenn Ihre Adresse außerhalb Deutschlands liegt …" | Gaggenau IST in DE, BfG-WMS muss antworten |
| pH-Wert (Topsoil 0–30 cm) | (im Teaser nicht direkt sichtbar) | **`pH 0,6 SAUER`** | unmöglich (pH-Skala 0–14, real-Boden nie < 3,5) |
| Tonanteil / Sandanteil | — | `27 g/kg` Ton, `24 g/kg` Sand | unphysikalisch (Tonanteile sind in % oder g/kg vom Bodengewicht, müssten zusammen 100 % bzw 1000 g/kg ergeben) |
| Lagerungsdichte | — | `0,01 g/cm³ NORMAL` | unmöglich (echte Lagerungsdichte 0,9–1,8 g/cm³, 0,01 ist Aerogel) |
| SOC | — | `6,2 % HUMOS` | wahrscheinlich richtig oder Off-by-100 (typisch Mineralboden 0,5–4 %, Moorböden 6–60 %) |

### 2.1 PSI-Routing zwischen Teaser und Vollbericht inkonsistent

**Hypothese:** `backend/app/visual_payload.py` (was die Vollbericht-Visuals füttert) macht eigene EGMS-Query gegen PostGIS, fängt Failure-Modes nicht oder mit Default 0 ab. Teaser-Path läuft über `_compute_geo_score()` in `backend/app/routers/leads.py` der die Punkte korrekt zählt.

**Fix-Richtung:**
- `visual_payload.py`-Query gegen `_compute_geo_score()`-Quelle vergleichen
- Single-Source-of-Truth einbauen — beide Reports lesen aus dem gleichen `report_data`-JSONB-Snapshot, der EINMAL beim Lead-Insert gefüllt wird
- Auf jeden Fall: kein silent default 0 mehr, lieber explizit "Daten konnten nicht geladen werden" wenn EGMS-Query failt

### 2.2 SoilGrids-Werte mit falschen Einheiten

Mehrere Topsoil-Felder zeigen falsche Größenordnungen:
- `pH 0,6` — vermutlich SoilGrids liefert pH × 10 (also 6 wäre richtig); Conversion fehlt
- `Lagerungsdichte 0,01 g/cm³` — vermutlich SoilGrids liefert in cg/cm³ × 100 (also 1,0 wäre richtig)
- `Ton 27 g/kg / Sand 24 g/kg` — vermutlich SoilGrids liefert in g/kg, Werte stimmen — Schluff fehlt aber im Output (sollte als drittes Tile mit dabei sein, sonst Summe = 51 g/kg statt 1000)

**Fix-Richtung:** SoilGrids API-Doc nochmal checken (https://www.isric.org/explore/soilgrids/faq-soilgrids — Conversion-Faktoren sind dokumentiert pro Layer). Der Code in `backend/app/soil_data.py` ist verdächtig.

### 2.3 BfG Hochwasser-Query failt für DE-Adresse

`backend/app/flood_data.py` muss country=DE erkennen, BfG HWRM-WMS aufrufen, Result parsen. Vollbericht zeigt Fallback-Text "außerhalb Deutschlands" → entweder:
- Country-Detection liefert nicht "DE" zurück (Geocoding-Output falsch geparsed)
- WMS-Call timeoutet/failt und Fallback ist generisch
- Code-Pfad gar nicht erreicht weil falsche Bedingung

Smoke-Test im Container:
```bash
docker compose exec -T backend python -c "
import asyncio
from app.flood_data import query_flood
print(asyncio.run(query_flood(48.80436, 8.31568, 'DE')))
"
```

---

## 3. 🟡 Layout-Bugs (mittel)

19 Seiten Vollbericht für ~10 Seiten echten Inhalt. Drei Klassen Verschwendung:

### 3.1 Block-Trenner-Seiten

Seiten 2, 6, 8 sind reine **Trenn-Seiten** (~250 Zeichen Text):
- Seite 2: "BLOCK 01 · 3 SEKTIONEN — Bodenrisiken aus Satellit & Wetter — Sentinel-1 InSAR-Streupunkte, BfG Hochwasser-Szenarien und DWD-Starkregenstatistik. — BODENBEWEGUNG · STABIL HOCHWASSER STARKREGEN"
- Seite 6: analog für Block 02
- Seite 8: analog für Block 03

→ **3 Seiten verloren** für Inhalt der locker als Section-Untertitel auf Folge-Seite passt. Templates: `backend/templates/full_report/block_separator.html`.

### 3.2 Padding zwischen Tabellen-Tiles zu groß

Seite 5 (KOSTRA): 6 Niederschlags-Werte als 6 separate Big-Number-Tiles mit 90 % Whitespace pro Tile. Bei vergleichbarer Tabellen-Dichte wie Teaser käme das auf 1/3 der Höhe.

### 3.3 Sparse-Data-Sektionen verbrauchen volle Seite

Sektion 4 (Hochwasser): wegen BfG-Failure (siehe 2.3) Inhalt = 1 Satz "Daten nicht verfügbar". Verbraucht trotzdem ~halbe Seite mit Header + Datenquelle-Caption.

→ Wenn Sektion 0 nutzbare Daten hat: Mini-Karte (1/4 Seite) statt volle Sektion. Oder Section weglassen + im Cover/Übersicht als "—" markieren.

---

## 4. 🟡 Designsprache-Drift (mittel)

Teaser und Vollbericht sehen aus wie verschiedene Produkte:

| | Teaser (`html_report.py`) | Vollbericht (`full_report.py`) |
|---|---|---|
| Domain-Identität | bodenbericht.de (kalmer Tailwind, navy + brand-grün) | geoforensic.de (Cozy: schwarz + lime, mono-font) |
| Format | Card-Gitter, 13 Locked-Cards, klare Hierarchie | Block-Sektionen, große Trennseiten, Tabellen-fokussiert |
| Tipografie | Inter | Sentient + Geist Mono (inline embedded) |
| Seitenanzahl | 6 | 19 |
| Design-Prinzip | Locked Cards mit CTA "Vollbericht freischalten" | Linear-narrativ |

**Designentscheidung offen:** Soll Vollbericht der Cozy-Sprache (geoforensic.de) folgen oder Teaser-Sprache (bodenbericht.de)? Beide sind im Code parallel implementiert. Aktuell verkauft bodenbericht.de den Vollbericht — der Käufer würde aber die Cozy-Variante bekommen, was UX-mäßig einen Bruch zwischen Bestellprozess und Produkt erzeugt.

**Empfehlung:** Vollbericht stilistisch an Teaser angleichen solange er auf bodenbericht.de verkauft wird. Cozy-Variante als geoforensic.de-eigenes Produkt für später (B2B-Schiene).

---

## 5. 📷 Stockphoto-Status

**Geplant, nie deployed.** Git history zeigt:

| Commit | Datum | Was |
|---|---|---|
| `0abdda0` | 20.4 | `landing/images/photos/download.sh` + 2 Pexels-Foto-IDs hinzugefügt: `hero-german-town.jpg` (Pexels 3489009), `waitlist-aerial-sunset.jpg` (Pexels 1637080) |
| `5d0aac2` | 20.4 | `_preview-graphics.html` nutzt /images/photos/*.jpg lokal statt Pexels-Hotlink |
| `48fa408` | 20.4 | `landing: hero as tool mockup instead of stock photo` |
| `6f44d68` | 20.4 | `Revert "landing: hero as tool mockup instead of stock photo"` |
| `87de1cb` | 24.4 | `cleanup — remove orphan preview files + unused graphic assets` → ALLE Photo-Files raus |

Aktuell im Repo (`landing/images/`):
- og-image.png, logo-horizontal.png
- testimonials/markus.jpg + sandra.jpg + thomas.jpg

**Recovery wenn gewünscht** (5 min):

```bash
# 1. Verzeichnis + download.sh aus history reanimieren
mkdir -p landing/images/photos
git show 0abdda0:landing/images/photos/download.sh > landing/images/photos/download.sh
chmod +x landing/images/photos/download.sh

# 2. Photos einmal fetchen (lokal oder auf VPS — Pexels CDN hat keine Auth)
bash landing/images/photos/download.sh

# 3. Bilder in landing/index.html als Hero-Background oder Section-BG referenzieren
#    Beispiel: hinter Hero mit opacity:0.15 + dark gradient overlay
```

Pexels-Lizenz: free für commercial use, no attribution required (aber empfehlenswert).

---

## 6. Priorität

1. **2.1 PSI-Diskrepanz zwischen Teaser und Vollbericht fixen** — höchste Prio, macht Vollbericht aktuell unverkäuflich
2. **2.2 SoilGrids Unit-Conversions** — pH 0,6 ist im Käufer-PDF ein klarer "stimmt was nicht"-Trigger
3. **2.3 BfG-Hochwasser-Query smoke-test** — wenn das nur am Container-Layer-Setup hängt, schnell behoben
4. **3.1 Block-Trenner kürzen** — 3 Seiten weniger im Output, ~5 Min Template-Edit
5. **4 Designsprache-Entscheidung** — strategisch, später entscheiden
6. **5 Stockphotos** — nice-to-have, optional

---

## 7. Test-Material für nächste Session

Die generierten PDFs liegen lokal:
```
/tmp/vollbericht.pdf  (589 KB, 19 pages, e13f5e68)
/tmp/teaser.pdf       (2.4 MB, 6 pages, ab87b5b5)
```

Bei nächstem Session-Start neu ziehen weil `/tmp` zwischen Sessions/Reboots verloren geht — Pull-Befehl siehe §1.

Lead `98a6b2b9-...` lebt in der Prod-DB und ist beliebig oft via Mock-Stripe re-trigger-bar:

```bash
curl -s -X POST https://bodenbericht.de/api/payments/checkout-from-lead \
  -H 'Content-Type: application/json' \
  -d '{"lead_id":"98a6b2b9-6e66-4d89-802d-404b365e5fa0",
       "email":"benjaminweise41+banner@gmail.com",
       "address":"Schulstr 12, 76571 Gaggenau",
       "coupon":"EARLY50"}'
```
