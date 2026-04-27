# MARKET_REALITY_DE_2026.md — DE-Wettbewerbsrecherche, 2026-04-27

**Zweck:** Korrektur eines blinden Flecks in unseren Strategie-Docs.
Bisher stand in `CLAUDE.md`, `PLAN_GEOFORENSIC_DE.md` und
`DATA_SOURCES_GROUNDSURE_PARITY.md` durchgängig: *„Germany: No competitor
exists."* — das ist falsch. Dieses Dokument hält fest, was wirklich am
Markt ist, damit nicht jede neue Claude/Cursor-Session denselben Fehler
wiederholt.

**Stand der Recherche:** frisch, 2026-04-27. Keine Treffer im Repo für
`karl|on-geo|envirotrust|bbsr|gis-immorisk|lora` vor diesem Doc — der
einzige bisherige „on geo"-String war eine Floskel in
`backend/app/email_service.py`.

**Status:** Recherche-Snapshot. Strategieentscheidung (Avista-Parität vs.
Soil-Act/InSAR-Pivot) ist **offen** — siehe §6.

---

## 1. Wettbewerbslandschaft DE (real, nicht „leer")

| Wer | Was | Preis | Zielgruppe | Bedrohung für uns |
|---|---|---|---|---|
| **BBSR GIS-ImmoRisk** | Hitze, Erdbeben, Waldbrand, Hagel, Sturm, Starkregen pro Adresse DE | gratis, staatlich | jeder | **Hoch** — macht unser Naturgefahren-Modul kostenlos |
| **K.A.R.L.® TAXO** (Köln.Assekuranz, ERGO-Tochter, vermarktet via on-geo) | Klimarisiko + EU-Taxonomie-Compliance, CMIP6-Projektionen bis 2050 | B2B Enterprise | Asset Manager, Banken, Versicherer | Mittel — anderes Segment, aber Datenüberlapp |
| **on-geo Lora** | Beleihungswertermittlung | B2B-Software | 85 % aller Sparkassen, 95 % aller Banken DE | Hoch im Banken-Segment, aber **kein Käufer-PDF** |
| **EnviroTrust** | Climate-Risk-Plattform: Flut, Hitze, Sturm, Waldbrand, Luft | B2B | Asset Manager | Mittel |
| **docestate.com** | Altlastenkataster-Auskunft pro Grundstück | B2C, ~30–100 EUR | Käufer | Hoch im Altlasten-Segment |

**Konsequenz:** Die Aussage „kein Wettbewerb in DE" galt nur, wenn man
ausschließlich nach „Standortauskunft" gegoogelt hat. Wer nach
„Klimarisiko-Tool für Banken" oder „Altlastenkataster online" sucht,
findet einen belebten Markt — mit Lücken, aber nicht leer.

---

## 2. Regulierungs-Sog: Pflichtversicherung Elementar

- Im **Koalitionsvertrag 2025** verankert
- **Bundesrats-Vorstoß** liegt vor
- **Linke-Antrag 16.04.2026** im Verfahren
- **Noch nicht beschlossen.**

Geplantes Modell: **Opt-out**. Alle Wohngebäude-Policen müssen
Elementarschadenschutz enthalten; opt-out möglich, dann aber keine
Staatshilfe bei Schadensfall.

**Wenn das kommt → ~50 Versicherer in DE brauchen adressgenaue
Risikodaten zur Prämienkalkulation.** Das ist B2B-API-Geschäft, kein
B2C-PDF — aber der Markt-Pull ist gewaltig, und unser EGMS-Datensatz
(7,9 Mio. PSI-Punkte mit Zeitreihen, gemessen statt modelliert) ist
anschlussfähig.

---

## 3. Was die Wettbewerber **nicht** haben

Der einzige echte Moat, den wir heute identifizieren können:

| Layer | BBSR | K.A.R.L. | on-geo | EnviroTrust | docestate | Wir |
|---|---|---|---|---|---|---|
| InSAR-Bodenbewegung mit Zeitreihen | ❌ | nur modelliert | ❌ | ❌ | ❌ | ✅ EGMS, gemessen |
| EU-Soil-Directive-Compliance (Käufer-Sicht) | ❌ | EU-Taxo, B2B | ❌ | ❌ | ❌ | offen, aber Pole-Position möglich |
| Adressgenaue Naturgefahren (Rohdaten) | ✅ | ✅ | teilweise | ✅ | ❌ | über BBSR ingesten geplant |
| Naturgefahren mit **Käufer-Interpretation** | ❌ Web-Karte, Klassen-Werte | B2B-Reports | ❌ | B2B-Reports | ❌ | ✅ einziges B2C-PDF mit Story |
| Altlasten DE-weit, günstig | ❌ | ❌ | ❌ | ❌ | ✅ aber teuer | offen |
| Käufer-PDF mit Laiensprache | ❌ | ❌ | ❌ | ❌ | teilweise | ✅ Teaser läuft |
| Banken-Integration | ❌ | über on-geo | ✅ Marktführer | teilweise | ❌ | nein |

