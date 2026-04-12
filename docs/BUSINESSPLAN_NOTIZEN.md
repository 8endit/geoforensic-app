# Businessplan-Notizen — GeoForensic

Kompiliert aus der gesamten Recherche vom 12. April 2026.
Alle Zahlen sind verifiziert (Quellen in den jeweiligen Recherche-Docs).

---

## 1. PROBLEM

### Niederlande (Erstmarkt)
- Seit 1. April 2026: jeder Taxatierapport muss Funderingsrisico-Label A-E enthalten
- 500.000+ Gebäude haben Fundamentprobleme
- Geschätzte Schadensvolumen: 50-60 Milliarden EUR
- Reparaturkosten pro Haus: 54.000-100.000+ EUR
- Nur ~1.000 Häuser werden pro Jahr repariert (massiver Rückstau)
- Fundamentschäden senken Immobilienwert um ~12% bei Bekanntwerden
- Versicherung deckt Fundamentschäden NICHT ab
- Das Problem: Käufer bekommt nur einen Buchstaben (A-E), keine Erklärung
- Der Score kommt erst IM Taxatierapport — also NACH dem Kaufvertrag (zu spät)

### Deutschland (ab 2028)
- EU Soil Monitoring Directive 2025/2360 muss bis Dezember 2028 umgesetzt werden
- Käufer/Mieter bekommen Recht auf Bodeninformationen
- Aktuell: NULL Anbieter für adressbasierte Bodenbewegungs-Reports
- Baugrundgutachten kosten 849-2.500 EUR (physische Bohrungen, dauert Wochen)
- Elementarschaden-Pflichtversicherung im Koalitionsvertrag (deckt Erdsenkung)
- Deutschland hat GEGEN die EU-Richtlinie gestimmt — aber muss trotzdem umsetzen
- Keine deutsche Firma positioniert sich kommerziell dafür

### Europa gesamt
- EGMS (European Ground Motion Service) deckt ganz Europa ab
- Kein Land außer UK hat einen adressbasierten Property-Risk-Report-Markt
- UK-Modell beweist: Groundsure wurde 2021 für 170 Mio GBP verkauft

---

## 2. LÖSUNG

Automatisierte, adressbasierte Bodenbewegungsscreenings ("Standortauskunft"):
- Adresse eingeben → Geocoding → EGMS-Satellitendaten abfragen → Report generieren
- Kostenlose Preview: Ampel + Punktanzahl (Lead-Magnet, kein Login nötig)
- Bezahlter Report: Karte, Zeitreihe, Histogram, Standortvergleich, PDF
- Keine Ortsbegehung, keine physische Inspektion — rein datenbasiert
- Sofortige Lieferung (Sekunden, nicht Wochen)

### Was der Report zeigt
- Bodenbewegung in mm/Jahr pro Messpunkt
- Statische Karte mit farbigen Messpunkten im 500m-Radius
- 7 Jahre Trend-Analyse (2019-2023, Sentinel-1)
- Nachbarvergleich (Standort vs. Stadt vs. Landesweit)
- Ampel-Klassifikation + GeoScore 0-100
- Velocity-Histogram (Verteilung der Geschwindigkeiten)

### Abgrenzung
- KEIN Gutachten (keine Haftung als Sachverständiger)
- KEIN Ersatz für physische Inspektion
- IST: Automatisierte Datenauskunft auf Basis öffentlicher EU-Satellitendaten
- Positionierung: "Die Erklärung NACH dem Label" / "Pre-Aankoop Screening"

---

## 3. MARKT

### TAM (Total Addressable Market)
- NL: 238.000 Transaktionen/Jahr × 39 EUR = 9,3 Mio EUR/Jahr
- DE: 700.000 Transaktionen/Jahr × 49 EUR = 34,3 Mio EUR/Jahr (ab 2028)
- Europa (EGMS-Abdeckung): 25+ Mio Transaktionen/Jahr

### SAM (Serviceable Addressable Market)
- NL: 238.000 × 30% in Risikogebieten × 39 EUR = 2,8 Mio EUR/Jahr
- DE: 700.000 × 20% Attach-Rate × 49 EUR = 6,9 Mio EUR/Jahr

