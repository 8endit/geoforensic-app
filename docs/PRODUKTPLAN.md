# Bodenbericht — High Level Produktplan

## Was ist das Produkt?

**Bodenbericht** ist ein automatisierter Standort-Risikobericht für Grundstücke in Deutschland und den Niederlanden. Der Nutzer gibt eine Adresse ein und erhält innerhalb von Minuten einen PDF-Report per Email — basierend auf öffentlichen EU-Satelliten- und Bodendaten.

**Das Produkt ist KEIN Gutachten.** Es ist ein datengetriebenes Screening das zeigt, ob an einem Standort Auffälligkeiten vorliegen. Für eine rechtsverbindliche Bewertung muss ein Sachverständiger hinzugezogen werden.

---

## Zielgruppen

### Primär (B2C)
| Zielgruppe | Schmerzpunkt | Zahlungsbereitschaft |
|---|---|---|
| **Hauskäufer** | "Ist das Grundstück sicher? Was ist im Boden?" | Hoch (Kaufpreis 200k-800k, Report ist Absicherung) |
| **Eigenheimbesitzer** | "Ist mein Garten kontaminiert? Kinder spielen dort" | Mittel (Gesundheitsangst) |
| **Landwirte** | "Wie ist meine Bodenqualität? Ertragssicherheit" | Mittel (wirtschaftliches Interesse) |

### Sekundär (B2B — Phase 2)
| Zielgruppe | Use Case |
|---|---|
| **Banken/Versicherungen** | Risikoprüfung bei Immobilienfinanzierung |
| **Immobilienmakler** | Mehrwert-Service für Verkäufer/Käufer |
| **Gutachter/Sachverständige** | Vorscreening vor Ortsbesichtigung |

---

## Was liefert der Report?

### Aktuell implementiert (v1)

| Section | Datenquelle | Abdeckung | Lizenz |
|---|---|---|---|
| **Bodenbewegung** (Setzung/Hebung) | Copernicus EGMS L3 Ortho (Sentinel-1) | NL komplett, DE noch nicht | CC BY 4.0 |
| **Schwermetalle** (Cd, Pb, Hg, As, Cr, Cu, Ni, Zn) | LUCAS Topsoil Survey (JRC) | DE: 3000 Punkte (7-15km Genauigkeit), NL: >50km → Warnung | Frei nach Antrag |
| **Bodenqualität** (pH, org. Kohlenstoff, Textur, Dichte) | SoilGrids 250m (ISRIC) | DE + NL komplett | CC BY 4.0 |
| **Nährstoffe** (Phosphor, Stickstoff) | LUCAS Topsoil | DE: ja, NL: eingeschränkt | Frei |
| **Pestizide** (118 Substanzen, NUTS2-Ebene) | LUCAS 2018 Pesticides (ESDAC) | DE + NL pro Region | Daten empfangen, noch nicht eingebaut |
| **Personalisierte Einschätzung** | Quiz-Antworten des Nutzers | — | — |

### Geplant (v2 — nächste 4-8 Wochen)

| Feature | Datenquelle | Aufwand |
|---|---|---|
| Hochwasser-Risikozonen | EU-Hochwasserrichtlinie WMS (PDOK NL, LUBW DE) | 2-3 Tage |
| Altlasten-Screening | NRW Open WFS, Bodemloket NL REST API | 2-3 Tage |
| Klimaprojektion | DWD (DE), Klimaateffectatlas (NL) | 1-2 Wochen |
| Radon-Vorsorgegebiet | BfS Radon-Karte (DE only) | 1 Tag |
| Funderingslabel-Kontext (NL) | PDOK BAG + BRO Bodemkaart | 1-2 Wochen |
| Karte im Report | Leaflet Static oder Matplotlib | 2 Tage |

### Langfristig (v3+)

- Zeitreihen-Charts (EGMS Displacement über 5 Jahre)
- Gebäudedaten (BAG NL / ALKIS DE)
- Bergbau-Altlasten (BGR, Landesbergämter)
- Premium-Tier mit namentlichem Gutachtertext

---

## Preismodell

### Phase 1: Pilotphase (jetzt)

| Angebot | Preis | Zweck |
|---|---|---|
| **Kostenloser Bericht** | 0 EUR | Lead-Generierung, Product-Market-Fit testen |
| **Email-Capture** | — | Quiz oder Direktformular → Report per Email |

