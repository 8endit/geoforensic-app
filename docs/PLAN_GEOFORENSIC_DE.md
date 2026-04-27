# PLAN_GEOFORENSIC_DE.md — Vollversion + Paid-Flow Roadmap

Strategisches Dokument, nicht zeit-spezifisch. Für den Tages-Snapshot siehe
[`STATUS_2026-04-24.md`](STATUS_2026-04-24.md).

Zweck: Grundlage für Team-Gespräche, Freelancer-Briefings (Designer,
Frontender) und Investment-Entscheidungen. Wird erweitert, wenn Phasen
abgeschlossen werden oder sich Marktannahmen ändern.

---

## 1. Ausgangslage

Zwei Produkte, ein Repo:

- **bodenbericht.de** — kostenloser Lead-Magnet mit Teaser-PDF, läuft live
- **geoforensic.de** — geplantes kostenpflichtiges Produkt im
  Groundsure-Stil, noch nicht gebaut

Unser Markt-Kontext (aus `CLAUDE.md`, hier nochmal komprimiert):

| Wettbewerb | Land | Preis | Stärke | Schwäche |
|---|---|---|---|---|
| FunderConsult | NL | 7,95 EUR | etabliert, KCAF-Anbindung | Black-Box-Label A–E, keine Rohdaten |
| Groundsure | UK | 47 GBP+ | Marktführer, große Datenbasis | UK-only |
| France-ERP | FR | 9,99 EUR | beweist, dass Paid + kostenlos koexistieren | frankophon |
| BBSR GIS-ImmoRisk | DE | gratis (staatlich) | Hitze/Erdbeben/Waldbrand/Hagel/Sturm/Starkregen pro Adresse | reine Naturgefahren, keine Bodenbewegung, keine Altlasten |
| K.A.R.L.® TAXO (Köln.Assekuranz / on-geo) | DE | B2B Enterprise | Klimarisiko + EU-Taxonomie, CMIP6 | B2B-only, modelliert nicht gemessen |
| on-geo Lora | DE | B2B-Software | 95 % der DE-Banken | Beleihungswert, kein Käufer-PDF |
| EnviroTrust | DE | B2B | Climate-Risk-Plattform | B2B-only |
| docestate.com | DE | 30–100 EUR | Altlastenkataster pro Grundstück | landesspezifisch, teuer |

**Korrektur 2026-04-27:** Frühere Versionen dieses Docs hatten „keine | DE
| — | — | Chance für uns" — das war ein Recherche-blinder Fleck. Volle
Recherche siehe [`MARKET_REALITY_DE_2026.md`](MARKET_REALITY_DE_2026.md).
Konsequenz: **Strategie-Entscheidung Avista-Parität vs.
Soil-Act/InSAR-Pivot ist offen** (siehe §7).

Unser Differenzierungspotenzial gegenüber Groundsure:

- **Transparente Datenansicht** — einzelne Messpunkte sichtbar, nicht nur
  ein Label
- **Mehrsprachig von Anfang an** (NL primär, DE sekundär, EN optional)
- **Laiensprache** durchgehend (Groundsure ist für Anwälte geschrieben)
- **Niedrigerer Einstiegspreis** durch Europa-weite Datenstandardisierung
  (Copernicus gratis)

---

## 2. Zielmärkte und Priorität

### Priorität 1: Niederlande

Ab **1. April 2026** muss jede Dutch property valuation (taxatierapport)
ein Foundation-Risk-Label A–E enthalten (Quelle: KCAF/FunderMaps, über
MVRDV-konforme Taxateure). Käufer, die Label C/D/E bekommen, wollen
**verstehen, was das heißt** — das ist unsere Chance. Wir sind die
„Second Opinion" zum schlanken Pflicht-Label.

### Priorität 2: Deutschland

EU Soil Monitoring Directive 2025/2360 muss bis ~Dezember 2028
transponiert werden. Ab dann Käufer-Rechtsanspruch auf Bodendaten.
DE-Markt heute ohne vergleichbaren Wettbewerber — First-Mover-Vorteil,
aber der Markt läuft erst 2027/2028 an.

### Zeithorizont

- 2026 Q2–Q3: NL-Launch, minimaler Funktionsumfang + NL-Sprache
- 2026 Q4: DE-Launch volle Funktion, englische Variante
- 2027+: EU-weit skalieren, B2B-API-Zugang

---

## 3. Phasen-Plan

Jede Phase ist sequenziell abhängig von der vorherigen. Aufwand in
Arbeitstagen (AT), Personentage.

### Phase 1 — Paid-Flow aktivieren (ca. 2–3 Wochen)