### SOM (Serviceable Obtainable Market — realistisch Jahr 1-2)
- NL: 5% Attach-Rate in Risikogebieten = ~3.500 Reports × 39 EUR = ~137k EUR/Jahr
- Ziel Jahr 1: 100-200 Reports/Monat = 47k-94k EUR/Jahr

### Zusätzliche Revenue-Streams (später)
- B2B an Versicherer (Bulk-Risikoanalysen, 10k-100k EUR/Jahr pro Versicherer)
- B2B an Taxateur-Software (API-Integration, per-Query Pricing)
- B2B an Kommunen (Stadt-Reports, Asset-Management)
- Premium-Report mit Zeitreihen (wenn EGMS-Archivdaten integriert)

---

## 4. KONKURRENZ

### Direkte Konkurrenz
| Wer | Land | Preis | Was sie machen | Schwäche |
|-----|------|-------|----------------|----------|
| FunderConsult | NL | 7,95 EUR | A-E Label aus FunderMaps | Käufer sieht keine Daten, nur Label |
| Groundsure | UK | ab 47 GBP | Full Property Risk Report | Nicht in DE/NL aktiv |
| France-ERP | FR | 9,99 EUR | Risiko-Report neben free gov data | Nur Frankreich |
| Geobear | UK | Kostenlos (Checker) | Postcode-Checker + Sanierung | Kein Report, Upsell auf Bauarbeiten |

### Indirekte Konkurrenz
| Wer | Preis | Schwäche |
|-----|-------|----------|
| Baugrundgutachten (DE) | 849-2.500 EUR | Physisch, dauert Wochen, für Neubau nicht Kauf |
| QuickScan (NL) | 350-650 EUR | Physisch, dauert Tage |
| Bodemdalingskaart.nl | Kostenlos | Rohdaten, nicht adressgenau, keine Interpretation |
| EGMS Viewer | Kostenlos | Technisch, nicht consumer-tauglich |

### Warum wir gewinnen
- Einziger Anbieter der EU-Satellitendaten in einen consumer-tauglichen Report verpackt
- Pan-europäisch skalierbar (gleiche Datenquelle für alle Länder)
- Sofort verfügbar (Sekunden statt Tage/Wochen)
- 10-100x günstiger als physische Alternativen
- EGMS-Daten sind kostenlos (CC BY 4.0) — keine Datenkosten

---

## 5. GESCHÄFTSMODELL

### Revenue
- Pay-per-Report (One-Time Payment, kein Abo)
- NL: 29-49 EUR pro Report
- DE: 49-99 EUR pro Report (kein Wettbewerb, höhere Zahlungsbereitschaft)
- Kostenlose Preview als Lead-Magnet

### Kostenstruktur
- Server: Hetzner Cloud CX22, ~50 EUR/Monat (PostGIS + FastAPI + Next.js)
- Datenquelle: EGMS = 0 EUR (CC BY 4.0)
- Geocoding: Nominatim = 0 EUR (OpenStreetMap)
- Anwalt (AGB, Disclaimer): ~1.000-1.500 EUR einmalig
- Domain + Email: ~15 EUR/Jahr
- Berufshaftpflicht: ~150 EUR/Jahr
- Marketing: SEO-Content + Outreach (Zeitinvestment, kein Budget nötig)

### Unit Economics (pro Report)
- Serverkosten pro Report: ~0,01 EUR
- Datenkosten: 0 EUR
- Payment Processing (Stripe): ~2,5% + 0,25 EUR
- Marge bei 39 EUR Preis: ~37,75 EUR (>96%)

### Break-Even
- Fixkosten: ~200 EUR/Monat (Server + Versicherung + Domain)
- Break-Even: 6 Reports/Monat bei 39 EUR
- 100 Reports/Monat = ~3.800 EUR/Monat Gewinn

---

## 6. GO-TO-MARKET

### Phase 1: NL Launch (2026 Q2-Q3)
1. EGMS-Daten importieren (Cursor, in Arbeit)
2. Erster echter Test-Report generieren
3. Report-Design finalisieren (Cozy)
4. 10-20 kostenlose Reports an NL Makler verteilen
5. Pricing validieren (6 Makler bereits angeschrieben)
6. NL Landing Page (geoforensic.de/nl/)
7. SEO-Artikel auf Niederländisch (5-10 Artikel)
8. Live gehen

