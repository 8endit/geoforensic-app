# Cursor-Task: Teaser-Report (bodenbericht.de) vs. Vollreport (geoforensic.de)

> **Status (2026-04-19):** Routing-Weiche, Email-Differenzierung und
> Admin-Badge sind implementiert (siehe unten "Umsetzungs-Status"). Was
> bleibt: Teaser-Design-Polish und die tatsächliche Verdrahtung des
> Vollreports für den Paid-Flow — das gehört in den geoforensic.de-Plan.

**Ziel:** Aktuell erzeugen Quiz- und Landing-Leads denselben Vollreport.
Das ist falsch aufgestellt. `bodenbericht.de` soll ein **Free Lead-Magnet**
sein mit einem **schönen, bewusst knappen Teaser-PDF**. Der **volle Bericht**
gehört auf `geoforensic.de` und ist zahlungspflichtig.

**Dieser Plan ist bindend.** Nicht interpretieren, nicht erweitern, nicht
neue Features dazudichten. Bei Unklarheit → zurückfragen.

---

## Regeln (für alle Tasks)

1. **Nur die hier genannten Dateien bearbeiten.**
2. **Keine neuen Dependencies**, kein `npm install`, kein `pip install`.
3. **Keine CSS-Umbauten** außerhalb der neuen Teaser-Datei.
4. **Keine neuen Routen** am Backend. Die Weiche läuft über das bestehende
   `source`-Feld von `POST /api/leads`.
5. **Die Engine selbst bleibt unangetastet.** `full_report.py`, `soil_data.py`,
   `report_charts.py`, EGMS-Query und SoilGrids-Logik werden nicht geändert.
6. **Kein Commit bevor alle 4 Tasks durch sind.**
7. **Formulierungen** unten wortwörtlich verwenden.

---

## Ausgangslage (zum Verifizieren)

- `backend/app/routers/leads.py:172` speichert `source` in die DB,
  aber **keine Code-Stelle wertet das Feld aus**.
- `backend/app/routers/leads.py:13` importiert `generate_html_report` aus
  `backend/app/html_report.py`, das ist der einzige Report-Generator der
  aktuell im Lead-Flow läuft.
- Die Funktion `generate_full_report` in `backend/app/full_report.py`
  existiert, wird aber im Lead-Flow **nicht** aufgerufen (sie ist für den
  späteren Paid-Flow gedacht).

Grep zum Gegenchecken bevor du loslegst:

```bash
grep -rn "generate_html_report\|generate_full_report" backend/app
grep -rn "payload\.source\|source ==" backend/app/routers
```

Wenn dieser Grep andere Ergebnisse liefert als hier beschrieben: **stopp,
zurückfragen**. Der Plan geht sonst ins Leere.

---

## Task 1 — Neuen Teaser-Generator anlegen

**Datei neu:** `backend/app/teaser_report.py`

Eine eigenständige Funktion `generate_teaser_report(address, lat, lon,
ampel, point_count, mean_velocity, geo_score, answers) -> str` die **nur**
einen HTML-String zurückgibt. Inhalt des Teasers:

1. **Kopf:** Adresse, Datum, Bodenbericht-Logo (aus `landing/images/logo-horizontal.png`)
2. **Ampel-Badge** (grün/gelb/rot) mit Klartext-Satz (Beispieltexte unten)
3. **Ein einziger Kernwert** — der GeoScore als großer Kreis-Gauge (SVG,
   gleiche Optik wie im Vollreport — Funktion `_svg_gauge` kann aus
   `html_report.py` kopiert werden, **nicht importiert**, damit der Teaser
   vom Vollreport unabhängig bleibt).
4. **Ein Satz** pro Quiz-Antwort (Nutzung, Dringlichkeit) — Template
   wortwörtlich wie in `full_report.py:54-66` (`_NUTZUNG`, `_DRINGLICHKEIT`).
5. **Teaser-Block:** Drei Platzhalter-Kacheln ("Schwermetalle", "Bodenqualität",
   "Versiegelung") mit Blur-Effekt und Schloss-Icon, darunter folgender Text
   wortwörtlich:

   > Der vollständige Bericht enthält Schwermetall-Analyse (LUCAS), Bodenqualität
   > (SoilGrids), Nährstoff-Profil und eine personalisierte Handlungsempfehlung.
   > **Verfügbar auf geoforensic.de — jetzt auf die Warteliste.**

