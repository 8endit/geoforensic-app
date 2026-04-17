# Cursor-Task: Landing Polish & Umlaut-Fix

**Ziel:** Restliche Hygiene-Baustellen auf der Landing schließen. Keine
Feature-Arbeit, keine neuen Seiten, kein Refactoring.

**Dieser Plan ist bindend.** Nicht interpretieren, nicht erweitern, nicht
optimieren. Wenn etwas unklar ist → **zurückfragen**, nicht raten.

---

## 0. Regeln (gelten für alle Tasks)

1. **Nur die hier aufgeführten Dateien bearbeiten.** Alles andere bleibt unangetastet.
2. **Keine Bulk-Regex-Replaces über mehrere Dateien.** Jede Ersetzung wird pro
   Datei einzeln geprüft. Beispiel: `ue` darf NICHT global ersetzt werden,
   weil `Museum`, `neu`, `Quelle` existieren. Nur die in Task 1 **explizit
   gelisteten Wörter** werden ersetzt.
3. **UTF-8 Umlaute verwenden** (ä, ö, ü, ß, §), keine HTML-Entities
   (`&auml;`, `&szlig;`). Die Dateien haben alle `<meta charset="UTF-8">`.
4. **Keine Stilanpassungen**, keine CSS-Änderungen, keine Re-Layouts.
5. **Keine neuen Dependencies** (kein npm install, kein pip install).
6. **Nach jedem Task:** Änderung lokal visuell prüfen (`python -m http.server 8080`),
   bevor zum nächsten Task weiter.
7. **Kein Commit vor Abschluss aller 8 Tasks.** Ein einziger Commit am Ende
   mit der Message aus Abschnitt "Commit" unten.

---

## Task 1 — ASCII-Transliteration zurück zu echten Umlauten und §

**Dateien** (exakt diese 6, nicht mehr):
- `landing/impressum.html`
- `landing/datenschutz.html`
- `landing/404.html`
- `backend/app/email_service.py`

**Ersetzungs-Liste** (exakt, case-sensitive, ganze Wörter):

| Finde | Ersetze durch |
|---|---|
| `Datenschutzerklaerung` | `Datenschutzerklärung` |
| `Anfuelen` / `AUSFUELLEN` | (nicht in Scope) |
| `gemaess` | `gemäß` |
| `Paragraph 5 DDG` | `§ 5 DDG` |
| `Paragraph 7 Abs. 1 DDG` | `§ 7 Abs. 1 DDG` |
| `Paragraphen 8 bis 10 DDG` | `§§ 8 bis 10 DDG` |
| `Paragraph 27 a Umsatzsteuergesetz` | `§ 27a Umsatzsteuergesetz` |
| `Paragraph 25 Abs. 1 TDDDG` | `§ 25 Abs. 1 TDDDG` |
| `Paragraph` (Rest, als einzelnes Wort) | `§` |
| `Geschaeftsfuehrer` | `Geschäftsführer` |
| `fuer` | `für` |
| `ueber` | `über` |
| `Ueberblick` / `Uebersicht` / `Ueberprueung` | `Überblick` / `Übersicht` / `Überprüfung` |
| `uebertragung` / `Uebertragung` / `uebermittelt` | `übertragung` / `Übertragung` / `übermittelt` |
| `uebermitteln` / `uebergeben` / `uebertragbarkeit` | `übermitteln` / `übergeben` / `Übertragbarkeit` |
| `koennen` / `koennten` | `können` / `könnten` |
| `moeglich` / `Moeglichkeit` | `möglich` / `Möglichkeit` |
| `persoenlich` / `persoenliche` | `persönlich` / `persönliche` |
| `ausfuehrlich` | `ausführlich` |
| `auszufuehren` / `Ausfuehrung` | `auszuführen` / `Ausführung` |
| `Ruecksprache` / `Rueckfragen` / `Rueckgang` | `Rücksprache` / `Rückfragen` / `Rückgang` |
| `zurueck` / `Zurueck` | `zurück` / `Zurück` |
| `Laender` / `Laendern` | `Länder` / `Ländern` |
| `gewaehrleisten` / `Gewaehrleistung` | `gewährleisten` / `Gewährleistung` |
| `gemaesse` | `gemäße` |
| `zustaendig` / `Zustaendige` | `zuständig` / `Zuständige` |
| `Aufsichtsbehoerde` / `Behoerde` | `Aufsichtsbehörde` / `Behörde` |
| `Beschaeftigung` | `Beschäftigung` |
| `Verstoesse` / `Verstoss` | `Verstöße` / `Verstoß` |
| `mutmasslich` | `mutmaßlich` |
| `ausserhalb` / `ausschliesslich` | `außerhalb` / `ausschließlich` |
| `grosse` / `Grosse` / `groesser` | `große` / `Große` / `größer` |
| `Strasse` / `Strassenname` | `Straße` / `Straßenname` |
| `Schliessen` / `schliessen` | `Schließen` / `schließen` |
| `Massnahme` / `Massnahmen` | `Maßnahme` / `Maßnahmen` |
| `Standardvertragsklauseln` | (unverändert, hat kein Umlaut-Problem) |
| `Aufloesung` | `Auflösung` |
| `Loeschung` / `loeschen` | `Löschung` / `löschen` |
| `Sachverstaendige` / `sachverstaendig` | `Sachverständige` / `sachverständig` |
| `Erfuellung` | `Erfüllung` |
| `erlaeutert` / `erlaeutern` | `erläutert` / `erläutern` |
| `waehrleisten` | (bereits in "gewährleisten" enthalten) |
| `Endgeraet` | `Endgerät` |
| `Naehrstoffe` | `Nährstoffe` |
| `laedt` / `laeden` | `lädt` / `laden` |
| `Schluessel` / `verschluesselt` / `Verschluesselung` | `Schlüssel` / `verschlüsselt` / `Verschlüsselung` |
| `Haeufig` / `haeufig` | `Häufig` / `häufig` |
| `Taetigkeit` / `taetig` | `Tätigkeit` / `tätig` |
| `Europaeisch` / `europaeisch` / `Europaeische` | `Europäisch` / `europäisch` / `Europäische` |
| `Universalschlichtungsstelle` | (unverändert) |
| `Erfassung` | (unverändert) |