**Lesart:** K.A.R.L. nutzt Klimamodelle, BBSR nutzt aggregierte Karten,
on-geo macht Beleihungswert. Niemand der Großen kombiniert
**gemessene InSAR-Bodenbewegung + Käufer-PDF + Soil-Act-Compliance**.
Das ist die einzige glaubhafte Differenzierung.

---

## 4. Strategische Optionen

### Option A — „Avista-Parität" (Stefan-Vorschlag)

Sieben Risikomodule analog Avista bauen: Bodenbewegung, Hochwasser,
Radon, Altlasten, Bergbau, Erdbeben, Naturgefahren-Mix.

**Risiken:**
- BBSR liefert 6 davon **gratis** (Hitze, Erdbeben, Waldbrand, Hagel,
  Sturm, Starkregen) → der Käufer fragt: „Warum zahlen, wenn der Bund
  gratis liefert?"
- on-geo hat 95 % der Banken-Schiene zu — kein B2B-Hebel
- K.A.R.L. ist EU-Taxonomie-zertifiziert — kein Asset-Manager-Hebel
- Kopf-an-Kopf gegen 4 etablierte Player ohne Geld/Team → Selbstmord

### Option B — „Soil-Act + InSAR + BBSR-Interpretations-Layer" (gewählt 2026-04-27)

Schmaler positionieren auf zwei Achsen, die niemand sonst kombiniert:

1. **EU Soil Monitoring Directive 2025/2360** — DE muss bis
   **17.12.2028** transponieren. Käufer-Rechtsanspruch auf Bodendaten
   wird kommen. Niemand der Großen positioniert sich als
   „Soil-Directive-Compliance-Tool für Privatkäufer". **Weißer Fleck,
   regulierungsgetriebener Sog.**
2. **InSAR-Bodenbewegung mit Tiefe** — gemessene Zeitreihen pro
   Messpunkt, nicht aggregiertes Label. Einziger echter Moat.

**BBSR ist Datenquelle, nicht Wettbewerber — aber derzeit blockiert.**

