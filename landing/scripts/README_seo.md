# SEO-Long-Tail-Stadt-Pages

3-Datei-Setup für Sprint D14 (Marketing-Kanal):

```
landing/scripts/
├── seo_template.html.jinja2   ← Layout (folgt landing/wissen/insar-egms.html)
├── seo_pages.json             ← Daten (Inhalt pro Stadt × Thema)
└── build_seo_pages.py         ← Generator
```

**Output**: `landing/orte/<thema_slug>-<stadt_slug>.html`

## Wer macht was

| Rolle | Aufgabe |
|---|---|
| **Marketing-Claude** (Web-Chat o.ä.) | Inhalte in `seo_pages.json` einpflegen — Stadt für Stadt |
| **Operator** | `python landing/scripts/build_seo_pages.py` ausführen, Pages in Repo commiten, deployen |
| **Backend (live)** | Liefert die Pages über die `landing/`-Static-Mount auf `/orte/<thema>-<stadt>.html` |

## Daten-Schema pro Eintrag

Jeder Eintrag in `pages: [...]` rendert eine Page. Pflichtfelder:

```json
{
  "thema_slug": "bodenbewegung",        // ein Wort, lowercase, kein Sonderzeichen
  "stadt_slug": "bochum",                // entsprechend
  "thema_label": "Bodenbewegung",        // Anzeigeform
  "stadt_name": "Bochum",                // Anzeigeform
  "lat": 51.4818,                        // GeoCoordinates für JSON-LD
  "lon": 7.2162,
  "lang": "de",                          // "de" oder "nl"
  "inLanguage": "de-DE",                 // BCP-47
  "og_locale": "de_DE",                  // OpenGraph

  "seo_title": "...",                    // <title>, max ~60 Zeichen
  "meta_description": "...",             // max ~160 Zeichen
  "og_title": "...",                     // optional, Default = seo_title
  "og_description": "...",               // optional, Default = meta_description

  "eyebrow": "InSAR-Standortauskunft",   // kurzer Lab-Style-Header über H1
  "h1": "Bodenbewegung in Bochum prüfen",
  "hero_intro": "1-2 Sätze, Hook für den Leser",

  "content_sections": [                  // 2-4 Sections empfohlen
    {
      "heading": "1. ...",
      "paragraphs": ["P1 mit <strong>HTML</strong>", "P2"]
    },
    ...
  ],

  "related_links": [                     // optional, schöner mit
    {"href": "/wissen/insar-egms.html", "label": "Wie EGMS misst"},
    ...
  ],

  "faq_items": [                         // optional, sehr schemafreundlich
    {"frage": "...", "antwort": "..."},
    ...
  ],

  "cta_lead": "Haben Sie eine Adresse..."  // optional, Default-Text generisch
}
```

## Themen-Vorschlag (Marketing-Claude legt fest)

In `_themen` im JSON ist nur Doku. Die Themen-Slugs werden direkt aus `thema_slug`
gelesen. Empfohlene 4 Themen:

| `thema_slug` | Passt zu |
|---|---|
| `bodenbewegung` | Bergbau-Städte, Altbergbau, Lockergesteins-Lagen |
| `altlasten` | Industriestädte, Häfen, ehemalige Kasernen |
| `hochwasser` | Flussstädte, Küsten, Senken |
| `funderingslabel` | NL-Holzpfahl-Städte (Amsterdam, Rotterdam, Den Haag, Zaandam, Gouda, Schiedam, Dordrecht) |

## Workflow

```bash
# 1) Inhalte pflegen
$EDITOR landing/scripts/seo_pages.json

# 2) Trockenlauf — was würde geschrieben?
python landing/scripts/build_seo_pages.py --dry-run

# 3) Echtes Rendern
python landing/scripts/build_seo_pages.py

# 4) Sitemap-Snippet für neue URLs ausgeben (manuell in sitemap.xml einkleben)
python landing/scripts/build_seo_pages.py --sitemap

# 5) Commit + Deploy
git add landing/orte/ landing/sitemap.xml landing/scripts/seo_pages.json
git commit -m "feat(seo): pages für ..."
git push
```

## Was Marketing-Claude tun sollte

Die Beispiel-Pages (Bochum, Amsterdam) zeigen Tonfall + Inhaltstiefe. Beim Skalieren auf 30+ Städte:

- **Stadt-spezifischer Hook**: kein „in Stadt X" sondern „warum Stadt X" — historische, geologische, hydrologische Eigenheiten
- **Faktencheck**: keine erfundenen Zahlen. Wenn unsicher → vager formulieren oder weglassen
- **Lokale Behörden** beim Namen nennen (Bezirksregierung Arnsberg für NRW, RAG, KCAF/FunderMaps für NL etc.)
- **Konkurrenz nicht erwähnen** außer wo zwingend (Funderingslabel-Page muss FunderMaps erwähnen, weil das der Anker ist)
- **Disclaimer-Hinweis steht im Footer-Template**, nicht in den Sections — keine eigenen Disclaimers im Text

## Was die Pages NICHT tun

- **Keine Lead-Form** auf Stadt-Pages — der CTA-Block am Ende verlinkt zu `/index.html#cta`. Das hält Stadt-Pages SEO-fokussiert (Content) statt zu Conversion-Punkten zu werden, die Search-Engines als „doorway pages" abstrafen
- **Keine Erfindung von Daten** — nur Faktisches über die Stadt und das Thema, plus generische Erklärung wie unser Bericht das adressiert
