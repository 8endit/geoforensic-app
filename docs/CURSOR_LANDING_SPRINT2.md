# Cursor-Task: Sprint 2 — Zielgruppen-Fokus auf Immobilienkäufer

**Ziel:** Task #05 aus dem Developer Brief von Domenico (Capihold GmbH,
2026-04-17) umsetzen. Betrifft nur [landing/index.html](../landing/index.html)
und ist rein Copy-Rewrite — keine neuen Features, keine Backend-Änderungen.

**Dieser Plan ist bindend.** Nicht interpretieren, nicht erweitern, nicht neue
Features dazudichten. Bei Unklarheit → zurückfragen.

**Grundlage:** `C:\Users\weise\Desktop\projekt\geo\Bodenbericht_Developer_Brief.pdf`
(Task #05 und begleitend #06 SEO-H2).

**Kontext — was bereits erledigt ist (nicht nochmal anfassen):**
- Task #01 (Widerrufsbelehrung, Footer-Links) — erledigt in Commit c935393
- Task #04 (BBodSchG §9 → §18) — erledigt in Commit c935393
- Task #07 (Secondary Quiz-CTA) — erledigt in Commit c935393
- Task #02 (Hero-Inline-Formular) — erledigt parallel zu diesem Plan
- Task #03 (Testimonials volle Namen) — Markus Köhler / Sandra Brandt /
  Thomas Heinen sind gesetzt; die Rollen-/Kontext-Zeilen sind Teil von #05

---

## Task #05 — Zielgruppen-Fokus auf Immobilienkäufer

### Problem

Aktuell spricht die Landing drei Zielgruppen gleichwertig an: Hauskäufer,
Gartenbesitzer, Landwirte. Laut Brief: "verwässerte Ansprache reduziert die
Conversion für alle drei." Primäre Zielgruppe soll **Immobilienkäufer** werden
(höchste Zahlungsbereitschaft, höchste emotionale Dringlichkeit, passt zu
Premium-Feature-Plan).

### Umsetzung — Copy-Rewrite in `landing/index.html`

#### 5.1 Badge oberhalb der Headline

Textzeile ca. **Zeile 141**:

**Alt:** `Wissenschaftlich fundierte Bodenanalyse`

**Neu:** `Bodenrisiko-Screening für Immobilienkäufer`

#### 5.2 H1 Headline

Block ca. **Zeile 145–150**:

**Alt:**
```
Sicherheit für Ihren Boden.
Schützen Sie, was Ihnen wichtig ist.
```

**Neu:**
```
Bodenrisiken prüfen, bevor Sie unterschreiben.
Klarheit für Ihre Kaufentscheidung.
```

Das Gradient-Styling auf Zeile 2 (`bg-gradient-to-r from-brand-300 to-brand-400
bg-clip-text text-transparent`) beibehalten.

#### 5.3 SEO-H2 direkt unter der H1 einfügen (bundled Task #06)

**Neu einzufügen** zwischen der bestehenden H1 und dem bestehenden
`<p class="mt-6 ...">` Sub-Headline-Absatz:

```html
<h2 class="mt-4 text-lg md:text-xl text-gray-300 font-medium max-w-3xl mx-auto">
  Altlasten-, Setzungs- und Schwermetall-Screening für Ihr Grundstück —
  in wenigen Minuten, auf Basis offizieller EU-Daten.
</h2>
```

**Begründung:** Deckt Suchbegriffe "Altlasten Grundstück prüfen", "Setzungen
Grundstück", "Bodengutachten vor Hauskauf" ab. Auf genau eine H1 achten — kein
zweites `<h1>` einbauen.

#### 5.4 Sub-Headline umformulieren

Der bestehende `<p class="mt-6 ...">` Absatz direkt unter der H2:

**Alt:**
> Datenscreening Ihres Standorts in wenigen Minuten: **Bodenbewegung** aus
> Satellitendaten, **regionale Schwermetall-Hintergrundwerte** und
> **Bodenqualität**. So können Sie einordnen, ob eine genauere Beprobung
> sinnvoll ist.

**Neu:**
> Automatisiertes Screening für Ihre Wunsch-Immobilie — **Setzungen**,
> **Altlasten-Hinweise** und **Bodenqualität** auf Basis offizieller EU-Daten.
> Ergebnisse in wenigen Minuten, rechtzeitig vor dem Notartermin.

Die `<strong class="text-white font-medium">` Tags um die drei Keywords
übernehmen.

#### 5.5 Trust-Indikatoren-Zeile unter dem Formular

Aktuell (ca. Zeile 178 ff.): drei Badges `Offizielle EU-Satellitendaten` /
`Ergebnis in wenigen Minuten` / `100% DSGVO-konform`.

**Neu:** Einen vierten Punkt ergänzen:
```
Vor dem Notartermin einsetzbar
```
Gleiches Markup-Pattern (Checkmark-SVG + `<span>`-Text) wie die bestehenden
drei Einträge.

#### 5.6 Testimonials-Sektion

Block ca. **Zeile 480–550** in `landing/index.html`. Fotos
(`/images/testimonials/*.jpg`) und Namen (Markus Köhler, Sandra Brandt,
Thomas Heinen) **bleiben identisch**. Nur die Rollen-/Kontext-Zeilen und die
Zitate werden auf Hauskauf-Kontext umgestellt:

| Foto-ID | Rolle/Kontext (neu) | Zitat (neu) |
|---|---|---|
| markus.jpg | Käufer eines Einfamilienhauses, München · Pilotphase | *(Zitat bleibt)* "Hat uns vor dem Kaufgespräch geholfen, die richtigen Fragen zu stellen. Im Bericht steht klar drin, was er kann und was nicht. Das fand ich seriös." |
| sandra.jpg | Immobilienkäuferin, Hamburg · Pilotphase | "Der Abschnitt mit den regionalen Vergleichswerten war für mich entscheidend. Da wusste ich endlich, wo das Grundstück im Vergleich zur Umgebung steht." |
| thomas.jpg | Käufer eines Landguts, Niedersachsen · Pilotphase | "Gute Datenbasis als Startpunkt für die Bewertung. Ersetzt natürlich keine Vor-Ort-Begutachtung, das wird aber auch so kommuniziert. Das find ich in Ordnung." |

Konkrete Stellen:
- Sandra: `Gartenbesitzerin, Hamburg · Pilotphase` → `Immobilienkäuferin, Hamburg · Pilotphase`
  Plus das Zitat ersetzen.
- Thomas: `Landwirt, Niedersachsen · Pilotphase` → `Käufer eines Landguts, Niedersachsen · Pilotphase`
  Plus das Zitat ersetzen.
- Markus: Rolle auf `Käufer eines Einfamilienhauses, München · Pilotphase`
  präzisieren (bisher `Haussuche, München · Pilotphase`). Zitat bleibt.

#### 5.7 "Warum ein Bodenbericht?" Sektion

Block ca. **Zeile 225–290**. Aktuell drei Themen gleichgewichtet:
- "Hinweise auf frühere Nutzung"
- "Regionale Bodenbelastung verstehen"
- "Setzungen & Bodenbewegung"

**Umstellen auf Hauskauf-Priorisierung** (Reihenfolge neu + Framing):

1. **"Altlasten-Verdacht prüfen vor dem Kauf"** (bisher "Hinweise auf frühere
   Nutzung") — Copy auf "Vor dem Notartermin sichere Antwort, ob das Grundstück
   historisch als Gewerbe/Industrie genutzt wurde" umstellen.
2. **"Setzungen & Bodenbewegung"** (bleibt) — Copy auf Kauf-Relevanz
   umformulieren: "Risse im Bestandsgebäude, statische Reserven beim Umbau —
   Satellitendaten zeigen ob Ihr Zielobjekt stabil ist."
3. **"Bodenqualität regional einordnen"** (bisher "Regionale Bodenbelastung
   verstehen") — Wording umstellen auf "Ihre Wunsch-Immobilie im regionalen
   Vergleich: Schwermetalle, pH, Bodendichte."

Icons, Grid-Struktur und Styling beibehalten.

#### 5.8 Meta-Tags (bundled Task #09)

Im `<head>` von `landing/index.html`:

```html
<title>Bodenrisiken prüfen vor dem Hauskauf – Bodenbericht</title>
<meta name="description" content="Altlasten, Setzungen und Bodenqualität für Ihre Wunsch-Immobilie prüfen — in wenigen Minuten, auf Basis offizieller EU-Satellitendaten. Rechtzeitig vor dem Notartermin.">
<meta property="og:title" content="Bodenrisiken prüfen vor dem Hauskauf | Bodenbericht">
<meta property="og:description" content="Altlasten, Setzungen und Bodenqualität für Ihre Wunsch-Immobilie — in Minuten, auf Basis offizieller EU-Daten.">
```

`og:image`, `twitter:card` und andere Meta-Tags bleiben unverändert.

#### 5.9 Sekundäre Zielgruppen NICHT wegwerfen

Garten- und Landwirt-Use-Cases nicht entfernen, aber visuell nachordnen:

**Option 1 (umzusetzen):** Nach der "Warum ein Bodenbericht?"-Sektion einen
schmalen Einzeiler-Block einfügen:

```html
<section class="py-12 bg-gray-50">
  <div class="max-w-4xl mx-auto px-4 text-center">
    <p class="text-sm text-gray-500 uppercase tracking-wide font-semibold mb-3">Auch geeignet für</p>
    <p class="text-gray-600">
      <strong class="text-navy-800">Gartenbesitzer</strong> (Schwermetalle im Gemüseanbau) ·
      <strong class="text-navy-800">Landwirte</strong> (regionale Bodenbelastung) ·
      <strong class="text-navy-800">Bauträger</strong> (Standortprüfung vor Kauf).
      <br>
      <span class="text-xs text-gray-500 mt-2 inline-block">Dedizierte Sub-Landingpages folgen in Q3/2026.</span>
    </p>
  </div>
</section>
```

**Option 2 (NICHT Teil dieses Tasks):** Separate `/garten.html` und
`/landwirtschaft.html` — nur als Kommentar im HTML markieren, nicht umsetzen:
```html
<!-- TODO: Eigene Sub-Landingpages /garten.html und /landwirtschaft.html anlegen -->
```

### Akzeptanzkriterien

- [ ] H1, Sub-Headline und Badge sprechen explizit Immobilienkäufer an
- [ ] Neue H2 direkt unter H1 enthält SEO-Keywords ("Altlasten", "Setzungs",
      "Schwermetall", "Grundstück")
- [ ] Alle 3 Testimonial-Zitate und -Rollen sind aus Hauskäufer-Kontext
- [ ] "Warum ein Bodenbericht?" Sektion priorisiert Hauskauf-Themen (neue
      Reihenfolge: Altlasten → Setzungen → Bodenqualität)
- [ ] Meta-Title und -Description sind auf Hauskauf-Kontext angepasst
- [ ] Sekundäre Zielgruppen (Garten, Landwirtschaft) sind weiterhin erwähnt,
      aber visuell nachgeordnet (kleine grauer Block nach dem Hauptblock)
- [ ] Genau eine H1 auf der Seite, saubere H2-Hierarchie
- [ ] Bilder der Testimonials bleiben identisch (markus.jpg, sandra.jpg,
      thomas.jpg), nur Texte ändern sich
- [ ] `alt`-Attribute der Testimonial-Bilder bleiben Markus Köhler /
      Sandra Brandt / Thomas Heinen
- [ ] Hero-Lead-Form (`#hero-lead-form`) und alle JS-Handler werden nicht
      angefasst — nur Texte davor/darüber ändern

### Was NICHT Teil dieses Tasks ist

- Neue Backend-Endpoints — keine
- Testimonial-Fotos ersetzen — die 3 in `landing/images/testimonials/` bleiben
- Footer-Struktur ändern — nicht anfassen
- Andere Unterseiten (datenquellen, muster-bericht, impressum, datenschutz,
  quiz, widerruf) — nicht anfassen
- Tailwind-Config ändern
- Dependencies neu installieren
- Task #08 (Premium-Warteliste Anreiz) — separater Task, nicht bundled
- Task #10 (Accessibility) und #11 (Performance) — Backlog

### Commit-Richtlinie

- **Ein Commit** für den gesamten #05-Rewrite, Message:
  `feat(landing): sharpen target audience focus on property buyers (task #05)`
- Nach dem Commit: `docker compose restart backend` ist nicht nötig (nur HTML
  geändert, FastAPI-StaticFiles-Mount liefert direkt aus).

Bei Unsicherheit: lieber zurückfragen als eigenmächtig erweitern.