Refinement nach Diskussion 2026-04-27: BBSR GIS-ImmoRisk liefert eine
staatliche Web-Karte mit Klassen-Werten („Hagelrisiko Klasse 3"), aber
**keine Käufer-Interpretation, keine Bündelung, kein PDF**. Das ist
exakt das France-ERP-Muster: kostenloses `georisques.gouv.fr` +
bezahltes 9,99-EUR-Bericht koexistieren, weil Bezahlbereitschaft aus
„verständlich machen, bündeln, Notar-tauglich" entsteht.

**Update nach Lizenz-Recherche 2026-04-27 (Web-Agent):** Die ursprüngliche
Annahme „BBSR per WMS ingesten" ist **so nicht haltbar**:

1. **Lizenz nicht öffentlich deklariert.** Weder im Footer der
   Web-Anwendung, noch in den Nutzungshinweisen, noch im
   GDI-DE-Katalog ist eine Lizenz für GIS-ImmoRisk angegeben.
   Drittdaten von GDV/Munich Re/DWD/KIT im Mix → die pauschale
   Annahme dl-de/by-2.0 wäre ein Rechtsrisiko.
2. **Kein Maschinen-Zugang.** Kein WMS, kein WFS, keine API.
   Suche im GDI-DE-Katalog nach „GIS-ImmoRisk" liefert null Treffer.
   Nur Web-Tool mit Adress-Suche, Ausgabe rein im Browser. Scraping
   rechtlich und technisch fragil.
3. **GeoNutzV greift nicht automatisch** — GeoNutzV deckt nur
   Geobasisdaten der Bundesverwaltung. GIS-ImmoRisk sind
   Geofachdaten aus einem Forschungsprojekt mit Verbund-Datenquellen.

**Aktueller Plan B-Refinement-2 (gilt jetzt):**

- **BBSR ist „blockiert".** Mail an `zentrale@bbr.bund.de` mit
  Lizenz-/Zugangs-Anfrage ist Voraussetzung
  (Vorlage: `docs/MAIL_BBSR_LIZENZ.md`). Bis schriftliche Antwort:
  weder ingesten noch verlinken.
- **Statt BBSR-Aggregat: direkte Quell-WMS** der Behörden, die BBSR
  ohnehin nutzt — DWD (Hitze, Starkregen), BGR (Erdbebenzonen). Mehr
  Code-Aufwand, aber lizenzsauber (alle GeoNutzV/dl-de).
- **Schnellster Win: BfG Hochwasser-WMS** — explizit GeoNutzV,
  kommerziell OK, INSPIRE-konform. Sofort startbar, siehe
  `docs/SPRINT_S1_DATA_INGEST.md`.
- **Altlasten** bleiben verschoben (BBodSchG-Datenschutz erlaubt
  keine flächendeckende automatisierte Auskunft; docestate-Modell
  ist Hybrid mit menschlichem Bearbeitungsschritt).

**Eigene Layer trotzdem nötig:**
- **Hochwasser** — BfG/Länder-WMS, präziser als BBSR-Aggregat
- **Radon** — BfS-Vorsorgegebiete (BBSR deckt nicht ab)
- **Bergbau** — landesspezifisch, BBSR deckt nicht ab
- **Altlasten** — docestate ist B2C, landesspezifisch und teuer
  (30–100 EUR pro BL) → echte Lücke für günstige DE-weite Lösung

**B2B-API als zweites Standbein vorbereiten:** sobald
Pflichtversicherung beschlossen wird, sind wir mit EGMS-Daten
anschlussfähig.

**Verkaufspfad-Klarstellung** (Antwort auf „lässt sich das sicher
verkaufen?"):

- **NL trägt 2026/2027:** Pflicht-Taxatie seit 1.4.2026 → Käufer mit
  Label C/D/E wollen verstehen → unser InSAR-Bericht ist die
  „Second Opinion". Das ist die unmittelbare Umsatzschiene.
- **DE 2026/2027:** B2B-Pilot (Makler, Notare, Gutachterbüros) +
  Bodenbewegung-Solo-Bericht für Bestandskäufer in Bergbau- und
  Subsidenz-Regionen. Soil-Act ist hier noch nicht das
  Verkaufsargument.
- **DE ab 2027/2028:** Soil-Act-Transposition wird Pflicht-Markt
  schaffen. Bis dahin sind wir mit Marke + Daten + B2B-Beziehungen in
  Pole-Position. Soil-Act ist Wachstumshebel, nicht Startbatterie.

---

## 5. Empfehlung (zur Diskussion, keine Entscheidung)

Option B trägt das geringere Risiko und nutzt unseren einzigen Moat.
Option A würde gegen vier etablierte Player gleichzeitig gefahren —
ohne entsprechendes Budget oder Teamstärke aussichtslos.

Argumente, die Option B stützen:

- **Avista-Parität** = 7 Module gegen 4 etablierte Anbieter. Wir
  verlieren auf jeder Achse (Preis, Datenzugang, Vertrieb).
- **EU Soil Act** = echter weißer Fleck, regulierungsgetriebener Sog
  bis Dez 2028, Pflicht-Markt statt Wunsch-Markt.
- **Pflichtversicherung Naturgefahren** = wenn Opt-out kommt, ist
  B2B-API-Pricing-Daten ein gewaltiger Sog. EGMS gibt uns dort einen
  echten Vorteil (gemessen, nicht modelliert).
- **EGMS-Bodenbewegung** = einziger echter Moat. Story bauen, nicht
  „wir sind das deutsche Avista".

**Aber:** das ist eine Geschäftsentscheidung, keine technische. Die
trifft Benjamin.

---

## 6. Strategie-Entscheidung — getroffen 2026-04-27

**Option B gewählt** mit Refinement: „Soil-Act + InSAR-Moat + BBSR als
Datenquelle für Naturgefahren mit eigener Interpretations-Schicht".

Begründung kurz:
- A scheitert an BBSR-Gratis + on-geo/K.A.R.L.-Marktbesetzung
- B nutzt einzigen Moat (gemessene InSAR-Tiefe) + regulatorischen Sog
  (Soil-Act 2028)
- Insight aus Diskussion: BBSR liefert Rohdaten, kein Produkt — wir
  können BBSR-Daten ingesten statt selbst sechs Layer zu bauen
  (France-ERP-Muster: gratis Behördenportal + bezahlter
  Interpretations-Bericht koexistieren)

Verbleibende offene Punkte zur Strategie:

- [ ] **BBSR-Lizenzanfrage rausschicken** —
      `docs/MAIL_BBSR_LIZENZ.md` an `zentrale@bbr.bund.de`. Recherche
      hat ergeben: Lizenz NICHT öffentlich deklariert, kein
      Maschinen-Zugang. Vor Antwort weder ingesten noch verlinken.
- [ ] Pricing für NL-Launch festlegen (Vorschlag 29–39 EUR; Phase-1
      des `PLAN_GEOFORENSIC_DE.md`)
- [ ] Daten-Layer-Reihenfolge festlegen — Vorschlag in
      `docs/SPRINT_S1_DATA_INGEST.md` §3 (BfG Hochwasser zuerst,
      sofort startbar)

---

## 7. Sofortige Hausaufgabe (egal welche Strategie)

- [x] Diesen Spec speichern (dieses Doc)
- [x] `CLAUDE.md` korrigieren — „No competitor exists" ist falsch
- [x] `PLAN_GEOFORENSIC_DE.md` korrigieren — Markttabelle aktualisiert
- [x] `DATA_SOURCES_GROUNDSURE_PARITY.md` korrigieren — Wettbewerbstabelle erweitert
- [x] Refinement nach Diskussion: BBSR als Datenquelle, nicht Wettbewerber
- [x] Strategie-Entscheidung dokumentiert: Option B gewählt

---

## 8. Konkrete nächste 2 Wochen — Sprint S1 + S2

Strategie B ist gesetzt. Vorgeschlagene Aufteilung:

### Sprint S1 (Woche 1) — „No-Regret + Paid-Flow scharf"

Alles, was unabhängig von BBSR-Lizenzklärung läuft und das Fundament
für Umsatz legt.

- [ ] Sentry DSN scharfschalten + Test-Crash verifizieren
- [ ] Better Stack Uptime-Pings auf bodenbericht.de + /api/health
- [ ] SSH Password-Login auf VPS abschalten (Handbook §2.2)
- [ ] `full_report.py` an Lead-Flow anbinden — Phase-1.1 aus
      `PLAN_GEOFORENSIC_DE.md`
- [ ] Stripe-Konto Live-Modus prüfen + Webhook-Secret in Prod
- [ ] BBSR-Lizenz-Recherche (parallel, niedrige Priorität): Mail an
      `info@bbsr.bund.de`, Web-Recherche dl-de/by-2.0 für GIS-ImmoRisk

### Sprint S2 (Woche 2) — „NRW Bergbau + KOSTRA + BfG-Verify"

Reihenfolge nach Live-Verifizierung 2026-04-27 angepasst — die
Verifikation hat ergeben, dass NRW Bergbau der einzige vollständig
verifizierte Layer ist, BfG Hochwasser noch einen Live-Capabilities-Test
vom VPS braucht. Details:
[`DATA_SOURCES_VERIFIED.md`](DATA_SOURCES_VERIFIED.md).

- [ ] **NRW Bergbau-WMS integrieren** — neues Modul `mining_nrw.py`,
      WMS GetFeatureInfo gegen `wms.nrw.de`, neuer Bericht-Abschnitt
      (nur für NRW-Adressen, sonst „nicht relevant")
- [ ] **DWD KOSTRA Download-Pipeline** — ASCII-Raster ziehen,
      konvertieren zu GeoTIFF, in `RASTER_DIR` legen, neues Modul
      `kostra_data.py` für Punkt-Lookup
- [ ] **BfG HWRM Live-Verify vom VPS** — Capabilities + Layer-Namen
      + AccessConstraints lesen, danach `flood_data.py`-Modul bauen
- [ ] PDF-Template-i18n-Skelett (NL-Strings noch leer, Engine bereit)
- [ ] NL-Sprachlektorat anfragen (Freelancer-Briefing schreiben)
- [ ] Outreach-Mail an erste 5 NL-Taxateure für Pilot-Reports
- [ ] BBSR-Lizenzanfrage rausschicken (parallel)
- [ ] BGR-BBD-Mail rausschicken (parallel) — liegt seit Wochen
      als Draft (`docs/MAIL_BGR_BBD.md`)

### Was **nicht** in S1/S2 kommt

- BBSR-Layer (Hitze/Hagel/Sturm/Erdbeben/Waldbrand/Starkregen) —
  blockiert bis Lizenzantwort
- BfS / Landes-Radon — Patchwork, mehrere Tage Klärung pro Land,
  Phase-2
- GFZ Erdbebenzonen DIN EN 1998-1/NA — Quelle korrigiert (war BGR,
  ist GFZ), Lizenz-Klärung offen, Phase-2
- Altlasten — unverändert verschoben (BBodSchG)
- B2B-API-Endpoints — kommt nach NL-Launch
- Cozy-Design für geoforensic.de — startet parallel sobald Cozy
  Kapazität hat, blockiert S1/S2 nicht