**Arbeitsweise:**
1. Grep auf die Datei nach dem alten String.
2. Kontext prüfen (ist das wirklich ein Wort, oder Teil eines anderen).
3. Nur wenn sicher → ersetzen.
4. Wenn unsicher → in der Datei lassen, ans Ende eine Zeile mit
   `<!-- TODO umlaut-review: <wort> in Zeile X -->` anhängen. NICHT raten.

**Akzeptanzkriterium:**
```bash
# Nach Task 1 ausführen - sollte 0 Treffer haben in den 4 Dateien:
grep -nE '\b(gemaess|Paragraph|fuer|ueber|koennen|moeglich|persoenlich|ausfuehrlich|ruecksprache|zurueck|gewaehrleisten|zustaendig|aufsichtsbehoerde|verstoesse|ausserhalb|ausschliesslich|schliessen|massnahme|Loeschung|sachverstaendig|Endgeraet|Naehrstoffe|Verschluesselung|haeufig|taetigkeit|europaeisch|Aufloesung|Datenschutzerklaerung|Geschaeftsfuehrer|Erfuellung|erlaeutert)\b' landing/impressum.html landing/datenschutz.html landing/404.html backend/app/email_service.py
```

**Sanity-Checks:**
- `grep -c "lang=\"de\"" landing/*.html` sollte weiterhin Treffer zeigen (charset ist da).
- Eine Browser-Vorschau nach dem Fix zeigt echte Umlaute, kein Mojibake wie `Ã¼`.

---

## Task 2 — "versteckte Toxine" aus Quiz-Hero entfernen

**Datei:** `landing/quiz.html`

**Zeile 148** (aktuell):
```html
Finden Sie heraus, ob auf Ihrem Grundstück ein Risiko durch Altlasten, versteckte Toxine oder schlechte Bodenqualität besteht.
```

**Ersetzen durch:**
```html
Finden Sie heraus, wie es um die Bodenbewegung, Bodenqualität und bekannte Risiko-Indikatoren an Ihrem Standort bestellt ist — auf Basis öffentlicher EU-Satelliten- und Bodendaten.
```

**Grund:** "versteckte Toxine" ist eine Aussage, die wir mit unserem Datenscreening
nicht halten können (wir messen keine Toxine am Standort, wir haben LUCAS-Punktdaten
auf regionaler Ebene). Diese Art Claim wurde bereits in Commit `28ac207` auf dem
Rest der Landing entfernt — das hier war übersehen.

**Akzeptanzkriterium:**
```bash
grep -n "Toxine\|versteckte" landing/quiz.html
# Soll 0 Treffer zurückgeben.
```

---

## Task 3 — Doppel-`<h1>` im Impressum zu `<h2>`

**Datei:** `landing/impressum.html`

**Zeile 184** (aktuell):
```html
<h1 style="margin-top:56px">Haftungsausschluss</h1>
```

**Ersetzen durch:**
```html
<h2 style="margin-top:56px; font-size:28px;">Haftungsausschluss</h2>
```