### Phase 2: NL Wachstum (2026 Q3-Q4)
- SEO-Traffic aufbauen ("funderingslabel C/D/E" Keywords)
- Expat-Communities (IamExpat, DutchNews)
- Makler-Partnerschaften (Provision pro empfohlenem Report)
- Journalisten kontaktieren (Cobouw, Vastgoedmarkt, EW Magazine)
- Erste 100 zahlende Kunden

### Phase 3: DE Vorbereitung (2027)
- BGR BBD-Daten integrieren (höhere Auflösung für DE)
- Deutsche SEO-Artikel vorbereiten
- B2B Kontakte zu Versicherern aufbauen
- AGB für deutschen Markt

### Phase 4: DE Launch (2028)
- EU Soil Directive greift
- Versicherer brauchen Risikodaten (Elementarschaden-Pflichtversicherung)
- First-Mover mit 2 Jahren NL-Erfahrung + Track Record
- B2B + B2C parallel

### Vertriebskanäle
| Kanal | Markt | Wie |
|-------|-------|-----|
| SEO | NL+DE | Artikel zu Funderingslabel, Bodenbewegung, Hauskauf |
| Makler-Empfehlung | NL | Provisionsmodell (5 EUR/empfohlener Report) |
| Expat-Communities | NL | IamExpat, DutchNews, Facebook-Gruppen |
| Journalisten | NL+DE | Cobouw, Vastgoedmarkt, EW Magazine |
| Versicherer (B2B) | DE | Direkt-Akquise ab 2027 |
| Taxateur-Software | NL | API-Integration in Realworks/Kolibri |

---

## 7. TEAM

- **[Dein Name]** — Informatiker, Backend-Entwicklung, Strategie, Daten-Pipeline
- **Cozy** — Mediengestalter, Frontend, UI/UX, Brand Design
- **AI-Assistenten** — Claude Code + Cursor für Entwicklung, Recherche, Code-Review
- **[Stefan]** — IT-Expertise, Business Development, Investoren-Netzwerk

### Was fehlt (Hiring/Partner ab Phase 2)
- Niederländisch-sprachiger Content Creator (für SEO-Artikel)
- Anwalt für AGB/Datenschutz (einmalig)
- Optional: Sales-Person für B2B Versicherer-Kanal (ab Phase 3)

---

## 8. TECHNOLOGIE

### Stack
- Frontend: Next.js 15 + React 19 + Tailwind CSS
- Backend: Python FastAPI + SQLAlchemy async + PostGIS
- Datenbank: PostgreSQL + PostGIS (Geodaten mit räumlichen Indizes)
- PDF: WeasyPrint (HTML → PDF serverseitig)
- Auth: JWT + bcrypt
- Payment: Stripe
- Hosting: Docker Compose, Ziel Hetzner Cloud
- Datenquelle: EGMS Ortho L3 (Copernicus, CC BY 4.0)

### Stand
- ✅ Prototyp funktioniert (Backend + Frontend + Auth + Stripe + PDF)
- ✅ Echte Pipeline (Nominatim Geocoding → PostGIS Query → Report)
- ✅ EGMS-Datenauflösung bestätigt (79 Punkte/500m in Städten)
- ✅ Import-Script fertig
- ⏳ EGMS-Daten noch nicht in DB importiert (Account steht)
- ⏳ Report-Design wird überarbeitet (Cozy)
- ⏳ UX/Security Fixes (Cursor)

### Technischer Moat
- Pipeline für EGMS-Datenverarbeitung + Adress-Auflösung
- Pan-europäische Skalierung (gleiche Datenquelle, gleiche Pipeline)
- Laufende Datenaktualisierung (Sentinel-1 Updates alle 6-12 Tage)
- Gewichteter Velocity-Score (proprietärer Algorithmus)

---

## 9. FINANZBEDARF

### Option A: Bootstrapped (0 EUR extern)
- Server: 50 EUR/Monat
- Anwalt: 1.500 EUR einmalig
- Domain + Email: 15 EUR/Jahr
- Versicherung: 150 EUR/Jahr
- = ~2.000 EUR Startkosten + 65 EUR/Monat laufend
- Break-Even bei 6 Reports/Monat

