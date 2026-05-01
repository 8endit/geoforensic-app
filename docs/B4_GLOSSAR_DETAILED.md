# B.4 Glossar — Detail-Plan zur direkten Ausführung

**Stand:** 2026-05-01, nach B.6-Deploy. Self-contained für Wiederaufnahme
in neuer Session — eine fremde Claude-Session liest dieses Doc und
kann mit der Erstellung der ersten Glossar-Page anfangen.

**Bezug:** `docs/SEO_BRANDING_ROLLOUT_PLAN.md` §B.4. Dieser Plan
erweitert die ursprünglich 5 Terms auf **8 Terms**, weil mit dem
Glossar-Pattern der Aufwand pro zusätzlicher Page klein ist und mehr
Terms breitere Topical Authority schaffen.

---

## 1. Voraussetzung — was vorher fertig sein muss

- [ ] B.6-Commit `de03a6a` ist auf VPS deployed (`git pull --ff-only` in `/opt/bodenbericht`)
- [ ] Alle vier Audience-Pages live (Käufer / Garten / Bauträger / Landwirte)
- [ ] Tailwind-Build funktioniert (`landing/tailwindcss.exe -c tailwind.config.js -i input.css -o tailwind.css --minify`)
- [ ] IndexNow-Hook funktioniert (`python landing/scripts/index_now.py --dry-run`)

Wenn etwas davon nicht zutrifft: zuerst Phase-B-State checken, ggf.
deployen, dann B.4 starten.

---

## 2. Strategie — warum 8 statt 5

Domenicos ursprünglicher Vorschlag waren 5 Terms. Wir haben in der
Strategie-Diskussion auf 8 erweitert weil:

1. Pro zusätzlichem Glossar-Eintrag wächst der „Topical Authority"-
   Faktor bei Google quasi linear, der Aufwand aber unterlinear (das
   Pattern, der Header, der Footer, die Cross-Links wiederholen sich)
2. Mit 8 Terms decken wir alle vier Audience-Segmente mindestens
   doppelt ab — jede Sub-Landing hat 2-3 Glossar-Einträge zum
   Querverlinken, was die internen Link-Wege multipliziert