Voraussetzung für alles andere. Ohne scharfen Bezahlweg gibt es kein
Produkt.

| Ticket | Was | AT |
|---|---|---|
| P1.1 | `full_report.py` an den Lead-Flow anbinden (heute Fallback auf Teaser) | 3–5 |
| P1.2 | Stripe-Konto scharf stellen, Webhook-Secret in Prod, Test-Checkout | 2 |
| P1.3 | Pricing final entscheiden und konfigurieren (Erwartung: 39–79 EUR) | 1 (Entscheidung Benjamin) |
| P1.4 | Rechnungs-PDF nach §14 UStG-konform | 2 |
| P1.5 | Widerrufsbelehrung mit digitaler-Inhalt-Ausnahme präzisieren | 1 (Anwalt oder Textmuster) |
| P1.6 | OSS-VAT-Registrierung für NL sobald 10k-EUR-Schwelle nahe kommt | 1 (Admin-Aufwand) |

Ende Phase 1: jemand kann auf der Landing seine Adresse eingeben,
29/39/79 EUR bezahlen und einen ordentlichen Vollbericht bekommen.

### Phase 2 — Daten-Parität zu Groundsure (ca. 4–6 Wochen)

Der Kern-Aufwand. Groundsure verkauft Risikolayer; wir haben heute einen
(Bodenbewegung). Für Parität müssen die folgenden Schichten dazu:

| Datenschicht | Status heute | AT bis live |
|---|---|---|
| Bodenbewegung EGMS | ✅ live | — |
| EGMS-Zeitreihen (Trend-Chart) | DB-leer, Code fertig | 1–2 (Import) |
| LUCAS Pestizide | Branch fertig, wartet auf xlsx-Upload | 0,5 nach Upload |
| HRL Imperviousness (Versiegelung) | Raster da, Code fehlt | 1 |
| SoilHydro AWC (Feldkapazität) | Raster da, Code fehlt | 1 |
| CORINE Land-Cover (Altnutzung) | Raster kaputt | 1 (neu ziehen + klippen) |
| BfG Hochwasser HWRM (HQ10/HQ100) | WMS verfügbar | 1–2 |
| BfS Radon-Vorsorgegebiete | WMS verfügbar | 1 |
| Bergbau / Altbergbau | nicht recherchiert | 2–3 |
| Bodenrichtwerte (Marktkontext) | nicht integriert | 1 |

Summe Phase 2: ca. 13–17 AT. Jede Schicht macht den Vollbericht spürbar
substantieller.

### Phase 3 — NL-Markt (ca. 2–3 Wochen)

| Ticket | Was | AT |
|---|---|---|
| P3.1 | PDF-Template auf Niederländisch (Template-Engine unterstützt i18n) | 3 (inkl. Übersetzungslektorat) |
| P3.2 | NL-Rechtshinweise: Zorgplicht, mededelingsplicht, taxatie-Bezug | 2 |
| P3.3 | KCAF/FunderMaps-Anbindung klären (API-Deal oder Fall-back) | 1–5 je nach Verhandlung |
| P3.4 | bodemdalingskaart.nl? — **NEIN**, CC-BY-SA ist Copyleft-Falle | 0 |
| P3.5 | Widerrufsbelehrung NL-konform | 1 (Textmuster) |

### Phase 4 — Professionelle Features (ca. 3–4 Wochen)

Was Groundsure funktional hat und wir heute nicht:

| Ticket | Was | AT | Nutzen |
|---|---|---|---|
| P4.1 | Worker-Queue (Redis + RQ), PDF-Rendering nicht mehr inline | 2 | Skaliert bei Lead-Spikes |
| P4.2 | API-Zugang für B2B-Kunden mit Keys + Quota | 3 | Makler, Notare, Gutachter-Kanzleien |
| P4.3 | Aktenzeichen-Feld (Fall-Bezug) | 0,5 | Wiedererkennbarkeit bei Mehrfach-Reports |
| P4.4 | Multiple Radien (100/500/1000 m) konfigurierbar | 1 | Präzision für Grundstücke, Umgebung, Region |
| P4.5 | Digitale PDF-Signatur / Zertifikat | 2 | Revisionssicherheit |
| P4.6 | Report-Versionierung (was bei Daten-Update?) | 3 | Rechtssicherheit bei zurückliegenden Reports |

### Phase 5 — Differenzierung (ca. 4 Wochen, laufend)

Da, wo wir besser werden als Groundsure.