**Grund:** SEO-Best-Practice ist ein `<h1>` pro Seite. "Impressum" ist der
echte H1. "Haftungsausschluss" ist ein Sub-Bereich.

**Akzeptanzkriterium:**
```bash
grep -c "<h1" landing/impressum.html
# Soll genau "1" zurückgeben.
```

---

## Task 4 — Nominatim-Adresse kürzen

**Datei:** `backend/app/routers/reports.py`

**Problem:** Nominatim liefert in `display_name` den kompletten Hierarchie-Pfad,
z.B.:

```
Thomass-Eck, 1, Marienplatz, Kreuzviertel, Altstadt-Lehel, München, Bayern, 80331, Deutschland
```

Das ist für Mail-Subject und Adress-Anzeige zu lang.

**Gewünschtes Format:**
```
Marienplatz 1, 80331 München
```

Also: **Straße + Hausnummer, PLZ + Stadt**. Alles andere (Stadtteil, Bundesland,
Land) weglassen.

**Vorgehen:**

In `reports.py`, Funktion `geocode_address()` (aktuell Zeile 39-94):
die Funktion ruft Nominatim auf und extrahiert `display_name`. Das lassen
wir unverändert (für Rückwärtskompatibilität).

**Neue Helfer-Funktion** direkt nach `geocode_address()` ergänzen:

```python
def _format_postal_address(nominatim_hit: dict) -> str:
    """Format Nominatim hit as 'Street Number, PLZ City'.

    Falls back to display_name if any component is missing.
    """
    addr = nominatim_hit.get("address", {})
    road = addr.get("road", "") or addr.get("pedestrian", "") or addr.get("footway", "")
    house = addr.get("house_number", "")
    postcode = addr.get("postcode", "")
    city = (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("municipality")
        or ""
    )

    street = f"{road} {house}".strip() if road else ""
    locality = f"{postcode} {city}".strip() if (postcode or city) else ""

    if street and locality:
        return f"{street}, {locality}"
    if locality:
        return locality
    return str(nominatim_hit.get("display_name", "")).split(",")[0]
```

**Aufrufer anpassen** — dort wo bisher `display_name` für die Anzeige/Mail
genutzt wird:

1. `reports.py:94` — `geocode_address` gibt ein 4-Tupel zurück:
   `(lat, lon, display_name, country_code)`. **Unverändert lassen**
   (kompatibilitätskritisch).

2. In `reports.py` **zusätzliche** Funktion exportieren, die den Kurz-Form liefert:
   Diese neue Funktion kann in `leads.py` importiert werden.

   **Ansatz:** `geocode_address` um einen zusätzlichen Return-Wert erweitern
   wäre ein Breaking-Change. Stattdessen: neue Funktion `geocode_address_short()`
   die intern dasselbe macht und `_format_postal_address` nutzt. Oder — wenn
   bei der Nominatim-Antwort direkt der address-Dict zurückgegeben wird —
   einfach `addressdetails=1` im Nominatim-Call setzen und in `geocode_address`
   parallel zum Tupel ein "short" zurückgeben.

   **Empfohlener minimaler Eingriff** (um keine Breaking Changes zu produzieren):
   - `geocode_address()` in Zeile 39-94: `params` um `"addressdetails": 1`
     erweitern beim `httpx.get`-Call.
   - Return-Tupel erweitern auf `(lat, lon, display_name, country_code, short_address)`.
   - `_format_postal_address(hit)` beim Return aufrufen.
   - Alle Callsites in diesem Repo anpassen: `reports.py:257, 288`, `leads.py:60`.

3. `leads.py:105` und `leads.py:125` (der `address=display_name` und
   `report_address=display_name`-Call) → `address=short_address` und
   `report_address=short_address`.

**Akzeptanzkriterium:**
Ein Test-Lead für `Marienplatz 1, München` erzeugt eine Mail mit Subject
`Ihr Bodenbericht für Marienplatz 1, 80331 München` (kurz, sauber), nicht
die komplette Nominatim-Kette.

**Was NICHT zu tun ist:**
- `address_input` und `address_resolved` in der DB-Schicht nicht anfassen
  (das ist das Original, darf für Audit-Zwecke detailliert bleiben).
- Keine Migration schreiben.
- Keine bestehenden Leads nachträglich anpassen.

---

## Task 5 — E-Mail-Template auch auf Umlaute umstellen

**Datei:** `backend/app/email_service.py`

**Scope:** Sowohl `_HTML_TEMPLATE` als auch `_build_text_body()` enthalten
aktuell "fuer", "Rueckfragen", "Naehrstoffe" etc. Diese werden im selben
Rutsch mit Task 1 auf echte Umlaute umgestellt.

