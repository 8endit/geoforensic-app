# PLAN_NL_I18N.md — Niederländische Sprachversion des Vollberichts

**Status:** offen, nicht angefangen.
**Trigger:** spätestens beim ersten zahlenden NL-Kunden.
**Aufwand-Schätzung gesamt:** 6–10 Stunden konzentrierte Arbeit, am
sinnvollsten in einer dedizierten Session — nicht zwischendurch.

---

## 1. Warum, und warum nicht früher

NL ist laut `CLAUDE.md` und `MARKET_REALITY_DE_2026.md` **Markt #1**.
FunderConsult ist die direkte Konkurrenz, ihr Output ist Niederländisch.
Wir verkaufen einen NL-Käufern aktuell ein Produkt, dessen
PDF-Hauptasset ausschließlich auf Deutsch ist. Damit kann man kein NL
B2C-Geschäft aufmachen.

**Warum nicht heute:** der Trigger fehlt. Stripe ist nicht live, das
Source-Routing für Vollbericht emittiert noch keinen NL-Kunden. Eine
halbe Übersetzung in den Code zu schmieren produziert Tech-Debt, das
beim ersten echten NL-Kunden nochmal überarbeitet werden muss. Lieber
beim Trigger ordentlich machen als jetzt halb.

**Was bis dahin reicht:** der Cover-Disclaimer könnte bilingual sein
(„Dit rapport is een Duitstalige geautomatiseerde
bodemscreening — Deutschsprachige Daten-Auswertung") als Stop-Gap für
ein paar NL-Test-Käufer in einer kontrollierten Pilotphase.

---

## 2. Scope — was übersetzt werden muss, was nicht

### Wird übersetzt

- Alle 16 Vollbericht-Templates unter `backend/templates/full_report/`
  - `cover.html`, `base.html`, `block_separator.html`, `data_sources.html`
  - `section_01_bodenbewegung.html` … `section_12_einschaetzung.html`
- Visual-SVG-Texte unter `backend/templates/visuals/*.jinja2`
  - 6 Komponenten: property_context_map, neighborhood_histogram,
    risk_dashboard, correlation_radar, time_series, etc.
- Mail-Templates in `backend/app/email_service.py`
  - `send_report_email` (HTML + plaintext) — variant für NL-Empfänger
  - `send_review_request_email` analog
- Disclaimer-Text in `app/full_report.py` und `app/html_report.py`

### Wird NICHT übersetzt (zumindest Phase 1)

- **Landing-Page** (`landing/*.html`) — bleibt deutsch. NL-Kunden
  kommen wahrscheinlich über NL-spezifische Sub-Landing oder
  FunderConsult-Affiliate, nicht über `bodenbericht.de` direkt.
  Eine eigene NL-Landing kommt in einer separaten Phase.
- **Admin-Dashboard** (`landing/admin.html`) — interne UI, bleibt DE.
- **Backend-Logs, Sentry-Messages, Alembic-Migration-Comments** —
  Operator-facing, bleibt EN/DE wie heute.
- **Daten-Quellen-Namen** (BBodSchV, KOSTRA, etc.) — Eigennamen,
  bleiben unverändert auch im NL-PDF.

---

## 3. Technischer Ansatz

### 3.1 Tooling

```
pip install Babel
```

`Babel` liefert:
- `pybabel extract` — sammelt alle `{% trans %}` und `_()` aus
  Templates und Python-Quellen in `messages.pot`
- `pybabel init -l nl` — erzeugt `locale/nl/LC_MESSAGES/messages.po`
- `pybabel compile -d locale` — produziert `messages.mo` Binärdateien

Jinja2 nutzt seine eingebaute `jinja2.ext.i18n` Extension. In
`backend/app/full_report.py :: _full_report_env()`:

```python
from jinja2 import Environment, FileSystemLoader
import gettext

def _make_env(locale: str = "de") -> Environment:
    translations = gettext.translation(
        "messages",
        localedir=BACKEND_ROOT / "locale",
        languages=[locale],
        fallback=True,
    )
    env = Environment(
        loader=FileSystemLoader(str(FULL_REPORT_TEMPLATES)),
        extensions=["jinja2.ext.i18n"],
        ...
    )
    env.install_gettext_translations(translations)
    return env
```

Aufrufer entscheidet pro Render-Aufruf welches Locale.

### 3.2 Locale-Routing in der Pipeline

In `backend/app/routers/leads.py` und `backend/app/routers/reports.py`
wird `country_code` bereits ermittelt (aus Nominatim). Locale-Mapping:

```python
LOCALE_BY_COUNTRY = {
    "de": "de",
    "at": "de",   # AT liest deutsche Reports, kein eigenes Locale
    "ch": "de",   # CH-DE-Region; CH-FR/IT separat falls je relevant
    "nl": "nl",
}
locale = LOCALE_BY_COUNTRY.get(country_code, "de")
```

Wird durchgereicht an `generate_full_report(..., locale=locale)`.

### 3.3 Template-Migration

Bestehende Templates haben Strings hartkodiert in Deutsch. Beispiel
aus `cover.html`:

```html
<h1>Bodenbericht</h1>
<p>Adressgenaue Auswertung satellitengestützter Bodendaten</p>
```

Wird zu:

```html
<h1>{{ _("Bodenbericht") }}</h1>
<p>{{ _("Adressgenaue Auswertung satellitengestützter Bodendaten") }}</p>
```

Längere Blöcke nutzen `{% trans %}…{% endtrans %}`. Variable
Inhalte:

```html
{% trans address=address %}
Bericht für {{ address }}
{% endtrans %}
```

### 3.4 Tests

- Unit-Test pro neuer Locale-Datei: `messages.mo` parst, alle Keys
  haben Übersetzung, keine `msgstr ""` für freigegebene Strings
- Integration-Test: `generate_full_report(..., country_code="nl")`
  produziert ein PDF, dessen Cover „Bodemrapport" enthält und nicht
  „Bodenbericht"
- Visual-Regression-Test auf NL-PDF separat (eigene Baselines)

---

## 4. Reihenfolge der Arbeit (Vorschlag)

| Phase | Inhalt | Aufwand |
|---|---|---|
| **0. Setup** | Babel installieren, locale/-Verzeichnis anlegen, Jinja-Env mit i18n-Extension verdrahten, Locale-Routing in leads.py + reports.py | 1 h |
| **1. Cover + Disclaimer** | `cover.html` + globale Disclaimer-Texte aus `full_report.py` extrahieren + NL übersetzen. Smoke-Test: PDF mit `country_code="nl"` rendert NL-Cover | 1 h |
| **2. Sektion 1 (Bodenbewegung)** | wichtigste Sektion, Erstkontakt für den Käufer | 1 h |
| **3. Sektionen 2–11** | restliche Sektionen, sequenziell. Übersetzung von ~250 Strings | 3–5 h, in Häppchen aufteilbar |
| **4. Visuals** | 6 SVG-Komponenten mit Texten (Histogramm-Achsen, Radar-Labels, Map-Legend) | 1 h |
| **5. Mails** | `email_service.py` HTML + plaintext für NL-Empfänger | 30 Min |
| **6. Sektion 12 (Einschätzung)** | Synthese-Sektion mit dynamischen Formulierungen, am tückischsten weil viele Variablen-Interpolationen | 1 h |
| **7. QA** | Vier verschiedene Test-Adressen rendern (NL Stadt, NL Land, DE Vergleich), PDF-Lesetest, Lektorat | 1 h |

**Total realistisch: 8–10 h**, davon ~50 % reine Übersetzungsarbeit
(braucht NL-Sprachgefühl, kein blosses DeepL).

---

## 5. Übersetzungs-Qualitäts-Hinweis

NL-Vokabular für unseren Kontext ist **fachsprachlich heikel**:

| DE | NL — *richtig* | NL — falsch (falscher Freund) |
|---|---|---|
| Bodenbericht | Bodemrapport | „Grondrapport" wäre umgangssprachlich |
| Bodensenkung | Bodemdaling | „Bodemzakking" wäre eher Setzung |
| Schwermetalle | Zware metalen | — |
| Mess-Punkte (PSI) | Meetpunten | „Meetpunten" ist Standard, „PSI-Punten" für Fach |
| Bergbau | Mijnbouw | — |
| Hochwasser | Overstromingsrisico | — |
| Altlasten | Bodemverontreiniging / Wbb-Locaties | „Oude lasten" wäre wörtlich-falsch |

**Empfehlung:** entweder NL-Muttersprachler engagieren (3–4 Stunden
Lektorat), oder DeepL Pro für die Erstübersetzung + manuell durch
die Tabelle oben gegenchecken. Auf keinen Fall Standard-DeepL
benutzen, der streut Fehler in juristisch sensiblen Passagen
(Disclaimer, BBodSchV-Verweise).

---

## 6. Was VOR Phase 0 erledigt sein muss

- [ ] Stripe customer-facing live (sonst gibt es keine NL-Kunden, die
  den NL-Bericht überhaupt sehen würden)
- [ ] Erste 3–5 NL-Pilotkäufer als Validation, dass der Markt
  überhaupt zugreift
- [ ] Entscheidung: NL-Pricing 29 € bestätigt
- [ ] FunderConsult als Affiliate angefragt? Oder eigene NL-Sub-Landing
  unter `/nl/`?

Solange diese Vorbedingungen offen sind, lohnt der i18n-Sprint nicht.
Erst der Trigger, dann der Sprint.

---

## 7. Wenn die Session startet — Quick-Start für eine neue Claude-Session

```bash
cd ~/Projects/geoforensic-app
git checkout -b claude/nl-i18n-sprint
# Phase 0
cd backend && uv pip install --python .venv/bin/python Babel
mkdir -p locale/{de,nl}/LC_MESSAGES
# Babel-Konfig
cat > babel.cfg <<'EOF'
[python: app/**.py]
[jinja2: templates/**.html]
[jinja2: templates/**.jinja2]
extensions=jinja2.ext.i18n
EOF
# Strings extrahieren (passiert nach erstem Marken im Template)
.venv/bin/pybabel extract -F babel.cfg -o locale/messages.pot .
.venv/bin/pybabel init -i locale/messages.pot -d locale -l nl
.venv/bin/pybabel init -i locale/messages.pot -d locale -l de
# Übersetzen ...
.venv/bin/pybabel compile -d locale
```

Plan dann durchgehen, Sektion für Sektion mit dem Operator.

---

*Dieses Dokument wurde am 2026-05-03 als Defer-Plan angelegt, nachdem
der Operator-Sprint heute schon mehrere andere Items abgearbeitet hatte
und NL-i18n als zu groß für eine "Tail-of-Day"-Aufgabe identifiziert
wurde.*
