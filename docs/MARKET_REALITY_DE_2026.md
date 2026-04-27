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
| Adressgenaue Naturgefahren | ✅ | ✅ | teilweise | ✅ | ❌ | teilweise |
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

### Option B — „Soil-Act + InSAR" (Benjamins Originalidee)

Schmaler positionieren auf zwei Achsen, die niemand sonst kombiniert:

1. **EU Soil Monitoring Directive 2025/2360** — DE muss bis
   **17.12.2028** transponieren. Käufer-Rechtsanspruch auf Bodendaten
   wird kommen. Niemand der Großen positioniert sich als
   „Soil-Directive-Compliance-Tool für Privatkäufer". **Weißer Fleck,
   regulierungsgetriebener Sog.**
2. **InSAR-Bodenbewegung mit Tiefe** — gemessene Zeitreihen pro
   Messpunkt, nicht aggregiertes Label. Einziger echter Moat.

**Naturgefahren schlank:** nur Hochwasser + Radon + Bergbau (lokale
Pflicht-Themen, BBSR deckt sie nicht alle ab). **Nicht versuchen,
BBSR zu kopieren.**

**Altlasten als Pflicht-Layer:** docestate ist B2C, aber
landesspezifisch und teuer (30–100 EUR pro BL) → echte Lücke für eine
günstigere DE-weite Lösung.

**B2B-API als zweites Standbein vorbereiten:** sobald
Pflichtversicherung beschlossen wird, sind wir mit EGMS-Daten
anschlussfähig.

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

## 6. Offene Entscheidung

- [ ] **Strategie:** Avista-Parität (Option A) oder
      Soil-Act + InSAR-Pivot (Option B)?

Sprint-Planung beginnt erst nach dieser Entscheidung. Bis dahin: kein
neues Modul anfangen, keine neuen Daten-Lizenzen verhandeln.

---

## 7. Sofortige Hausaufgabe (egal welche Strategie)

- [x] Diesen Spec speichern (dieses Doc)
- [x] `CLAUDE.md` korrigieren — „No competitor exists" ist falsch
- [x] `PLAN_GEOFORENSIC_DE.md` korrigieren — Markttabelle aktualisiert
- [x] `DATA_SOURCES_GROUNDSURE_PARITY.md` korrigieren — Wettbewerbstabelle erweitert

---

## 8. Konkrete nächste 2 Wochen (nach Strategieentscheidung)

Das hängt komplett von §6 ab. Vorgeschlagener Ablauf:

1. **Heute:** Spec ist gespeichert, Repo-Docs sind aktualisiert.
2. **Diese Woche:** Benjamin entscheidet Option A oder B.
3. **Nächste Woche:** Sprint-Planung gemäß Entscheidung.

Ohne Entscheidung in §6 ist jeder neue Sprint ein Schuss ins Dunkle.