3. Long-tail-Suchen (Google-Phrasen wie „LAGA Z-Werte Aushub Kosten"
   oder „BBodSchV Schwellwerte Cadmium") landen heute auf
   Behörden-PDFs ohne Konversionspfad — wir können dort ranken

Pro Page strikt: 700–900 Wörter visible body, dichte Datenpunkte,
keine ChatGPT-Marketing-Sprache.

---

## 3. Die 8 Glossar-Einträge im Detail

Ausführungs-Reihenfolge ist nicht zwingend — alle 8 sind unabhängig
voneinander, können aber in vier Paaren parallel bearbeitet werden.
Empfohlene Reihenfolge: höchste Such-Volumina zuerst.

### G.1 `/wissen/altlast`

**Title:** „Was ist eine Altlast? — Definition, Recht, Konsequenzen | Bodenbericht" (~70 chars, ggf. kürzen)
**Meta-Desc (140-160 chars):** „Eine Altlast ist eine Bodenkontamination aus historischer Nutzung, die nach BBodSchG §2 sanierungsbedürftig sein kann. Hier: Verdachtsfläche, Ablauf, Käuferhaftung."
**Hero-Definition (Google-Snippet-Target, 1-2 Sätze):**
> Eine Altlast ist eine Verunreinigung des Bodens oder Grundwassers durch frühere gewerbliche, militärische oder landwirtschaftliche Nutzung, die nach §2 Bundes-Bodenschutzgesetz Gesundheits-, Umwelt- oder Sachschäden verursachen kann. Der Begriff umfasst sowohl bestätigte Kontaminationen (Altlasten im engeren Sinn) als auch Verdachtsflächen, bei denen ein Eintrag aus der Vornutzung wahrscheinlich, aber noch nicht analytisch nachgewiesen ist.

**Hauptsektionen (jeweils ein H2 + 2-3 H3):**
1. **Rechtliche Definition** — BBodSchG §2 Abs. 5, Unterscheidung Altablagerung / Altstandort, INSPIRE Art 13
2. **Verdachtsfläche vs. echte Altlast** — Stufenkonzept, Phase 1/2/3-Untersuchungen
3. **Wer haftet** — §4 BBodSchG, Verursacher- vs. Zustandsverantwortung, Käufer-Risiken
4. **Wie sie ans Licht kommt** — Standortauskunft der unteren Bodenschutzbehörde, §11 BBodSchG-Auskunftsrecht, was wir als Indikator zeigen
5. **Was tun bei Verdacht** — Flowchart: Auskunft anfordern → Bodenbericht → Phase-1-Untersuchung → Sanierung
6. **Sanierungs-Spannen** — €10k bis €500k+ aus BBodSchV-Vollzugshilfen

**Cross-Links:**
- → `/fuer-immobilienkaeufer.html` (Käufer-Konsequenz)
- → `/fuer-bautraeger.html` (Aushub-Klassifikation)
- → `/fuer-gartenbesitzer.html` (Vornutzungsfrage)
- → `/wissen/bbodschv` (Rechtsgrundlage)
- → `/wissen/schwermetalle-im-boden` (Hauptkontaminanten)

**FAQ (3 Q&As):**
- Was unterscheidet Altlast von Altablagerung?
- Muss der Verkäufer Altlasten offenbaren?
- Wer trägt die Sanierungskosten beim Privatkauf?

---

### G.2 `/wissen/setzung-vs-hebung`

**Title:** „Setzung vs. Hebung im Boden — Ursachen und Sichtbarkeit | Bodenbericht"
**Meta-Desc:** „Setzung ist Absinken, Hebung ist Anheben des Untergrunds. Wir erklären die Ursachen, die Geschwindigkeits-Klassen und wie EGMS-Satelliten beide Bewegungen messen."
**Hero-Definition:**
> Setzung und Hebung sind die zwei Richtungen vertikaler Bodenbewegung. Setzung beschreibt das Absinken des Bodens — typischerweise durch Bergbau-Altschäden, Grundwasserabsenkung, Konsolidierung organischer Schichten oder dynamische Belastung. Hebung beschreibt das Anheben — durch Quellung von Tonmineralien, Auftrieb in Bergsenkungsgebieten nach Wassereinstauung oder Frosteinwirkung. Beide Bewegungen sind meistens langsam (1-10 mm pro Jahr) und mit bloßem Auge nicht erkennbar.

**Hauptsektionen:**
1. **Setzungs-Mechanismen** — Bergbau (Steinkohle, Braunkohle, Salz), Grundwasser-Förderung, organische Konsolidierung (Marsch, Moor)
2. **Hebungs-Mechanismen** — Quellton (Smektit, Ettringit), Bergsenkungs-Rebound, Hebung in NL durch Gas-Förderung-Stop
3. **Geschwindigkeits-Klassen** — <2 mm/a unauffällig, 2-5 mm/a auffällig, >5 mm/a signifikant (übernommen aus EGMS-Klassifikation)
4. **Wie EGMS misst** — Sentinel-1 Radar-Interferometrie, 6-12-Tage-Wiederholung, Millimeter-Auflösung
5. **Was es im Bauwesen bedeutet** — Risse-Bildung, Tiefgründung-Notwendigkeit, statische Folgen
6. **Risikogebiete in DE** — Lausitz/Mitteldeutschland (Braunkohle-Reviere), Ruhrgebiet (Steinkohle), Norddeutsche Tiefebene (Marsch), Hamburg-Wilhelmsburg

**Cross-Links:**
- → `/fuer-immobilienkaeufer.html`
- → `/fuer-bautraeger.html`
- → `/wissen/insar-egms` (Mess-Methode)

**FAQ:**
- Ab welcher mm/Jahr-Geschwindigkeit wird es kritisch?
- Kann mein Haus betroffen sein, ohne dass ich es merke?
- Wie unterscheidet sich Setzung von Erdbebenaktivität?

---

### G.3 `/wissen/eu-bodenrichtlinie`

**Title:** „EU-Bodenrichtlinie 2025/2360 — Die 16 Descriptoren | Bodenbericht"
**Meta-Desc:** „Die EU-Bodenmonitoring-Verordnung 2025/2360 etabliert 16 Descriptoren für den Bodenzustand. Umsetzungsfrist Dezember 2028. Hier alle Descriptoren erklärt."
**Hero-Definition:**
> Die EU-Bodenmonitoring-Verordnung 2025/2360 (Soil Monitoring Law) ist eine im Frühjahr 2025 verabschiedete EU-Verordnung, die erstmals einen verbindlichen Rahmen für die Erfassung und Bewertung des Bodenzustands in allen EU-Mitgliedstaaten schafft. Mitgliedstaaten haben sie bis Dezember 2028 in nationales Recht umzusetzen. Sie definiert 16 Descriptoren — von Erosion über Verdichtung bis Schwermetallbelastung — die für jede Bodenfläche regelmäßig erhoben und gegen Schwellwerte abgeglichen werden müssen.

**Hauptsektionen:**
1. **Worum es geht** — Hintergrund, EU Soil Strategy 2030, politischer Kontext
2. **Die 16 Descriptoren** — Tabellarisch aufgelistet (Erosion, SOC-Verlust, Versalzung, Verdichtung, Versiegelung, Schwermetalle, Pestizide, etc.)
3. **DE-Umsetzungsfrist** — Dezember 2028, Bezug zu BBodSchV-Novelle
4. **Was es für Eigentümer bedeutet** — keine direkte Pflicht, aber Erhöhung des Informations-Drucks
5. **Was es für Landwirte bedeutet** — GAP-Konditionalität wird sich ankoppeln
6. **Wie wir die Descriptoren liefern** — Mapping auf unsere 13 Datenquellen

**Cross-Links:**
- → `/fuer-landwirte.html` (Compliance-Implications)
- → `/datenquellen.html` (Mapping)
- → `/wissen/erosion-rusle`
- → `/wissen/schwermetalle-im-boden`

**FAQ:**
- Wann müssen Eigentümer reagieren?
- Werden die Descriptoren öffentlich einsehbar?
- Gilt das auch für die Schweiz?

---

### G.4 `/wissen/schwermetalle-im-boden` (SAMMELSEITE)

**Title:** „Schwermetalle im Boden — Cd, Pb, As, Hg, Cu, Ni, Zn | Bodenbericht"
**Meta-Desc:** „Sieben Schwermetalle, die im Boden relevant werden: Cadmium, Blei, Arsen, Quecksilber, Kupfer, Nickel, Zink. Quellen, BBodSchV-Schwellen, Sanierung."
**Hero-Definition:**
> Schwermetalle im Boden sind metallische Elemente, die ab definierten Konzentrationen Gesundheits- und Umweltrisiken verursachen — sieben sind nach BBodSchV §4 für deutsche Böden besonders relevant: Cadmium, Blei, Arsen, Quecksilber, Kupfer, Nickel und Zink. Anders als organische Schadstoffe bauen sich Schwermetalle nicht ab; einmal eingelagert, bleiben sie im Oberboden über Jahrzehnte messbar.

**Hauptsektionen — eine pro Metall, plus Querschnitt:**
1. **Cadmium (Cd)** — Quellen (Phosphat-Dünger, Klärschlamm, Reifenabrieb), Schwellwert BBodSchV 1,3 mg/kg, Pflanzen-Aufnahme (besonders Blattgemüse), Gesundheit
2. **Blei (Pb)** — Quellen (verbleites Benzin bis 1996, Schmieden, Schießstände), Schwellwert 70 mg/kg, persistent im Oberboden
3. **Arsen (As)** — natürlich erhöht in Schwarzwald/Erzgebirge, Schwellwert 20 mg/kg, Trinkwasser-Risiko
4. **Quecksilber (Hg)** — Schwellwert 1 mg/kg, Quellen (Chloralkali-Industrie, Goldbergbau historisch)
5. **Kupfer (Cu)** — Schwellwert 60 mg/kg, Quellen (Weinbau, Schweinemast)
6. **Nickel (Ni)** — Schwellwert 70 mg/kg, geogen erhöht in Serpentinit-Gebieten
7. **Zink (Zn)** — Schwellwert 200 mg/kg, ubiquitär (Reifenabrieb, Zink-Dächer)
8. **Sanierungs-Optionen** — Bodenaustausch, Phytoremediation, Immobilisierung — Spannen 10k-500k €

**Cross-Links:**
- → `/fuer-gartenbesitzer.html` (Pflanzen-Aufnahme)
- → `/fuer-landwirte.html` (Düngeverordnung)
- → `/wissen/altlast`
- → `/wissen/bbodschv` (Rechtsgrundlage Schwellwerte)

**FAQ:**
- Welche Schwermetalle nehmen Pflanzen am stärksten auf?
- Sind Schwellwerte Verbots- oder Maßnahmewerte?
- Wie sanieren bei einer auffälligen Ampel?

**Wichtig:** Diese Page hat sieben Anker-Links (`#cadmium`, `#blei` etc.), damit Nutzer aus Suchen wie „Cadmium Boden Grenzwert" direkt zur richtigen Sektion springen.

---

### G.5 `/wissen/insar-egms`

**Title:** „InSAR und EGMS — Bodenbewegung per Satellit messen | Bodenbericht"
**Meta-Desc:** „InSAR ist die Radarinterferometrie, EGMS der EU-Service. Wie Sentinel-1-Satelliten Millimeter-genaue Bodenbewegung messen — für jede Adresse in Europa."
**Hero-Definition:**
> InSAR (Interferometric Synthetic Aperture Radar) ist eine satellitengestützte Messtechnik, die Bewegungen der Bodenoberfläche durch Vergleich aufeinanderfolgender Radar-Aufnahmen ermittelt. Der EU-Dienst EGMS (European Ground Motion Service) wendet InSAR auf das Sentinel-1-Satellitenpaar an und liefert seit 2022 für jeden Punkt der EU eine Zeitreihe der Bodenbewegung mit Millimeter-Genauigkeit und 6-12-Tage-Wiederholung.

**Hauptsektionen:**
1. **Wie Radar-Interferometrie funktioniert** — Phasenvergleich, Wellenlänge C-Band 5,6 cm
2. **Sentinel-1** — ESA-Satellitenpaar, 2014 + 2016 gestartet, Wiederholungs-Geometrie
3. **EGMS L1/L2/L3** — Datenebenen, was öffentlich verfügbar ist
4. **Datendichte** — typisch 50-80 Punkte pro 500m-Radius im urbanen Umfeld
5. **Was es kann / nicht kann** — Stärken (flächendeckend, Millimeter, regelmäßig); Grenzen (Wald + Wasser-Bedeckung schwierig, keine horizontale Bewegung in N-S)
6. **Vergleich mit Inklinometer** — Bauwerks- vs. Bodenbewegung

**Cross-Links:**
- → `/wissen/setzung-vs-hebung`
- → `/datenquellen.html` (EGMS-Eintrag)
- → `/fuer-immobilienkaeufer.html` und `/fuer-bautraeger.html`

**FAQ:**
- Wie oft werden die EGMS-Daten aktualisiert?
- Funktioniert das auch in der Niederlande?
- Wie genau ist die Messung am Einzelgebäude?

---

### G.6 `/wissen/hochwasser-risikoklasse` (NEU, nicht in Domenicos Liste)

**Title:** „Hochwasser-Risikoklassen HQ_häufig, HQ_100, HQ_extrem | Bodenbericht"
**Meta-Desc:** „Drei Hochwasser-Szenarien nach EU-HWRM-Richtlinie. Was sie bedeuten, welche Auflagen sie auslösen, wie Versicherer und Bauämter sie verwenden."
**Hero-Definition:**
> Hochwasser-Risikoklassen sind drei statistische Szenarien, die die EU-Hochwasserrisikomanagement-Richtlinie für jede Fläche in Mitgliedstaaten vorsieht — HQ_häufig (Wiederkehr 10-25 Jahre), HQ_100 (100 Jahre) und HQ_extrem (200+ Jahre, oft 1.000-jährliches Ereignis). In Deutschland werden sie von der Bundesanstalt für Gewässerkunde gepflegt und sind die Grundlage für Bauamts-Auflagen, Versicherungsprämien und seit 2025 die politische Diskussion um eine Pflichtversicherung für Elementarschäden.

**Hauptsektionen:**
1. **Die drei Szenarien** — statistische Definition, Praxis-Bedeutung
2. **EU-HWRM-Richtlinie 2007/60/EG** — rechtlicher Rahmen
3. **Bauamts-Auflagen** — angehobene EG-OK, Rückstauschutz, dichte Kellerwannen
4. **Versicherer-Bezug** — VdS-Klassifikation, Prämien-Effekt, Verweigerungsrisiko
5. **Politische Lage 2025/26** — Pflichtversicherungs-Diskussion
6. **Wie wir prüfen** — BfG WMS-Endpoint, drei Szenarien gleichzeitig

**Cross-Links:**
- → `/fuer-immobilienkaeufer.html`
- → `/fuer-bautraeger.html`
- → `/datenquellen.html`

**FAQ:**
- Wer prüft Hochwasser-Risiken beim Hauskauf?
- Beeinflusst HQ_extrem die Versicherbarkeit?
- Was bedeutet die geplante Pflichtversicherung?

---

### G.7 `/wissen/bbodschv` (NEU)

**Title:** „BBodSchV — Bundes-Bodenschutz- und Altlastenverordnung | Bodenbericht"
**Meta-Desc:** „Die BBodSchV regelt Schadstoff-Schwellwerte, Untersuchungs-Stufen und Sanierungs-Pflichten für Böden in Deutschland. Hier alle Schwellen pro Pfad."
**Hero-Definition:**
> Die Bundes-Bodenschutz- und Altlastenverordnung (BBodSchV, BGBl. I 1999/1554, novelliert 2021 und 2023) ist die zentrale Verordnung, die die Schadstoff-Schwellwerte, Untersuchungs-Stufen und Sanierungs-Pflichten für Böden in Deutschland regelt. Sie unterscheidet drei Wirkungspfade — Boden-Mensch (direkter Kontakt + Inhalation), Boden-Pflanze (Aufnahme über Wurzeln) und Boden-Grundwasser (Sickerung) — und definiert für jeden Pfad eigene Prüf-, Maßnahme- und Vorsorgewerte.

**Hauptsektionen:**
1. **Aufbau der Verordnung** — §1-§12, Anhänge mit Schwellwerten
2. **Die drei Pfade** — Boden-Mensch, Boden-Pflanze, Boden-Grundwasser
3. **Prüfwert vs. Maßnahmewert** — wann was passiert
4. **Schwellwerte für die wichtigsten Stoffe** — Tabellen (Cd, Pb, As, Hg, MKW, PAK, BTEX)
5. **Vollzug** — Ländersache, untere Bodenschutzbehörde
6. **Wie wir die Verordnung anwenden** — Mapping LUCAS/SoilGrids gegen Schwellen

**Cross-Links:**
- → `/wissen/altlast`
- → `/wissen/schwermetalle-im-boden`
- → alle 4 Sub-Landings (Käufer + Garten + Bauträger + Landwirte)

**FAQ:**
- Was passiert bei Überschreitung des Maßnahmewerts?
- Sind die Schwellwerte EU-weit gleich?
- Welche Stoffe sind nicht in der BBodSchV?

---

### G.8 `/wissen/erosion-rusle` (NEU)

**Title:** „RUSLE-Erosionsmodell — R · K · LS · C · P erklärt | Bodenbericht"
**Meta-Desc:** „RUSLE ist das Standardmodell für Boden-Erosion durch Wasser. Fünf Faktoren — R, K, LS, C, P — beschreiben Niederschlag, Erodibilität, Hang, Bedeckung, Schutz."
**Hero-Definition:**
> Die Revised Universal Soil Loss Equation (RUSLE) ist seit 1997 das international anerkannte empirische Modell zur Schätzung des langfristigen Bodenabtrags durch Wasser-Erosion. Sie multipliziert fünf dimensionslose oder physikalische Faktoren — R für Niederschlagserosivität, K für Bodenerodibilität, LS für Hangneigung × Hanglänge, C für Bodenbedeckung, P für Erosions-Schutzmaßnahmen — und liefert das Ergebnis in Tonnen pro Hektar pro Jahr.

**Hauptsektionen:**
1. **Die fünf Faktoren im Detail** — pro Faktor: Was er misst, woher Daten kommen, typische Wertebereiche
2. **R-Faktor in Deutschland** — ESDAC Panagos 2015, lat-linear-Approximation
3. **Wie LUCAS und SoilGrids in K einfließen**
4. **GLÖZ-5-Bezug** — GAP-Konditionalität verlangt RUSLE-Argumentation
5. **Was wir liefern** — adress-genaue R, K, LS, plus Annahmen für C/P

**Cross-Links:**
- → `/fuer-landwirte.html` (GAP)
- → `/fuer-bautraeger.html` (Erosionsschutz im Bauantrag)
- → `/wissen/eu-bodenrichtlinie`

**FAQ:**
- Ab welcher t/ha/a wird Erosion problematisch?
- Wie wirkt Bodenbedeckung quantitativ?
- Reicht RUSLE für die GLÖZ-5-Argumentation?

---

## 4. Index-Seite `/wissen/`

**URL:** `/wissen/index.html` (oder via Server-Routing auf `/wissen/`)
**Title:** „Wissen — Glossar zu Boden, Recht und Daten | Bodenbericht"
**Meta-Desc:** „Glossar mit den wichtigsten Begriffen rund um Bodenrisiken: Altlast, Setzung, EU-Bodenrichtlinie, Schwermetalle, InSAR, Hochwasserklassen, BBodSchV, RUSLE."

**Layout:** Hero (Definition was das Glossar ist) + Grid mit 8 Karten (eine pro Term, mit Eyebrow + H3 + 1-Satz-Definition + „Mehr erfahren →"-Link).

**JSON-LD:** `CollectionPage` mit `hasPart`-Liste aller 8 `DefinedTerm`s.

---

## 5. Strukturelles Pattern (gilt für alle 8 Pages)

### 5.1 Header / Footer

Header: gleicher Pattern wie B.6-Pages (Logo, Nav „So funktioniert's
| Für Käufer | Leistungen | Datenquellen | FAQ", CTA „Bericht
anfordern"). Kein Glossar-Switcher in der Hauptnav — die Pages sind
zu spezifisch für Hauptnav-Vermarktung.

Footer: das aktuelle „Für wen / Service / Rechtliches"-Pattern. Im
Service-Block neuen Eintrag „Wissen" hinzufügen (zwischen „Datenquellen"
und „Risikocheck-Quiz").

### 5.2 JSON-LD

Pro Page drei Schema-Blöcke:

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {"@type": "BreadcrumbList", "itemListElement": [
      {"@type": "ListItem", "position": 1, "name": "Bodenbericht", "item": "https://bodenbericht.de/"},
      {"@type": "ListItem", "position": 2, "name": "Wissen", "item": "https://bodenbericht.de/wissen/"},
      {"@type": "ListItem", "position": 3, "name": "<Term-Name>", "item": "<URL>"}
    ]},
    {"@type": "DefinedTerm",
     "name": "<Term-Name>",
     "description": "<Hero-Definition>",
     "inDefinedTermSet": "https://bodenbericht.de/wissen/",
     "url": "<URL>"
    },
    {"@type": "FAQPage",
     "mainEntity": [{"@type": "Question", "name": "...", "acceptedAnswer": {"@type": "Answer", "text": "..."}}, ...]
    }
  ]
}
```

**Wichtig:** Wegen JSON/Unicode-Falle (siehe Phase A): alle deutschen
typografischen Anführungszeichen im JSON müssen `„...“` (U+201E +
U+201C) sein, nicht ASCII `"..."`. Sonst Parse-Error.

### 5.3 Hero-Pattern

Identisch zu B.6:
- Hero-Gradient
- Breadcrumb (3 Ebenen statt 2)
- Eyebrow „Glossar / Wissen"
- H1 = Term-Name
- 1-2 Sätze Definition (Google-Snippet-Target)
- Optional: kein CTA-Button hier — der CTA kommt am Ende

### 5.4 Body-Pattern

`max-w-3xl` statt `max-w-4xl` für Lesbarkeit (Glossar-Pages sind
text-lastig, nicht visual-lastig). Eine Sektion pro H2, klar nummeriert.

### 5.5 Cross-Link-Block

Am Ende vor der FAQ:

```html
<aside class="bg-gray-50 border border-gray-200 rounded-2xl p-6 my-12">
  <p class="text-xs uppercase tracking-wide font-bold text-brand-700 mb-3">Verwandte Begriffe</p>
  <div class="flex flex-wrap gap-2">
    <a href="..." class="...">Term A</a>
    <a href="..." class="...">Term B</a>
  </div>
</aside>
```

### 5.6 CTA am Ende

Nicht so prominent wie auf den Sub-Landings — Glossar-Visitor sind
informations-suchend, nicht conversion-ready. Format:

```html
<section class="py-12 bg-white border-t border-gray-100">
  <div class="max-w-2xl mx-auto px-4 text-center">
    <p class="text-gray-600">Haben Sie eine konkrete Adresse, für die diese Faktoren relevant sind?</p>
    <a href="/index.html#cta" class="...">Bericht für Ihre Adresse anfordern →</a>
  </div>
</section>
```

Kein eigenes Lead-Form auf Glossar-Pages. Conversion läuft über Klick
zur Hauptseite.

---

## 6. Cross-Update-Checkliste (am Ende, vor Commit)

- [ ] `landing/sitemap.xml` — 9 neue Einträge (8 Terms + Index), priority 0.6 (niedriger als Sub-Landings)
- [ ] `landing/tailwind.config.js` — alle 9 neuen Pfade in `content`
- [ ] `landing/tailwindcss.exe -c tailwind.config.js -i input.css -o tailwind.css --minify` neu bauen
- [ ] `landing/index.html` Footer Service-Spalte — „Wissen" Eintrag hinzufügen
- [ ] `landing/llms.txt` — neue Sektion mit Glossar-Links
- [ ] JSON-LD-Validation: `python -c "import json; ..."` für alle 9 Pages
- [ ] Tailwind-Klassen-Check — alle neu verwendeten Klassen existieren in `tailwind.css`

---

## 7. Hand-off — Wie eine neue Session damit startet

**Empfohlene erste Anweisung an Claude:**

> Lies `docs/B4_GLOSSAR_DETAILED.md`. Bestätige dass du den Plan
> verstehst. Beginne mit G.1 `/wissen/altlast` — schreib die Page
> komplett mit Header, Hero, Body, Cross-Link-Block, FAQ und CTA
> nach Section §5. Vorher: stelle sicher dass B.6 (`de03a6a`) auf
> dem VPS deployed ist.

**Voraussetzungen für Wiederaufnahme:**
- Repo lokal: `C:/dev/geoforensic-app/`
- Preview-Server läuft auf `localhost:8001` (oder neu starten)
- VPS-SSH-Zugang nicht zwingend nötig (Push reicht, User deployt selbst)
- Tailwind-CLI verfügbar (`landing/tailwindcss.exe`)

**Datenquellen-Wahrheit für Inhalte:**
- `docs/DATA_PROVENANCE.md` — verifizierte Datenquellen pro Modul
- `landing/datenquellen.html` — Live-Übersicht der 13 Quellen
- `backend/app/soil_directive.py` — Code-Referenz für die 16 EU-Descriptoren
- `backend/app/altlasten_data.py` — DE/NL Altlasten-Logik
- `backend/app/full_report.py` — Vollbericht-Sektionen-Mapping

**Was NICHT mehr im Scope von B.4:**
- B.5 Provenexpert (Ops-Aufgabe für User, nicht Code)
- Backend-Änderungen (kein neuer Source-Routing nötig — Glossar nutzt nur Hauptseiten-CTA)
- Tracking-Änderungen (Glossar-Pages routen via Hauptseite, kein eigenes utm_content nötig)

---

## 8. Akzeptanz-Checkliste (Phase B abgeschlossen wenn alle Häkchen)

- [ ] 8 Glossar-Seiten + Index-Seite live auf bodenbericht.de
- [ ] Alle 8 Pages haben validen DefinedTerm + BreadcrumbList + FAQPage Schema
- [ ] Cross-Link-Graph: jeder Term hat 3-5 Links zu anderen Terms oder Sub-Landings
- [ ] Sitemap mit allen 9 neuen URLs
- [ ] IndexNow-Push erfolgreich für alle 9 URLs (`python landing/scripts/index_now.py`)
- [ ] Lighthouse mobile auf 1-2 stichprobenartig: Performance ≥ 95, A11y ≥ 90, BP 100, SEO 100
- [ ] Footer-Update auf allen Hauptseiten enthält „Wissen"-Link
- [ ] llms.txt enthält Glossar-Sektion
- [ ] Word-Count visible body pro Page: 700-900 Wörter
- [ ] JSON-LD-Quotes-Falle vermieden (nur U+201E/U+201C in JSON-Strings)

Wenn alle 10 Häkchen — Phase B ist offiziell durch (zusammen mit
B.5 das beim User liegt).
