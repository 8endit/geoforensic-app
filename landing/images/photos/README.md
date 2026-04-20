# Fotos fuer bodenbericht.de Landing

**Status:** Noch nicht im Repo. Muss manuell runtergeladen und committet werden
bevor die Landing-Integration live geht (DSGVO: kein Hotlinking auf externe
CDNs in Produktion).

## Warum nicht ueber den Sandbox-Agent

Die Sandbox des Agenten blockiert externe Image-Hosts. Die Preview-Seite
`landing/_preview-graphics.html` laedt die Bilder deshalb direkt vom
Pexels-CDN, damit du sie auf dem Handy siehst. **Das ist nur fuer die
Preview zulaessig — fuer Prod muessen sie lokal liegen.**

## Zwei Fotos, gezielt ausgesucht

### 1. Hero — historische deutsche Altstadt

- **Motiv:** Luftaufnahme Bamberg, rote Dachziegel, bewoelkter Himmel
- **Fotograf:** Markus Spiske
- **Pexels ID:** 3489009
- **Page:** https://www.pexels.com/photo/aerial-photography-of-brown-and-white-buildings-3489009/
- **Lizenz:** Pexels License (kommerziell nutzbar, keine Attribution
  erforderlich — wir nennen den Fotografen trotzdem im Impressum)
- **Zielpfad:** `landing/images/photos/hero-german-town.jpg`
- **Empfohlene Groesse:** 1920 × 1080 (Hero-Banner)

Warum: Deutsche Altstadt, warme Rottoene, historische Wertigkeit. Spricht
Kaeufer-Zielgruppe "ich kaufe ein Bestandsgebaeude in gewachsener Lage" an.
Kein Hochglanz-Stock-Look, echter dokumentarischer Schnitt.

### 2. Premium-Warteliste — Golden-Hour-Siedlung

- **Motiv:** Luftaufnahme Wohngebiet, Haeuser zwischen Baeumen, Sonnenuntergang
- **Fotograf:** Deva Darshan
- **Pexels ID:** 1637080
- **Page:** https://www.pexels.com/photo/aerial-view-of-city-1637080/
- **Lizenz:** Pexels License (kommerziell nutzbar, keine Attribution
  erforderlich — wir nennen den Fotografen trotzdem im Impressum)
- **Zielpfad:** `landing/images/photos/waitlist-aerial-sunset.jpg`
- **Empfohlene Groesse:** 1600 × 900 (Sektions-Hintergrund)

Warum: Goldenes Licht, viele Einfamilienhaeuser — emotional passend zur
"dein Haus, deine Entscheidung"-Narrative der Premium-Warteliste.
Aspirational, nicht angstbesetzt.

## Download-Anleitung (Cozy oder Felix)

1. Pexels-Seite oeffnen (Links oben)
2. "Free Download" Dropdown &rarr; **Large** oder **Original**
3. Datei umbenennen zum Zielpfad oben
4. `git add landing/images/photos/hero-german-town.jpg
   landing/images/photos/waitlist-aerial-sunset.jpg`
5. Commit + push

Danach kann die Integration in die echte `landing/index.html` passieren.
Die Preview-Seite wird spaetestens dann auch umgestellt (von Pexels-CDN
auf lokale Pfade) oder geloescht.

## Optional: weitere Bearbeitung

- **Dezente Koernung/Grain** (Tailwind: `mix-blend-multiply` Overlay oder
  CSS-Filter) um den Stock-Foto-Look zu brechen
- **Duotone-Tint** mit `#166534` (Brand-Green) auf niedriger Opacity —
  harmonisiert mit dem SVG-B (InSAR-Karte) darunter
- Beide Bilder auf 1920 skalieren, dann `cwebp -q 78` &rarr; `.webp` zusaetzlich
  zur `.jpg` fuer `<picture>`-Fallback

## Wenn die Fotos nicht passen

Dann sag es bevor Cozy sie laedt. Alternative Motive:
- Hero: echtes Nördlingen-Luftbild (schwerer zu finden auf CC-freien
  Plattformen, ggf. Wikimedia Commons)
- Waitlist: Drohnenaufnahme Einfamilienhaus-Siedlung bei Tag statt
  Sonnenuntergang — weniger emotional, mehr sachlich
