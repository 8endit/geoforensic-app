# SEO_BRANDING_ROLLOUT_PLAN.md — Konversion, SEO, KI-Auffindbarkeit

**Stand:** 2026-05-01, nach Visuals-Sprint Deploy (Commit `9e51c3f` live).
**Bezug:** Domenico hat einen 15-seitigen Maßnahmenkatalog
(`docs/external/Domenico_Massnahmenkatalog_2026-05.pdf`, falls archiviert)
geliefert. Dieses Doc ist die **operative Antwort** darauf — was wir
übernehmen, was wir umparken, was fehlt und in welcher Reihenfolge.

**Zweck dieses Docs:** Self-contained Plan, der ohne den Kontext der
vorigen Chat-Session ausreicht. Eine neue Claude-Session liest dies und
kann mit Phase A.1 starten.

**Vorgeschichte:** Der Visuals-Sprint (V.0–V.4.7 + V.7) wurde
2026-05-01 abgeschlossen und deployed. Hero, Problem-Sektion,
How-It-Works, Benefits und Premium-Teaser sind narrativ um die sechs
Visualisierungen gebaut. Berlin-Charlottenburg-Demo (Bismarckstr. 10)
mit Klasse 2 / Note B / 47 PSI / r=0.89 ist live. Domenicos Katalog
basiert auf der **live deployten Version** dieser Landing.

---

## 1. Diagnose im Vergleich Visuals-Sprint vs. Domenico-Katalog

| Bereich | Visuals-Sprint (erledigt) | Domenico-Katalog (offen) |
|---|---|---|
| Hero | 2-spaltig mit Bericht-Vorschau, Trust-Bar mit 8 Quellen | „Doppelter Hero" — Eyebrow + H1 + H2 + Sub-Headline = 3× dasselbe Versprechen |
| Visual-Storytelling | Visuals narrativ in 4 Sektionen verzahnt | — |
| Bericht | Vollbericht-Refactor FPDF→Chrome-Headless (442 KB, Cozy-Design) | — |
| Free-Teaser | Polished Trust-Bar, Lock-Pille, CTA | — |
| **SEO-Markup** | — | **Komplett fehlt:** FAQPage, Organization, Service, BreadcrumbList |
| **Branding** | — | **Versand-Domain ist `geoforensic.de`** statt `bodenbericht.de` (Spam-Score, Brand-Bruch) |
| **Trust/E-E-A-T** | — | **Kein „Über uns"** auf einer Adresse mit rechtlich-finanzieller Tragweite |
| **Konversion** | Lead-Form prominent | Quiz-Link visuell zu gleichwertig zum Primary-CTA |
| **Topical Authority** | — | Single-Page-Architektur, kein Glossar, kein Magazin |
| **KI-Auffindbarkeit** | — | Keine `llms.txt`, keine strukturierten Snippets |
| **Title/Meta** | — | Generisch, primäres Keyword nicht am Anfang |

**Kernbefund:** Das Produkt sieht jetzt sehr gut aus — niemand findet
es. Der Visuals-Sprint hat die Tür schön gemacht, dieses Doc baut den
Weg dorthin.

## 2. Was Domenico richtig gesehen hat — und was nicht

### Übernehmen (strikt, ohne Tweaks)
- **A1** Versand-Domain auf `bodenbericht.de` mit SPF/DKIM/DMARC
- **A2** Hero entdoppeln (Beschreibungsabsatz raus, eine Subline reicht)
- **A3** Quiz-Link visuell klar untergeordnet, nicht gleichwertig
- **A4** FAQPage JSON-LD im `<head>` der Startseite
- **A5** Organization + Service JSON-LD
- **A7** Title 50–60 Zeichen, Description 140–160, primäres Keyword vorne
- **B2** Glossar/Wissens-Hub (aber nur ~5 Begriffe, nicht 8 — siehe §3)
- **B4** `llms.txt` im Webroot
- **C2** Backlink-Aufbau über Branchenkontakte (Stefan/Domenico/Gregor-
  Netzwerk, nicht generisches Cold-Outreach)