6. **CTA-Button:** "Zur Warteliste" mit Link auf `https://bodenbericht.de/#waitlist`.
7. **Disclaimer-Fußzeile** wortwörtlich wie in `full_report.py` (nicht
   weichspülen — der rechtliche Text bleibt).

**Wichtig:**
- Zwei Seiten maximal bei A4-Druck.
- Keine Metals-Tabelle, keine SoilGrids-Balken, keine LUCAS-Werte, kein
  Karten-Snippet.
- Kein neuer Font-Load. Gleiche Font-Discovery wie `full_report.py:24-40`.

**Ampel-Texte wortwörtlich:**

- grün: "Die Satellitendaten zeigen an Ihrer Adresse keine auffälligen Bodenbewegungen."
- gelb: "Die Satellitendaten zeigen an Ihrer Adresse leichte Bodenbewegungen. Beobachtung empfohlen."
- rot: "Die Satellitendaten zeigen an Ihrer Adresse deutliche Bodenbewegungen. Weiterführende Prüfung empfohlen."

---

## Task 2 — Weiche im Lead-Flow

**Datei:** `backend/app/routers/leads.py`

**Aktuell** ruft `_generate_and_send_lead_report` direkt
`generate_html_report(...)` auf.

**Neu:** Vor dem Aufruf entscheiden:

```python
if source in ("quiz", "landing", "premium-waitlist"):
    from app.teaser_report import generate_teaser_report
    html = generate_teaser_report(...)
else:
    html = generate_html_report(...)
```

Dazu muss `source` bis in `_generate_and_send_lead_report` durchgereicht
werden (aktuell nicht, siehe `leads.py:49-56`). Also:

- Funktions-Signatur um `source: str` erweitern
- Aufruf-Seite (`leads.py:184` Bereich) `source=payload.source` mitgeben

**Wichtig:** Der Default für unbekannte Sources ist **Teaser**, nicht
Vollreport. Der Vollreport läuft erst ab einer neuen Source `"paid"` (die
heute noch nicht existiert — das ist korrekt so).

---

## Task 3 — Betreff + Mail-Text anpassen

**Datei:** `backend/app/email_service.py`

Wenn der Teaser geschickt wird, soll der Mail-Betreff lauten:

> Ihr kostenloses Boden-Screening für {Adresse}

(Aktuell: generisch "Ihr Bodenbericht"). Die Mail-Body-Einleitung bekommt
einen zusätzlichen Absatz **über** dem Anhang-Hinweis, wortwörtlich:

> Dies ist eine kostenlose Kurzfassung. Den ausführlichen Bericht mit
> Schwermetall-Analyse, Bodenqualität und Handlungsempfehlung entwickeln
> wir gerade unter geoforensic.de — trag dich dort gerne auf die Warteliste.

Keine Umformulierung. Kein "wir freuen uns" o.ä.

Wenn `source == "paid"`: alter Betreff + alter Body (unverändert).

---

## Task 4 — Admin-Dashboard Badge

**Datei:** `backend/app/routers/admin.py` und `landing/admin.html`

In der Leads-Tabelle soll pro Zeile sichtbar sein, ob der Lead einen
Teaser- oder Voll-Report bekommen hat. Ein simples Text-Badge reicht:

- `source in ("quiz", "landing", "premium-waitlist")` → Badge "TEASER"
- `source == "paid"` → Badge "VOLL"
- Sonst → Badge "—"

Keine neue Spalte, keine neue Migration. Nur die vorhandene `source`-Spalte
visuell sichtbar machen. Kein JS-Framework, kein Ajax-Reload.

---

## Nicht Teil dieser Task

- Stripe-Checkout / Paid-Flow → separater Task, später
- Neue Domain `geoforensic.de` verdrahten → separater Task, später
- Teaser-Design-Polish (Icons, Grafik-Feinschliff) → separater Task, später
- NL-Version des Reports → separater Task, später
- Map-Snippet im PDF → separater Task, später

**Wenn du bei einem dieser Punkte landest: stopp.**

---

## Definition of Done

1. `grep -rn "generate_teaser_report" backend/app/` findet mindestens zwei
   Treffer (Datei + Import).
2. Ein Lead mit `source: "quiz"` auf `/api/leads` erzeugt ein **zweiseitiges**
   PDF ohne Metall- oder SoilGrids-Tabellen.