| Ticket | Was | AT |
|---|---|---|
| P5.1 | Interaktive Karten statt PDF-Thumbnails (HTML-Report-Variante) | 5 |
| P5.2 | Zeitreihen-Grafik pro einzelnem Messpunkt (nicht nur Aggregat) | 3 |
| P5.3 | Nachbarschafts-Vergleich (Durchschnittswerte Straße/Gemeinde) | 3 |
| P5.4 | Handlungs-Empfehlungen mit Behörden-Ansprechpartner-Datenbank | 3 |
| P5.5 | Laiensprache-Modus vs. Fach-Modus umschaltbar | 2 |
| P5.6 | Mehrsprachigkeit NL/DE/EN i18n-Framework | 3 |

---

## 4. Daten-Strategie

### EGMS als Basis, BGR BBD als Zusatzlayer für DE

Heute nutzen wir ausschließlich EGMS (European Ground Motion Service,
Copernicus). EU-weit einheitlich, CC-BY-4.0-lizenziert, kommerziell
nutzbar. Typische Dichte: 50–80 Messpunkte pro 500-m-Radius in einer
deutschen Wohnsiedlung.

BGR BBD (Bodenbewegungsdienst Deutschland) liefert 80–120 Messpunkte pro
500-m-Radius für DE-Adressen und hat mit 2015–2024 eine längere
Zeitreihe. Lizenz nicht geklärt (Mail an `BBD@bgr.de` seit Wochen
unbeantwortet).

**Plan**: Hybrid-Ansatz für Phase 4+. Wenn BGR-Lizenz geklärt ist:
- Bei NL-Adressen: EGMS only (BGR deckt NL nicht ab)
- Bei DE-Adressen: EGMS-Basis + BGR zusätzlich, Report zeigt beide mit
  Hinweis auf die jeweilige Datenquelle
- Differentielles Setzen und Trendklassifikation aus dem Überschneidungsbereich

Für die Vollversion 1.0 reicht **EGMS allein** — das ist keine Ausrede
für Verzögerung der Paid-Flow-Aktivierung.

### Was wir **nicht** nutzen sollten

- `bodemdalingskaart.nl` — CC BY-SA ist Copyleft, würde unsere Reports
  zwingen ebenfalls offen zu lizenzieren → Geschäftsmodell kaputt

### Externe APIs (kommerziell, für später)

- **MapTiler** — Fallback für Static-Maps wenn OSM-Community-Service
  überlastet. Free-Tier: 100k Map-Loads/Monat (reicht bis ~3000
  Reports/Monat). Ab Phase 4 oder bei häufigen Map-Ausfällen.
- **Mapbox** — Alternative, teurer. Nur wenn MapTiler nicht reicht.

---

## 5. Geschäftsmodell

### Pricing (Vorschlag, nicht final)

Basierend auf Wettbewerbsvergleich:

| Markt | Preis | Begründung |
|---|---|---|
| NL B2C | 29–39 EUR | deutlich mehr als FunderConsult (7,95), aber „Second Opinion"-Positionierung rechtfertigt 4-5x |
| DE B2C | 49–79 EUR | kein direkter Wettbewerb, Baugrundgutachten-Alternative (849–2500 EUR) macht uns preiswert |
| B2B-API | 29 EUR pro Report, Mengenrabatt ab 10 / 50 / 200 | Makler, Notare, kleine Gutachter-Büros |

### Marge pro Report

Realistisch grob geschätzt:
- Satelliten-Daten: 0 EUR (Copernicus)
- Bodenproben-Daten: 0 EUR (LUCAS, SoilGrids)
- Server-Kosten: <0,05 EUR pro Report (Contabo flat)
- Mail-Versand: <0,01 EUR (Brevo)
- Stripe-Gebühr: 1,4 % + 0,25 EUR → bei 39 EUR rund 0,80 EUR
- Static-Map: 0 EUR (OSM) oder <0,001 EUR (MapTiler)
- Chrome-Rendering: nur CPU-Zeit auf Server

Marge pro Report bei 39 EUR Netto: ca. 37 EUR brutto. Kein Cogs-Problem,
Kosten skalieren praktisch linear nur mit dem Volumen.

### Rechtliche Struktur

- **Deutschland**: Gewerbeanmeldung (liegt bei Tepnosholding GmbH),
  Berufshaftpflichtversicherung ~150 EUR/Jahr
- **Niederlande**: Keine eigene Rechtspersönlichkeit nötig
  (EU-Dienstleistungsrichtlinie), OSS-VAT ab 10k EUR NL B2C-Umsatz

**Kein Gutachten** — wichtig: nirgends das Wort „Gutachten" verwenden.
Der Report ist ein **Standortscreening** / **Datenanalyse**. Steht so im
Disclaimer, steht in AGB, steht in CLAUDE.md als Dauer-Anweisung. Wer
das missachtet, öffnet die Haftung nach §18 BBodSchG.

