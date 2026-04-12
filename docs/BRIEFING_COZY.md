# Briefing für Cozy — Stand 12. April 2026

Hey Cozy, hier ist was sich seit gestern alles getan hat. Wir haben den ganzen Tag Marktrecherche + Konkurrenzanalyse + Rechtscheck gemacht. Deine Recherche geht in die richtige Richtung, aber wir sind ein paar Schritte weiter. Hier das Wichtigste:

## 1. Niederlande ist unser Erstmarkt, nicht Deutschland

Seit 1. April 2026 muss in den Niederlanden JEDE Immobilienbewertung (Taxatierapport) ein Fundament-Risiko-Label (A-E) enthalten. Das ist Pflicht. 230.000 Transaktionen pro Jahr.

Das Problem: Käufer bekommen nur einen Buchstaben (z.B. "C"), aber KEINE Erklärung was das bedeutet. Kein Satellitenbild, keine Zeitreihe, keine Karte. Nur ein Buchstabe.

Unser Produkt: "Du hast Label C bekommen — hier sind 7 Jahre Satellitendaten die zeigen was unter deinem Haus passiert. Für 29-49 EUR."

Deutschland kommt danach (2027-2028), wenn die EU Soil Directive umgesetzt wird.

## 2. Konkurrenz in NL: FunderConsult

FunderConsult verkauft das Basis-Label für 7,95 EUR pro Adresse. Aber:
- Die haben InSAR-Daten von SkyGeo für 40% der Niederlande
- Der Käufer sieht davon NICHTS — nur den Buchstaben A-E
- Die sind institutionell eingebettet (NVM, NWWI, NRVT)
- Winzige Firma: 2-3 Entwickler

Wir konkurrieren nicht mit denen. Wir ERGÄNZEN sie. Die erzeugen die Angst (Label C/D), wir liefern die Antwort (Satellitendaten, Karte, Trend).

## 3. Pricing — warum nicht 5 EUR

Dein Vorschlag 5 EUR pro Check: verstehe den Gedanken (niedrige Hürde), aber das positioniert uns UNTER FunderConsult (7,95 EUR). Wir wären billiger als ein automatischer Datenbank-Lookup — obwohl unser Report deutlich mehr enthält:

- Echte Satellitenmessdaten pro Adresse (nicht nur ein Label)
- Interaktive Karte mit allen Messpunkten
- 7 Jahre Trend-Analyse
- Nachbarvergleich
- PDF-Report

Das ist ein komplett anderes Produkt. Preislich sitzen wir hier:

```
FunderConsult (Datenbank-Lookup, 1 Buchstabe)     7,95 EUR
>>> UNSER REPORT (Satellitendaten, Karte, Trend)  29-49 EUR <<<
QuickScan (Mensch kommt vorbei, Risse messen)     350-650 EUR
Funderingsonderzoek (Bohrungen, Labor)             700-3.500 EUR
```

One-Time Payment statt Abo: ja, da hast du recht. Einmal kaufen, einmal bezahlen. Niemand braucht ein Abo für einen Report den man einmal beim Hauskauf braucht.

Wir haben 6 niederländische Makler und Taxateure angeschrieben und gefragt was ein fairer Preis wäre. Warten auf Antworten.

## 4. Rechtlich: "Standortauskunft", NIEMALS "Gutachten"

Das Wort "Gutachten" darf NIRGENDS im Produkt, auf der Website oder im Marketing auftauchen. Das impliziert in Deutschland einen Sachverständigen mit physischer Ortsbegehung und zieht volle Haftung nach sich.

Wir sind ein "Bodenbewegungsscreening" / "Standortauskunft" — automatisiert, datenbasiert, kein Ersatz für physische Inspektion. Der Disclaimer im PDF ist rechtlich wichtig.

## 5. Was als nächstes für dich ansteht

Sobald Pricing aus dem Makler-Feedback klar ist:
- NL Landing Page unter geoforensic.de/nl/
- Niederländische Texte (ich liefere den Content)
- Report-PDF Design an dein Design System anpassen
- SEO-Artikel auf /nl/blog/ (Content kommt von uns)

## 6. Was technisch steht

- Backend: echte Pipeline mit Nominatim Geocoding + PostGIS
- EGMS-Daten: Auflösung bestätigt — 79 Punkte pro 500m-Radius in Rotterdam
- PDF-Generierung: WeasyPrint (läuft in Docker)
- Import-Script für EGMS-Daten: fertig
- Daten sind nur noch nicht in der DB — braucht EGMS-Account + Archiv-Download

Die CLAUDE.md im Repo ist aktualisiert mit dem ganzen Business-Kontext. Lies die mal durch wenn du Zeit hast.