**Ziel:** 100-500 kostenlose Reports verteilen, Feedback sammeln, Conversion messen.

### Phase 2: Monetarisierung

| Tier | Preis DE | Preis NL | Inhalt |
|---|---|---|---|
| **Basis-Screening** | 29-49 EUR | 19-29 EUR | Bodenbewegung + Bodenqualität + Schwermetalle |
| **Erweiterter Report** | 69-99 EUR | 39-59 EUR | + Hochwasser + Altlasten + Klimaprojektion |
| **Premium** | 149-199 EUR | 99-149 EUR | + Gutachter-Review + namentlicher Experte im PDF |

**Pricing-Logik:**
- NL günstiger weil FunderConsult dort 7.95 EUR nimmt (aber nur Label, kein Detail)
- DE teurer weil kein Wettbewerber (Baugrundgutachten kostet 849-2.500 EUR)
- Kostenstruktur: ~0.01 EUR/Report (EGMS frei, Nominatim frei, Server 6 EUR/Mo)
- Break-even bei 6 EUR/Mo Server: **1 Report/Monat bei 29 EUR**

### B2B-Preise (Phase 3)

| Modell | Preis |
|---|---|
| Batch (100+ Reports) | 15-25 EUR/Stück |
| API-Zugang (unlimited) | 500-1.500 EUR/Monat |
| White-Label | Individuell |

---

## Wettbewerb

| Anbieter | Markt | Preis | Was sie haben | Was wir besser können |
|---|---|---|---|---|
| **FunderConsult** (NL) | NL | 7.95 EUR | A-E Label (Blackbox) | Wir zeigen die echten Satellitendaten |
| **Groundsure** (UK) | UK | ab 47 GBP | Vollständiger Property Report | UK-only, nicht in DE/NL |
| **Avista** (NL) | NL/UK | ~100 EUR | Hochwasser, Altlasten, Klima | Wir haben InSAR + Bodenchemie |
| **Baugrundgutachten** (DE) | DE | 849-2.500 EUR | Physische Bohrung | Wir sind 10-50x günstiger |
| **Niemand** (DE) | DE | — | — | Wir sind First-Mover in DE |

---

## Technische Architektur

```
Landing Pages (systeme.io / statisch)
    ↓ POST /api/leads
FastAPI Backend (Docker, Contabo/Hetzner 6 EUR/Mo)
    ├── Geocoding (Nominatim)
    ├── EGMS Query (PostGIS, 3.25M NL Punkte)
    ├── SoilGrids Raster (pH, SOC, Textur)
    ├── LUCAS Metalle (KD-Tree Interpolation)
    ├── HTML Report → Chrome Headless → PDF
    └── Email (SMTP) → User
```

**Kosten pro Report:** ~0.01 EUR (kein externer API-Call nötig, alles lokal)

---

## Go-to-Market

### NL zuerst (Q2-Q3 2026)
- Seit 1.4.2026: Funderingslabel Pflicht bei jeder Immobilienbewertung
- 238.000 Immobilientransaktionen/Jahr
- Käufer die Label C/D/E bekommen wollen wissen WARUM → unser Report
- SEO-Keywords: "funderingslabel C", "bodembewegung check", "grondonderzoek"

### DE danach (2027-2028)
- EU Soil Monitoring Directive (2025/2360) → Umsetzung bis Dez 2028
- Kein Wettbewerber in DE
- Höhere Zahlungsbereitschaft (49-99 EUR)

---

## Team

| Person | Rolle |
|---|---|
| **Benjamin** | Produkt & Technik |
| **Domenico** | Backend & Infrastruktur |
| **Stefan** | Vertrieb & PM |
| **Gregor** | Marketing & Landing Pages |

---

## Nächste Schritte (Priorität)

1. **Server aufsetzen** (Contabo/Hetzner) + SMTP → Reports gehen live per Email
2. **100 kostenlose Reports verteilen** (NL + DE Testgruppe)
3. **Feedback sammeln** → Product-Market-Fit messen
4. **Gregor:** systeme.io Landing Pages live schalten
5. **Stefan:** 10 Pilotpartner ansprechen (5 Makler, 5 Banken BW)
6. **EGMS DE runterladen** → DE-Markt freischalten
7. **Hochwasser + Altlasten** einbauen (v2, +2-3 Wochen)
8. **Pricing einführen** wenn PMF bestätigt

---

*Erstellt: 16. April 2026 | Bodenbericht / GeoForensic*
