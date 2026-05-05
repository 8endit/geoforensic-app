# Mail-Vorlagen — INSPIRE Cadastral-WFS kommerzielle Nutzung

Für Phase E1 (Sprint Flurstück-Integration). Pro Bundesland eine Mail.
Bitte vor dem Versand:
- Empfänger-Adressen aktuell verifizieren (INSPIRE-Kontakt-Stelle steht
  meist in den Metadaten des jeweiligen WFS-GetCapabilities)
- Eigene Kontaktdaten + Firmierung einfügen
- Falls du eine Brief-Vorlage hast: Logo/Footer dranhängen

Versand am besten von `bericht@bodenbericht.de` oder
`benjamin.weise@bodenbericht.de` — wegen DKIM-konformer Signatur (Brevo
ist schon eingerichtet, läuft über `mail.bodenbericht.de`).

---

## 1) Bayern — Landesamt für Digitalisierung, Breitband und Vermessung (LDBV)

**Empfänger:** `inspire@ldbv.bayern.de`
**Betreff:** Anfrage kommerzielle Nutzung INSPIRE Cadastral Parcels Bayern

Sehr geehrte Damen und Herren,

ich betreibe die Plattform bodenbericht.de — ein automatisiertes Bodenrisiko-Screening für Immobilienkäufer, Bauträger und Versicherer auf Basis offizieller EU- und Bundesdaten (Copernicus EGMS, BfG HWRM, DWD KOSTRA, BBodSchV-Schwellen).

Ab Phase 2 unserer Plattform möchten wir das jeweilige Flurstück zu einer Adresse als räumlichen Bezug nutzen — insbesondere um Hochwasserzonen (HQ100), Bergbau-Berechtigungen und Versiegelungsgrad parzellenscharf statt nur radial um eine Adresse zuzuordnen.

Konkret möchten wir den von Ihnen bereitgestellten WFS für INSPIRE Cadastral Parcels (CP) per Point-Query nutzen, um pro Adresse ein Flurstücks-Polygon, die Flurstücksnummer und die Gemarkung zu erhalten. Die Flurstücks-Geometrie wird in unserer PostGIS-Datenbank gecached (TTL ein Jahr) und im PDF-Bericht zur Visualisierung verwendet — sie wird nicht weiterverkauft, exportiert oder als Bulk-Datensatz weitergegeben.

Können Sie mir mitteilen:

1. Unter welchen Lizenzbedingungen ist die kommerzielle Nutzung des INSPIRE Cadastral Parcels-WFS in unserem Anwendungsfall möglich?
2. Gibt es Quoten / Drosselungen für die per-Adresse-Abfrage, die wir berücksichtigen müssen?
3. Welche Attribution ist im PDF-Bericht und in unserer Datenquellen-Übersicht (https://bodenbericht.de/datenquellen.html) zu führen?
4. Falls eine Lizenzgebühr anfällt: bitte um ein Angebot mit erwarteter Anzahl von Abfragen (Schätzung 5.000–20.000 Adress-Lookups pro Jahr im ersten Jahr, projiziert auf 100.000+ ab Jahr 2).

Vielen Dank für Ihre Rückmeldung.

Mit freundlichen Grüßen
Benjamin Weise
bodenbericht.de · Bodenrisiko-Screening
[Adresse / Telefon / Impressum-Link]

---

## 2) Baden-Württemberg — Landesamt für Geoinformation und Landentwicklung (LGL)

**Empfänger:** `poststelle@lgl.bwl.de` (allgemein) oder `inspire@lgl.bwl.de` falls vorhanden
**Betreff:** Anfrage kommerzielle Nutzung INSPIRE Cadastral Parcels Baden-Württemberg

Sehr geehrte Damen und Herren,

ich betreibe die Plattform bodenbericht.de — ein automatisiertes Bodenrisiko-Screening für Immobilienkäufer, Bauträger und Versicherer auf Basis offizieller EU- und Bundesdaten (Copernicus EGMS, BfG HWRM, DWD KOSTRA, BBodSchV-Schwellen).

Ab Phase 2 unserer Plattform möchten wir das jeweilige Flurstück zu einer Adresse als räumlichen Bezug nutzen — insbesondere um Hochwasserzonen (HQ100), Versiegelungsgrad und Land-Use-Klassifikation parzellenscharf statt nur radial um eine Adresse zuzuordnen.

Mir ist bewusst, dass das LGL die ALKIS-Volldaten als kostenpflichtige Lizenz vergibt. Für unseren Anwendungsfall wäre der INSPIRE Cadastral Parcels-WFS (Point-Query pro Adresse, kein Bulk-Download) der passende Schnitt, da wir nur das jeweilige Flurstücks-Polygon einer einzelnen Adresse benötigen, nicht den gesamten Datenbestand.

Können Sie mir mitteilen:

1. Ist die kommerzielle Nutzung des INSPIRE-Cadastral-Parcels-WFS für Baden-Württemberg in unserem Anwendungsfall möglich, und wenn ja unter welchen Lizenzbedingungen?
2. Falls nicht: gibt es einen alternativen, schmaleren Lizenz-Schnitt (z.B. Pay-per-Query) den Sie für den B2C-Massenmarkt anbieten?
3. Welche Attribution / Quellenangabe ist erforderlich?

Wir sehen den Bericht als Vorbereitung für eine möglicherweise erforderliche behördliche Auskunft — Käufer wissen oft nicht, welches Flurstück zu ihrer Wunschimmobilie gehört, das wäre ein klarer Endkunden-Mehrwert.

Vielen Dank für Ihre Rückmeldung.

Mit freundlichen Grüßen
Benjamin Weise
bodenbericht.de · Bodenrisiko-Screening
[Adresse / Telefon / Impressum-Link]

---

## 3) Hessen — Hessische Verwaltung für Bodenmanagement und Geoinformation (HVBG)

**Empfänger:** `geodaten@hvbg.hessen.de` oder `poststelle@hvbg.hessen.de`
**Betreff:** Anfrage kommerzielle Nutzung INSPIRE Cadastral Parcels Hessen

Sehr geehrte Damen und Herren,

ich betreibe die Plattform bodenbericht.de — ein automatisiertes Bodenrisiko-Screening für Immobilienkäufer, Bauträger und Versicherer auf Basis offizieller EU- und Bundesdaten (Copernicus EGMS, BfG HWRM, DWD KOSTRA, BBodSchV-Schwellen).

Ab Phase 2 unserer Plattform möchten wir das jeweilige Flurstück zu einer Adresse als räumlichen Bezug nutzen — insbesondere um Hochwasserzonen (HQ100), Bergbau-Berechtigungen und Versiegelungsgrad parzellenscharf statt nur radial um eine Adresse zuzuordnen.

Konkret möchten wir den von Ihnen bereitgestellten WFS für INSPIRE Cadastral Parcels per Point-Query nutzen, um pro Adresse ein Flurstücks-Polygon, die Flurstücksnummer und die Gemarkung zu erhalten. Die Flurstücks-Geometrie wird in unserer PostGIS-Datenbank gecached (TTL ein Jahr) und im PDF-Bericht zur Visualisierung verwendet — sie wird nicht weiterverkauft, exportiert oder als Bulk-Datensatz weitergegeben.

Können Sie mir mitteilen:

1. Unter welchen Lizenzbedingungen ist die kommerzielle Nutzung des INSPIRE Cadastral Parcels-WFS in unserem Anwendungsfall möglich?
2. Gibt es Quoten / Drosselungen für die per-Adresse-Abfrage, die wir berücksichtigen müssen?
3. Welche Attribution ist im PDF-Bericht und in unserer Datenquellen-Übersicht zu führen?
4. Falls eine Lizenzgebühr anfällt: bitte um ein Angebot mit erwarteter Anzahl von Abfragen (5.000–20.000 Adress-Lookups pro Jahr im ersten Jahr, 100.000+ ab Jahr 2).

Vielen Dank für Ihre Rückmeldung.

Mit freundlichen Grüßen
Benjamin Weise
bodenbericht.de · Bodenrisiko-Screening
[Adresse / Telefon / Impressum-Link]

---

## 4) Niedersachsen — Landesamt für Geoinformation und Landesvermessung (LGLN)

**Empfänger:** `inspire@lgln.niedersachsen.de` oder `geodaten@lgln.niedersachsen.de`
**Betreff:** Anfrage kommerzielle Nutzung INSPIRE Cadastral Parcels Niedersachsen

Sehr geehrte Damen und Herren,

ich betreibe die Plattform bodenbericht.de — ein automatisiertes Bodenrisiko-Screening für Immobilienkäufer, Bauträger und Versicherer auf Basis offizieller EU- und Bundesdaten (Copernicus EGMS, BfG HWRM, DWD KOSTRA, BBodSchV-Schwellen).

Ab Phase 2 unserer Plattform möchten wir das jeweilige Flurstück zu einer Adresse als räumlichen Bezug nutzen — insbesondere um Hochwasserzonen (HQ100), Bergbau-Berechtigungen und Versiegelungsgrad parzellenscharf statt nur radial um eine Adresse zuzuordnen.

Konkret möchten wir den von Ihnen bereitgestellten INSPIRE Cadastral Parcels-WFS per Point-Query nutzen, um pro Adresse ein Flurstücks-Polygon, die Flurstücksnummer und die Gemarkung zu erhalten. Die Flurstücks-Geometrie wird in unserer PostGIS-Datenbank gecached (TTL ein Jahr) und im PDF-Bericht zur Visualisierung verwendet — sie wird nicht weiterverkauft, exportiert oder als Bulk-Datensatz weitergegeben.

Können Sie mir mitteilen:

1. Unter welchen Lizenzbedingungen ist die kommerzielle Nutzung des INSPIRE Cadastral Parcels-WFS in unserem Anwendungsfall möglich?
2. Gibt es Quoten / Drosselungen für die per-Adresse-Abfrage, die wir berücksichtigen müssen?
3. Welche Attribution ist im PDF-Bericht und in unserer Datenquellen-Übersicht zu führen?
4. Falls eine Lizenzgebühr anfällt: bitte um ein Angebot mit erwarteter Anzahl von Abfragen (5.000–20.000 Adress-Lookups pro Jahr im ersten Jahr, 100.000+ ab Jahr 2).

Vielen Dank für Ihre Rückmeldung.

Mit freundlichen Grüßen
Benjamin Weise
bodenbericht.de · Bodenrisiko-Screening
[Adresse / Telefon / Impressum-Link]

---

## Hinweise zum Versand

- Mail-Adressen oben sind **plausibel-Standard**, sollten vor dem Versand
  über die jeweilige LVG-Website verifiziert werden (oft hat die WFS-
  GetCapabilities-Antwort einen `<ContactInformation>`-Block mit der
  echten INSPIRE-Kontakt-Adresse)
- Antwortzeiten typisch: **2–6 Wochen pro Behörde**
- Falls eine Behörde ablehnt oder Lizenzgebühren > 5 000 €/Jahr fordert:
  Fallback auf 500 m-Radius wie heute, mit klarem Hinweis im Bericht
- Erfolgreiche Antworten + Lizenzbedingungen bitte in
  `docs/DATA_PROVENANCE.md` ergänzen