**Zusätzlich**: Der Charset in der Mail ist bereits UTF-8 (EmailMessage
default), Brevo-Relay kann UTF-8, das Postfach auch. Also risikofrei.

**Akzeptanzkriterium:**
```bash
grep -nE '\b(fuer|ueber|Rueckfragen|Naehrstoffe|persoenlich|koennen|moeglich|gemaess|Paragraph)\b' backend/app/email_service.py
# Soll 0 Treffer zurückgeben.
```

---

## Task 6 — Cookie-Einstellungen-Link im Footer

**Dateien:**
- `landing/index.html` (Footer, bei "Rechtliches"-Spalte)
- `landing/datenquellen.html` (Footer)
- `landing/muster-bericht.html` (Footer)
- `landing/impressum.html` (Footer)
- `landing/datenschutz.html` (Footer)

**Was tun:**
Unter jedem Footer-Link "Datenschutz" einen weiteren Link hinzufügen:

```html
<a href="#" class="hover:text-white transition"
   onclick="event.preventDefault(); if (window.klaro) klaro.show(); else alert('Cookie-Einstellungen wurden noch nicht geladen. Bitte Seite neu laden.');">
  Cookie-Einstellungen
</a>
```

(Bei den 3 Tailwind-HTMLs genau so. Bei den 2 Standalone-HTMLs Impressum/
Datenschutz: CSS-Klasse entsprechend dem bestehenden Footer-Link-Styling
anpassen, nicht das Tailwind-`hover:text-white`.)

**Grund:** DSGVO-konform muss der User seine Consent-Entscheidung jederzeit
widerrufen können. Klaro bietet dafür `klaro.show()`. Der Link muss auf jeder
Seite erreichbar sein.

**Akzeptanzkriterium:**
```bash
grep -c "Cookie-Einstellungen" landing/*.html
# Soll 5+ Treffer zurückgeben (einer pro oben gelisteter Datei).
```

---

## Task 7 — GTM-Snippet von Legal- und 404-Seiten entfernen

**Dateien:**
- `landing/impressum.html`
- `landing/datenschutz.html`
- `landing/404.html`

**Was tun:**
Diese drei Seiten haben aktuell **sowohl** Klaro als auch den GTM-Script-Tag
`<script type="text/plain" ...>`. Der GTM-Tag soll auf diesen Seiten **ganz
raus**.

**Behalten:**
```html
<!-- Klaro consent manager (self-hosted, DSGVO-konform) -->
<script defer src="/klaro/klaro-config.js"></script>
<script defer src="/klaro/klaro.js"></script>
```

**Entfernen** (auf den 3 Seiten):
```html
<!-- Google Tag Manager (laedt erst nach Einwilligung via Klaro) -->
<script type="text/plain" data-type="application/javascript" data-name="google-tag-manager">
(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','GTM-KFG5W96X');
</script>
```

**Grund:** Auf Rechtstext-Seiten (Impressum, Datenschutz) und der Fehler-Seite
hat Analytics-Tracking keinen Mehrwert. Best Practice ist, diese Seiten
tracking-frei zu halten, damit der User sich sicher fühlt beim Lesen der
rechtlichen Informationen. Der Klaro-Manager selbst bleibt auf diesen Seiten,
damit der "Cookie-Einstellungen"-Link im Footer funktioniert.

**Weiterhin GTM laden** auf:
- `landing/index.html`
- `landing/quiz.html`
- `landing/datenquellen.html`
- `landing/muster-bericht.html`
- `landing/admin.html` (oder auch raus, siehe Optional unten)

**Optional (anfragen bevor tun):** Auf `admin.html` den GTM-Tag auch
entfernen — Admin-Seite ist intern, kein Nutzertraffic relevant.

**Akzeptanzkriterium:**
```bash
grep -l "GTM-KFG5W96X" landing/*.html
# Soll auf KEINEN Fall impressum.html, datenschutz.html, 404.html listen.
```

---

## Task 8 — DSE Abschnitt 7 "Analyse-Tools und Einwilligungsmanagement" prüfen

**Datei:** `landing/datenschutz.html`

**Was tun:**
Die DSE hat einen neuen Abschnitt 7 im TOC. Der Inhalt muss folgende
drei Sub-Einträge haben. Falls einer fehlt → nachtragen.

