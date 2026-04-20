# Grafik-Entwurf fuer bodenbericht.de

Vier SVG-Grafiken zur Auswahl. **Noch nicht in die Landing eingebaut** — reine
Preview. Tap auf die `.svg`-Dateien in der GitHub-App rendert sie inline.

| Datei | Gedachter Einsatz | Hintergrund |
|---|---|---|
| `01-hero-satellite.svg` | Hero (ueber oder neben der Headline) | funktioniert auf **dunklem** Navy-Hero |
| `02-insar-velocity-map.svg` | Feature-Karte "Bodenbewegungs-Screening" | funktioniert auf **weissem** Kartenhintergrund |
| `03-data-pipeline.svg` | "Automatische Datenanalyse"-Schritt | funktioniert auf weissem/hellgrauem Bg |
| `04-waitlist-earth.svg` | Premium-Warteliste-Sektion | funktioniert auf weissem/hellgruenem Bg |

Alle 4 nutzen das bestehende Brand-Gruen (`#16A34A` / `#22C55E`), Ampel-Farben
fuer Messpunkte, und sind gaenzlich Vektor — rund 4-5 KB pro Datei, scharf auf
jedem Screen, keine externen Abhaengigkeiten.

## Wenn Freigabe: minimale Einbauanleitung

Jede Grafik braucht nur ein `<img src="/images/graphics/XX.svg">` an der
gewuenschten Stelle — keine Build-Schritte, kein Tailwind-Config-Change,
nichts im Backend. Rebuild des Containers ist NICHT noetig (Landing-Mount
serviert die Dateien direkt).