### Übernehmen mit Modifikation
- **A1 ergänzt** — Versand-Domain umstellen, ABER **Brand-Stack nicht
  flachklopfen**. Geoforensic GmbH bleibt als Betreibergesellschaft
  sichtbar (Footer, Impressum, Über-uns). Versand-Adresse wird
  `bericht@bodenbericht.de` für Konsumenten-Mails, `team@geoforensic.de`
  für B2B-Kommunikation. Zwei Adressen mit klaren Rollen statt einer.
- **A6 Über uns** — **nicht** als weitere Homepage-Sektion einschieben
  (Narrative bleibt sauber), sondern als eigene `/ueber-uns`-Seite +
  diskreter Footer-Link + 1-Zeiler unter Hero „Service der
  Tepnosholding GmbH".
- **B1 Sub-Landings** — `/fuer-immobilienkaeufer` priorisieren als
  HAUPTZIELGRUPPE; `/fuer-gartenbesitzer`, `/fuer-landwirte`,
  `/fuer-bautraeger` als zweite Welle. **Nicht alle gleichzeitig**.
- **B6 Reviews** — Provenexpert oder Google Business Profile statt
  Trustpilot (Trustpilot hat Pay-to-Suppress-Reputation in DE).

### Bremsen / Defer
- **B5 10 Stadt-Landingpages** — Programmatic Stadt-SEO wirkt schnell
  thin/templated, Google straft das ab. Erst 4 Wochen GSC-Daten sammeln,
  ob Stadtanfragen tatsächlich Traffic bringen. Defer auf Phase C oder
  ganz streichen.
- **B7 „Konkretes Launchdatum für Premium"** — Stripe-Flow ist nicht
  gebaut. Datum publik nennen schafft Pressure ohne Backup. „Q3/2026"
  bleibt vage.
- **C1 „15-20 Artikel à 1500-2500 Wörter in 90 Tagen"** — Unrealistisch
  ohne Content-Writer. Stattdessen **5-8 tiefe Artikel** > 20 thin ones
  für E-E-A-T.