---

## 6. Rollen und Aufgabenverteilung

### Claude (KI-Developer)

- Backend, Daten-Pipelines, API, DB-Schema
- Report-Engine (HTML-Templates, PDF-Rendering)
- Deployment-Automatisierung
- Admin-Tools und Diagnostik
- Dokumentation (dieses Dokument, CLAUDE.md, API-Doku)

### Cozy (Design-Partner)

- Visuelle Gestaltung der Landing geoforensic.de (Groundsure-Niveau)
- Bodenbericht.de Design-Polish
- PDF-Layout-Feinschliff
- Marketing-Grafiken für Social

### Benjamin

- Geschäftsentscheidungen (Pricing, NL/DE-Priorität, Daten-Lizenzen)
- Account-Verwaltung (Stripe, Sentry, MapTiler, BGR-Anfragen)
- Server-Zugang und Deploys
- Kundengespräche, Verhandlungen (FunderMaps-Anbindung, B2B-Pilotkunden)
- Soziale Kanäle und Lead-Generierung

### Freelancer (bei Bedarf)

- Frontend-Entwickler für aufwendigere Landing-Integrationen (z. B.
  interaktive Kartenkomponenten) — Claude bei reiner Integration ok,
  bei Design-Iteration nicht
- NL-Sprachlektorat für PDF und Landing
- Anwalt für Widerrufsbelehrung-Präzisierung, AGB-Review

---

## 7. Offene Entscheidungspunkte

Diese Fragen müssen beantwortet werden, bevor die entsprechende Phase
startet.

### Vor allem anderen — Strategie

- [ ] **Avista-Parität (Option A)** oder
      **Soil-Act + InSAR-Pivot (Option B)?** Volle Argumentation in
      [`MARKET_REALITY_DE_2026.md`](MARKET_REALITY_DE_2026.md) §4–§5.
      Bis zur Entscheidung: kein neues Risikomodul anfangen, keine
      neuen Daten-Lizenzen verhandeln. Phase-2-Datenliste unten ist
      Avista-Parität-Zustand und ggf. zu kürzen.

### Vor Phase 1

- [ ] Pricing: 29 oder 39 oder 49 EUR für NL-Launch?
- [ ] Ist Tepnosholding GmbH die richtige Rechtsperson für den
      Zahlungsempfang, oder soll eine neue Entity gegründet werden?

### Vor Phase 2

- [ ] BGR-Lizenz: Antwort von `BBD@bgr.de` erzwingen oder ohne
      weitermachen?
- [ ] LUCAS-Pestizid-xlsx auf dem Server hochladen — wann?
- [ ] CORINE-Lizenz (Copernicus Land Monitoring Service) prüfen
      (vermutlich CC BY 4.0, muss verifiziert werden)

### Vor Phase 3

- [ ] FunderMaps / KCAF: eigener API-Deal versuchen, oder mit
      open-data-Alternativen arbeiten?
- [ ] NL-spezifische Domain (`geoforensic.nl`?) oder mit
      `geoforensic.de/nl` arbeiten?

### Vor Phase 4

- [ ] B2B-Zielgruppe: Makler, Notare, Gutachter, alle drei?
      Vertriebsweg?
- [ ] Redis als Service hosten oder lokal am VPS betreiben?

### Vor Phase 5

- [ ] Interaktiver HTML-Report als separates Format oder ersetzt es
      PDF? (B2B will PDF, B2C findet interaktiv spannender)

---

## 8. Was das MVP für den Launch ist

Absoluter Minimal-Umfang, um `geoforensic.de` live zu schalten:

- ✅ Teaser-Report läuft (als Lead-Magnet weiter)
- ☐ Vollbericht mit 2 zusätzlichen Schichten über Teaser: EGMS-Zeitreihe
  + Schwermetalle aus LUCAS
- ☐ Stripe-Checkout live
- ☐ Pricing festgelegt und in Config
- ☐ Eigene geoforensic.de-Landing (Cozy-Design)
- ☐ AGB und Widerrufsbelehrung präzisiert
- ☐ Rechnungs-PDF automatisch
- ☐ mindestens 5 Test-Käufe ohne Bugs

Das ist Phase 1 komplett plus die zwei einfachsten Items aus Phase 2.
Realistisch ca. 3 Wochen Claude-Arbeit plus 2 Wochen Cozy-Design
parallel.

---

*Dieses Dokument wird versioniert. Bei größeren Änderungen — neue Phase
abgeschlossen, Pricing entschieden, neue Daten-Lizenz geklärt — im Commit
klar kennzeichnen.*