### 7.1 Klaro Consent Manager
- Selbst gehostet auf unseren Servern (Contabo GmbH)
- Keine Übermittlung von Daten an Dritte
- Speichert Einwilligungs-Entscheidung als Cookie `klaro-consent` für 365 Tage
- Rechtsgrundlage: Art. 6 Abs. 1 lit. c DSGVO (gesetzliche Pflicht: DSGVO-Consent)
- Widerruf jederzeit über Footer-Link "Cookie-Einstellungen"

### 7.2 Google Tag Manager
- Anbieter: Google Ireland Limited, Gordon House, Barrow Street, Dublin 4, Irland
- Container-ID: GTM-KFG5W96X
- Lädt nur nach aktiver Einwilligung (Klaro) — Rechtsgrundlage Art. 6 Abs. 1 lit. a DSGVO
- Übertragung in die USA auf Basis DPF / SCC
- Lädt nachfolgend GA4 und PostHog (siehe unten)

### 7.3 Google Analytics 4 (via GTM)
- Anbieter: Google Ireland Limited
- Anonymisiertes Tracking (IP-Kürzung, keine Cross-Site-Erkennung)
- Cookies: `_ga`, `_gid`, `_gat` (Lebensdauer siehe Google-Dokumentation)
- Einwilligung + Widerruf über Klaro
- Rechtsgrundlage: Art. 6 Abs. 1 lit. a DSGVO + § 25 Abs. 1 TDDDG

### 7.4 PostHog (via GTM)
- **Anbieter prüfen:** Ist es PostHog EU (Frankfurt) oder PostHog US Cloud?
  → **Cursor: bitte zurückfragen bei Ben bevor Absatz geschrieben wird.**
  PostHog EU = keine Drittland-Übertragung. PostHog US = DPF/SCC erforderlich.
- Cookie-Pattern: `ph_*`
- Sitzungs-Aufzeichnung (wenn aktiviert): Klarstellung dass Passwort-/Formular-Inputs
  per Default maskiert sind
- Einwilligung + Widerruf über Klaro

**Hinweis am Ende von Abschnitt 7:**
Der alte Abschnitt 6 "Schriften und Skripte" (Inter + Tailwind lokal) bleibt
unverändert. Nicht löschen.

**Akzeptanzkriterium:**
- Abschnitt 7 im TOC korrespondiert mit einer `<h2 id="analyse">` im Body.
- Alle vier Sub-Dienste (7.1–7.4) haben eigene `<h3>`-Überschriften.
- Test-Link im TOC funktioniert (`href="#analyse"` springt zur Überschrift).

---

## Commit

Am Ende aller 8 Tasks **ein einzelner** Commit:

```
git add -A
git commit -m "polish(landing+email): umlauts, GTM scope, consent footer, short address" \
           -m "- Native UTF-8 umlauts (ä ö ü ß §) across impressum, datenschutz, 404, email_service
- quiz.html: 'versteckte Toxine' claim removed (regression from 28ac207)
- impressum: second H1 'Haftungsausschluss' demoted to H2 (SEO)
- reports.py: geocode_address returns short postal form for mail subject
- email body uses short address ('Marienplatz 1, 80331 München')
- Footer: 'Cookie-Einstellungen' link (Klaro.show()) on all 5 landing pages
- GTM snippet removed from impressum.html, datenschutz.html, 404.html (Klaro stays)
- DSE section 7 completed: Klaro + GTM + GA4 + PostHog disclosures"
```

**Nicht pushen.** Ben reviewed den Commit lokal bevor `git push`.

---

## Nicht in Scope (explizit)

- Keine Änderungen an `landing/tailwind.config.js`, `tailwind.quiz.config.js`,
  `input.css`, `build.ps1`.
- Kein Rebuild von `tailwind.css` / `tailwind-quiz.css` — Klassen ändern sich nicht.
- Keine Änderungen an `landing/og-image.png`, `favicon.*`, `sitemap.xml`,
  `robots.txt`, `build_brand_assets.py`.
- Keine Änderungen an `backend/app/html_report.py` (Report-PDF-Design ist
  separater Task).
- Keine Änderungen an `backend/app/email_logo.py`.
- Keine Änderungen an `backend/requirements.txt`.
- Keine Änderungen an `docker-compose.yml` oder `backend/Dockerfile`.
- Keine Stripe/Payment-Änderungen.

---

## Bei Unklarheiten

Wenn eine Ersetzung unklar ist (Kontext könnte Wort verändern) → **nicht
automatisch entscheiden**. Stattdessen in der Datei an der Stelle einen
HTML-Kommentar setzen:

```html
<!-- TODO umlaut-review (Cursor): "ueberwachen" in folgendem Satz prüfen -->
```

Und diese offenen Punkte am Ende als Liste in der Chat-Antwort zusammenfassen.
Ben entscheidet dann.