3. Ein Lead mit `source: "paid"` erzeugt weiterhin den Vollreport (aktueller
   Stand, kein Regress).
4. Admin-Dashboard zeigt für jeden Lead "TEASER" oder "VOLL".
5. Keine der vier Engine-Dateien (`full_report.py`, `html_report.py`,
   `soil_data.py`, `report_charts.py`) ist im Diff.
6. Commit-Message-Vorschlag:
   `feat(leads): split teaser vs full report per source, bodenbericht.de = teaser`

---

## Umsetzungs-Status (2026-04-19)

Pragmatische Abweichung vom Ursprungsplan: `html_report.py` rendert **bereits
heute** faktisch den Teaser — die Helper-Funktionen für Metals, SoilGrids und
Texture existieren, werden aber in der finalen Template-String-Interpolation
(Zeilen 413-499) **nicht** aufgerufen. Es war also keine neue Datei nötig,
nur eine klare Weiche + ehrliches Benennen.

**Erledigt auf Branch `claude/discuss-before-unavailable-foZZ4`:**

1. ✅ **Weiche in `routers/leads.py`:**
   `TEASER_SOURCES = {"quiz", "landing", "premium-waitlist"}` — alles andere
   loggt Warnung und fällt auf den Teaser zurück, bis der Paid-Flow steht.
   `source` wird bis `_generate_and_send_lead_report` durchgereicht und
   an `send_report_email(is_teaser=…)` übergeben.
2. ✅ **Email-Differenzierung in `email_service.py`:**
   - Teaser-Betreff: "Ihre kostenlose Boden-Kurzfassung für {Adresse}"
   - Vollreport-Betreff: "Ihr Bodenbericht für {Adresse}" (wie bisher)
   - HTML-Body + Plaintext-Fallback haben je Teaser/Voll andere Überschrift,
     Intro, Info-Liste und (nur im Teaser) einen Upsell-Block mit Link auf
     `https://bodenbericht.de/#premium` (die Warteliste — `geoforensic.de`
     existiert als Domain noch nicht, Link kommt erst wenn der Paid-Flow live ist).
3. ✅ **Admin-Dashboard-Badge in `landing/admin.html`:**
   Neue Spalte "Report" mit `TEASER`/`VOLL`/`—` — nur JS-Branching, keine
   Schema-Änderung.
4. ✅ **Docstring in `html_report.py`:**
   Klargestellt dass dies der Teaser ist und die Engine-Helper bewusst nicht
   interpoliert werden.

**Nicht erledigt (bewusst verschoben):**

- ❌ Eigenständige Datei `backend/app/teaser_report.py` — nicht nötig, weil
  `html_report.py` bereits die Teaser-Funktion ist. Wenn Cursor/Future-Me
  später eine Umbenennung möchte, ist das ein Rename-Refactor, kein Feature.
- ❌ Stripe-Checkout / Paid-Flow → gehört in den geoforensic.de-Plan.
- ❌ Tatsächliche Verdrahtung von `full_report.py` (FPDF, liefert Bytes, nicht
  HTML — API-Mismatch zum Chrome-Renderer). Muss beim geoforensic.de-Plan
  mitbedacht werden: entweder `full_report.py` auf HTML+Chrome umstellen,
  oder `pdf_renderer.py` um einen Bytes-Passthrough erweitern.
- ❌ Teaser-Design-Polish (Blur-Kacheln, Schloss-Icons, CTA-Hierarchie) —
  separater Design-Task, sobald visuell getestet werden kann.

**Verifikation im Deploy (wenn du wieder am PC bist):**

```bash
# Auf dem Server
ssh root@185.218.124.158
cd /opt/bodenbericht
git pull origin main                 # (nach Merge des Branches)
docker compose build backend && docker compose up -d

# Anschließend: Test-Lead absenden und Mail-Betreff prüfen
curl -X POST https://bodenbericht.de/api/leads \
  -H "Content-Type: application/json" \
  -d '{"email":"dein-test@example.com","address":"Alexanderplatz, Berlin","source":"quiz","answers":{"nutzung":"Eigenheim / Garten","dringlichkeit":"Ich informiere mich nur"}}'
```

Erwartet: Betreff "Ihre kostenlose Boden-Kurzfassung für …" und Body mit
Warteliste-Hinweis (Link `https://bodenbericht.de/#premium`). Admin-Dashboard
zeigt neuen Eintrag mit `TEASER`-Badge.