### Option B: Pre-Seed (15-30k EUR)
- 6 Monate Runway für NL-Launch
- Professionelle AGB + Datenschutz: 3.000 EUR
- Marketing-Budget (Google Ads Test): 2.000 EUR
- Server (12 Monate): 600 EUR
- Freelance NL-Content Creator: 3.000 EUR
- Puffer: 5.000 EUR
- Verwendung: Product-Market-Fit validieren, erste 100 Kunden

### Option C: Seed (50-150k EUR)
- 12-18 Monate Runway
- Teilzeit-Gehälter für Team
- B2B Sales-Person für Versicherer-Kanal
- Multi-Country Expansion (BE, AT, CH)
- Premium-Features (Zeitreihen, Prognosen)

### Investoren-Return-Szenario
- Jahr 1 (NL): 2.000 Reports × 39 EUR = 78k EUR
- Jahr 2 (NL+DE): 15.000 Reports × 45 EUR = 675k EUR
- Jahr 3 (Multi-Country): 50.000 Reports × 49 EUR = 2,45 Mio EUR
- Exit-Vergleich: Groundsure wurde für 170 Mio GBP verkauft bei ~20 Mio GBP Umsatz (8,5x Umsatz-Multiple)

---

## 10. RECHTLICHES

### Produkt-Positionierung
- "Standortauskunft" / "Bodenbewegungsscreening" — NIEMALS "Gutachten"
- Automatisiertes Datenscreening, kein Sachverständigen-Urteil
- Disclaimer ist rechtlich erforderlich und im PDF eingebaut

### Lizenzen
- Keine spezielle Lizenz nötig (normale Gewerbeanmeldung)
- EGMS: CC BY 4.0 (kommerziell OK, Attribution Pflicht)
- BGR BBD: Vermutlich dl-de/by-2.0 (Bestätigung ausstehend)

### Regulatorisches
- DE: Gewerbeanmeldung, AGB, Impressum, Datenschutzerklärung
- NL: Keine NL-Firma nötig (EU Dienstleistungsfreiheit), OSS-Umsatzsteuer
- DSGVO: Wir speichern Adress-Daten (Standorte, keine Personen) + User-Accounts
- Berufshaftpflicht empfohlen (~150 EUR/Jahr)

### IP
- Keine Patente nötig/möglich (InSAR-Methoden sind publiziert)
- Moat durch: laufende Datenverarbeitung + proprietäre Scoring-Algorithmen + Workflow-Integration
- Marke "GeoForensic" ggf. als Wortmarke schützen (DPMA, ~300 EUR)

---

## 11. RISIKEN

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| EGMS-Auflösung reicht nicht für ländliche Gebiete | Bestätigt | Mittel | Report nur für urbane Adressen, Warnung bei <20 Punkten |
| KCAF/SkyGeo baut Consumer-Report | Niedrig (2-4 Jahre) | Hoch | First-Mover-Vorteil, pan-europäisch, Speed of Innovation |
| EU Soil Directive wird in DE verwässert | Mittel | Mittel | NL-Markt als Absicherung, Versicherer-Kanal unabhängig von Regulierung |
| Bayern klagt erfolgreich vor EuGH | Sehr niedrig | Hoch | Betrifft DE, nicht NL; Versicherer-Kanal bleibt |
| Kein Product-Market-Fit in NL | Unbekannt | Hoch | Makler-Feedback läuft, kostenlose Test-Reports |
| Sentinel-1 Ausfall | Sehr niedrig | Hoch | Sentinel-1C seit Dez 2024 aktiv, ESA-Backup |

---

## 12. VISION — "Schufa für Häuser"

Langfristig: Der Standard-Risiko-Score den jeder abfragt bevor er eine Immobilie kauft, finanziert oder versichert. Wie die Schufa für Kreditwürdigkeit, aber für Bodenrisiko.

Kurzfristig: Consumer-Report der Satellitendaten verständlich macht.
Mittelfristig: API die Taxateure, Makler und Versicherer in ihren Workflow einbinden.
Langfristig: Pan-europäischer Standard, integriert in jede Immobilientransaktion.

Die EU Soil Directive 2025/2360 ist der regulatorische Katalysator der das möglich macht.