- **C3 Markenproblem** — Disambiguierung im Title („nicht zu
  verwechseln mit dem behördlichen Bodenbericht der Landesämter") wirkt
  defensiv-werblich. Lieber positiv besetzen: „Privater
  Risiko-Report" als Untertitel etablieren, nicht über Negation.

## 3. Was Domenicos Katalog FEHLT (eigene Ergänzungen)

1. **Source-Routing für Vollbericht.** Quiz und Landing emittieren nur
   `source=quiz`/`source=landing` → `TEASER_SOURCES` → Free-Teaser.
   **Der frische V.4-Vollbericht ist nur per direkter API erreichbar.**
   Wir produzieren das beste Asset, das niemand sieht. **Größerer
   Marketing-Fehler als alles in Domenicos Katalog.**

2. **Browser-Preview** ist zur Hälfte schon da. `POST /api/reports/preview`
   existiert backend-seitig (rate-limited 10/h, gibt Ampel + Punktzahl
   zurück). Es fehlt nur der Frontend-Hook. Domenico veranschlagt das
   als 30-Tage-Projekt — bei uns ~4 h Frontend.

3. **Lighthouse-Baseline** nicht gemessen. Bevor wir Stunden in
   Page-Speed investieren: einmal Lighthouse laufen lassen, Score
   notieren, gezielt das Schlechteste fixen.

4. **Vollbericht-PDF-SEO.** Beispiel-Vollberichte als HTML-Versionen
   unter `/muster-berichte/<adresse>` veröffentlichen sind instant
   indexierbare Long-Form-Inhalte ohne neuen Content-Writing-Aufwand.

5. **IndexNow-Hook.** Bing/Copilot/ChatGPT-Web crawlen über IndexNow.
   Nach jedem Deploy einen IndexNow-Push beschleunigt KI-Indexierung
   um Tage.

6. **Sentry-DSN scharfschalten.** Aus dem alten Backlog. Wenn
   Konversion-Tracking jetzt scharfgeschaltet wird, müssen wir auch
   Fehler sehen.

## 4. Phasen — was wir wann machen

### Phase A — Sofort (diese Woche, ~6 h Arbeit)

| Aufgabe | Ort | Aufwand | Eigner |
|---|---|---|---|
| **A.1** Hero entdoppeln (Beschreibungsabsatz raus) | `landing/index.html` Zeile ~157 | 5 min | dev |
| **A.2** Quiz-Link in Hero visuell untergeordnet (kleinerer Schrift, gedämpfte Farbe) | `landing/index.html` ca. Zeile ~193 | 10 min | dev |
| **A.3** FAQPage JSON-LD im `<head>` | `landing/index.html` `<head>` | 30 min | dev |
| **A.4** Organization + Service JSON-LD | dito | 20 min | dev |
| **A.5** Title + Meta-Description schärfen | `landing/index.html` `<head>` | 5 min | dev |
| **A.6** SMTP-Konfig auf `bericht@bodenbericht.de` + DKIM/SPF/DMARC | Brevo + DNS | 2 h | ops/founder |
| **A.7** `/ueber-uns`-Seite anlegen | `landing/ueber-uns.html` neu | 1 h | founder (Bio + Foto) |
| **A.8** Source-Routing-Fix: zweiter Form-Pfad „Premium-Vorab-Anfrage" → setzt `source` außerhalb `TEASER_SOURCES` → liefert Vollbericht | `landing/index.html` neue Sektion + `routers/leads.py` Test | 1 h | dev |
| **A.9** IndexNow-Hook im Deploy-Script | `landing/scripts/index_now.py` neu | 15 min | dev |
| **A.10** Lighthouse-Baseline messen (Mobile + Desktop) | Console | 15 min | dev |

**Akzeptanz-Checkliste Phase A:**
- Mail-Tester (mail-tester.com) ≥ 9/10
- Google Rich Results Test grün für FAQPage + Organization + Service
- Title 50-60 Zeichen, Description 140-160 Zeichen, primäres Keyword am Anfang
- `/ueber-uns` zeigt Foto + Bio + fachlichen Hintergrund + Beziehung Bodenbericht/Tepnosholding
- Premium-Vorab-Form-Pfad emittiert `source=premium-vorab` → Lead bekommt Vollbericht-PDF (nicht Teaser)
- Lighthouse Mobile/Desktop Performance, Accessibility, Best-Practices, SEO ≥ 90 (oder dokumentierte Lücken)

### Phase B — Kurzfristig (30 Tage, ~20 h Arbeit)

| Aufgabe | Aufwand | Eigner |
|---|---|---|
| **B.1** Browser-Preview (Frontend-Hook auf existing `POST /api/reports/preview`) | 4 h | dev |
| **B.2** Sub-Landingpage `/fuer-immobilienkaeufer` (1500 Wörter, eigene FAQ, eigener CTA mit `utm_content=immobilienkaeufer`) | 6 h | dev + content |
| **B.3** `llms.txt` im Webroot mit kuratierter Liste der Hauptinhalte | 30 min | dev |
| **B.4** Glossar startet mit 5 Seiten unter `/wissen/`: `altlast`, `setzung-vs-hebung`, `eu-bodenrichtlinie`, `schwermetalle-im-boden` (Sammelseite, nicht 8 einzelne), `insar-egms` | 8 h | dev + content |
| **B.5** Provenexpert-Profil anlegen, Pilotnutzer aktiv um Review bitten (automatisierte E-Mail nach PDF-Versand) | 1 h Setup | ops |
| **B.6** Sub-Landings für Garten/Landwirte/Bauträger (zweite Welle, 600+ Wörter pro Seite, eigenes Schema) | 8 h | dev + content |

**Akzeptanz-Checkliste Phase B:**
- Browser-Preview lädt < 5 s, Mobile + Desktop sauber
- `/fuer-immobilienkaeufer` indexiert in GSC, eigenes Service-Schema valide
- `llms.txt` erreichbar, korrektes Markdown-Format
- 5 Glossar-Seiten indexiert in Sitemap, alle in GSC
- Mindestens 5 echte Reviews auf Provenexpert

### Phase C — Mittelfristig (90 Tage)

- **C.1** 5-8 Magazin-Artikel à 1500-2500 Wörter (Quality-over-Quantity, nicht 15-20)
- **C.2** Backlink-Aufbau über Stefan/Domenico/Gregor-Netzwerk + Whitepaper „EU-Bodenrichtlinie 2025/2360 — Auswirkungen auf Eigentümer"
- **C.3** PR mit eigenen Daten: „Bodenbericht-Index 2026: Wo in DE Altlastenrisiken konzentriert sind" als interaktive Karte + Whitepaper + Pressemitteilung
- **C.4** Beispiel-Vollberichte als HTML unter `/muster-berichte/<adresse>` veröffentlichen (instant Long-Form-Content)
- **C.5** Stadt-Landingpages **nur wenn** GSC-Daten nach 4 Wochen tatsächliche Stadtanfragen zeigen
- **C.6** Wikipedia-Eintrag prüfen sobald Relevanzkriterien erfüllt (mehrfache Berichterstattung in Fachmedien)

## 5. Reihenfolge mit Abhängigkeiten

```
Phase A (Woche 1)
   ├── A.1-A.5 (HTML-Edits, parallel)
   ├── A.6 SMTP (parallel, ops-Aufgabe)
   ├── A.7 Über-uns (braucht Foto + Bio von founder)
   ├── A.8 Source-Routing (parallel)
   ├── A.9 IndexNow (nach Deploy-Script-Verständnis)
   └── A.10 Lighthouse (nach Phase A.1-A.5 abgeschlossen, sonst Baseline veraltet)

Phase B (Woche 2-4)
   ├── B.1 Browser-Preview (parallel zu Sub-Landings)
   ├── B.2 /fuer-immobilienkaeufer (zuerst, weil Hauptzielgruppe)
   ├── B.3 llms.txt (nach Sub-Landing live, damit darauf verweist)
   ├── B.4 Glossar (parallel, aber jede Begriffsseite verlinkt auf Sub-Landings → erst nach B.2)
   ├── B.5 Provenexpert (jederzeit)
   └── B.6 weitere Sub-Landings

Phase C (Woche 4-12)
   ├── C.1 Magazin (parallel zu allem)
   ├── C.2 Backlinks (jederzeit, brauchen Outreach-Vorlauf)
   ├── C.3 PR (nach Magazin live, sonst nichts zum Verlinken)
   ├── C.4 Muster-Berichte (parallel)
   ├── C.5 Stadt-Pages (nur wenn GSC-Daten dafür sprechen)
   └── C.6 Wikipedia (Trigger: 3+ unabhängige Fachmedien-Erwähnungen)
```

## 6. Risiken und Stolperfallen

### 6.1 Brevo Multi-Domain
SMTP-Provider Brevo unterstützt Multi-Domain-Versand, aber je nach
Plan kostenpflichtig. Vor A.6: Brevo-Plan prüfen, ggf. Upgrade einplanen.
DKIM-Records in DNS bei `bodenbericht.de` neu setzen (Domain liegt
vermutlich bei united-domains/INWX → DNS-Editor-Zugriff sicherstellen).

### 6.2 Source-Routing-Fix (A.8) ändert Lead-Flow
Aktuell ist `source != TEASER_SOURCES` als „Logwarning + Fallback auf
Teaser" implementiert. Wenn wir einen neuen Source-Wert einführen, der
ECHT auf Vollbericht routet, müssen wir testen:
- Vollbericht rendert in der `routers/leads.py`-async-Pipeline ohne
  Timeout (Chrome-Headless braucht ~5 s vs. FPDF früher 1 s)
- Brevo-Mail mit größerem PDF-Anhang (442 KB) wird zugestellt
- Admin-Dashboard `landing/admin.html` zeigt VOLL-Badge korrekt

### 6.3 FAQPage-Schema vs. realer FAQ
FAQ-Snippet im JSON-LD MUSS exakt dem sichtbaren FAQ-HTML entsprechen,
sonst verstößt es gegen Google-Richtlinie und kann zu Manual Action
führen. Bei FAQ-Änderungen Schema mitziehen.

### 6.4 Glossar-Content nicht von ChatGPT generieren
Google hat 2024 begonnen, AI-generierten Content härter zu strafen.
Glossar-Texte müssen **menschlich verfasst** oder **AI-assisted +
human-edited** sein, nicht 1:1 ChatGPT-Output. E-E-A-T-Risiko.

### 6.5 Marken-Disambiguierung — Risiko Verwirrung
Domenicos „nicht zu verwechseln mit dem behördlichen Bodenbericht"
wirkt defensiv. Risiko: User googelt „Bodenbericht Sachsen-Anhalt",
landet auf unserer Seite, sieht Disambiguierung und denkt „die machen
was anderes als ich suche". Lieber positives Branding als Negation.

## 7. Was nach diesem Sprint offen bleibt

- **Stripe-Paywall scharfschalten** für Premium-Vollbericht (~199 EUR,
  preislich noch nicht final, siehe `docs/PLAN_GEOFORENSIC_DE.md`)
- **NL-i18n** des Vollberichts — Markt #1 erfordert NL-Sprache
- **NL-Pendant der 6 Visuals** — alle Texte müssen übersetzt werden
- **V.5 React-Komponenten** + **V.6 Frontpage-Demo** im
  `cozy-frontend`-Repo (interaktiv, eigenes Frontend-Stack)
- **KOSTRA-Raster auf VPS hochladen** (alter Backlog, blockiert
  KOSTRA-Sektion im Vollbericht)
- **BBSR/GFZ-Lizenz-Klärung** (Mail-Vorlagen liegen bereit)
- **SSH-Passwort-Login auf VPS abschalten** (key-only Hardening)

## 8. Wie eine neue Claude-Session damit startet

**Empfohlene erste Anweisung:**

> Lies `docs/SEO_BRANDING_ROLLOUT_PLAN.md`. Bestätige dass du den Plan
> verstehst, dann fang an mit Phase A.1 (Hero entdoppeln).

**Voraussetzungen:**
- Visuals-Sprint Commit `9e51c3f` ist auf VPS deployed
- Brevo-Account-Zugriff (für A.6)
- DNS-Editor-Zugriff für `bodenbericht.de` (für A.6)
- Foto + Bio des founders (für A.7)
- Branding/Company-Verhältnis Bodenbericht/Tepnosholding/Geoforensic
  ist klar (für Footer + Über-uns-Wortlaut)

**Datenquellen der Wahrheit:**
- `landing/index.html` — Live-Markup
- `backend/app/routers/leads.py` — `TEASER_SOURCES`-Set, Lead-Flow
- `backend/app/email_service.py` — Brevo SMTP-Konfig
- `docs/visuals/SPEC_VISUALS.md` — Visual-Spec (für Konsistenz mit neuen Sub-Landings)
- `docs/DATA_PROVENANCE.md` — Datenquellen-Audit (für Glossar-Belege)

**Bei Unklarheiten:** Annahme treffen, in Commit-Message dokumentieren,
weitermachen. SEO-Effekte brauchen 2-4 Wochen GSC-Sichtbarkeit nach
Deploy — Phase A messbar erst Mitte Mai 2026.
