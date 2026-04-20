# Next Session — Plan & Mobile Workflow

Stand nach dem 20.04.2026 Abend-Sprint. Diese Datei fasst zusammen was
offen ist und wie wir vom Handy aus am effizientesten weiterarbeiten.

---

## 1. Teaser-PDF Polish (höchste Priorität)

Was der aktuelle Teaser (live seit heute Abend) noch nicht kann:

- **Saubere Seitenumbrüche.** Aktuell trennt Chrome-Headless die
  Nährstoffe-/InSAR-Kachel mitten durch und schiebt den CTA allein auf
  Seite 2. Fix: `page-break-inside: avoid` auf `.card` ist schon gesetzt,
  aber der CTA-Block und die Datenquellen/Disclaimer brauchen explizite
  `page-break-before: always` wenn die vorige Kachel schon nahe am
  Seitenende ist. Evtl. Höhen-Budget pro Seite prüfen.
- **Hintergrundbilder / Grafiken** passend zum Landing-Stil (nicht nur
  die subtilen Orbit-/Grid-SVGs von heute). Die gleiche Bildsprache wie
  auf der neuen Landing (gemerged als `landing/_preview-graphics.html`):
  warme Farben, dezenter Hero-Streifen, Foto als Hintergrund-Element hinter
  dem Header. Wichtig: **inline als base64** ins PDF (kein externer Fetch,
  Chrome-Headless rendert aus `file:///tmp`).
- **Referenz zur Landing.** Die Preview-Seite `/_preview-graphics.html`
  ist jetzt live und zeigt die finale Bildsprache. Teaser-PDF sollte
  visuell so wirken als gehörte es zur gleichen Marke.

---

## 2. Landing-Integration (Option A von heute Abend)

Die neue Landing liegt nur als Preview unter `/_preview-graphics.html`.
Damit sie die echte `bodenbericht.de/` ist:

1. Die 5 Sektionen aus `_preview-graphics.html` (Hero / Haus-InSAR-Map /
   Zeitreihe / Ampel / Waitlist) nach `landing/index.html` portieren.
2. Bestehenden Header, Footer, Form-Handler, FAQ und Analytics erhalten.
3. Tailwind-CDN-Klassen ersetzen durch die im prebuilt `/tailwind.css`
   enthaltenen — falls welche fehlen, `tailwind.config.js` erweitern und
   CSS neu bauen lokal, dann commiten.
4. Kurzer Cross-Browser-Check (Safari iPhone, Chrome Mobile, Firefox).

Aufwand 30–60 min.

---

## 3. Kleinere Landing-Hygiene

- **`quiz.html`:** "FM / Beispiel-Nutzer / Pilotphase 2026"-Testimonial
  wurde heute entfernt (war nur Platzhalter). Falls noch andere
  Beispiel-Nutzer-Blöcke auftauchen, gleich mit raus.

---

## 4. Daten-Integrationen (aus TODO-Liste)

Reihenfolge bleibt wie vorher besprochen:

| # | Layer | Wo liegt was? |
|---|---|---|
| 1 | **LUCAS Pestizide** | Code fertig auf `claude/lucas-pesticides-integration`. Wartet nur darauf dass die `lucas_pesticides_nuts2.xlsx` auf den Server kommt (vom Dev-PC per `scp`). |
| 2 | HRL Imperviousness (Versiegelung %) | Raster liegt bereits auf Platte, nur Integration fehlt. |
| 3 | SoilHydro AWC (Feldkapazität) | dito — Raster liegt, Integration fehlt. |
| 4 | Hochwasser BfG HWRM (HQ10/HQ100) | Externer WMS, kein Upload nötig. |
| 5 | Radon BfS | Externer WMS, kein Upload nötig. |
| 6 | CORINE Land Cover | Aktuelles Raster ist kaputt (RGB-PNG ohne CRS). CLC2018 neu von `land.copernicus.eu` ziehen, klippen auf DE+NL. |

"Eigene Methode" beim Hochwasser: Du hattest Variante 1 bestätigt — EGMS-
Senkungsmuster als ergänzender Indikator zur BfG-Karte. Separater Sprint
nach den Quick Wins.

---

## 5. Mobile-Workflow (Termius auf iPhone)

Heute gelernt, damit wir das nicht jedes Mal neu merken:

### iOS wrappt URLs automatisch mit `<>`

Jeder URL-ähnliche String im Paste wird von iOS mit spitzen Klammern
umschlossen. Das killt sofort jeden `curl`, `wget` oder `ssh` Befehl, weil
bash `<` und `>` als Shell-Redirects interpretiert.

**Workarounds (nach Robustheit sortiert):**

1. **Script im Repo.** Bester Weg. Wir commiten `download.sh` oder ähnlich
   mit der URL fest eingebacken. Auf dem Handy nur `bash /pfad/script.sh`
   eingeben — keine URL im Clipboard, kein Wrapping. Beispiel:
   `landing/images/photos/download.sh`.
2. **URL aus Bash-Variablen zusammensetzen.** Nur wenn Script overkill
   wäre:
   ```
   export H=https D=domain.example
   curl "$H://$D/path"
   ```
   Keine der Zeilen enthält `https://domain.example` als Substring, also
   nix zum Wrappen. **Wichtig:** die `export`-Zeile muss **vor** dem
   `curl` in einer eigenen Shell-Zeile laufen, sonst ist `$H`/`$D` im
   Child-Process nicht gesetzt.
3. **localhost statt Domain.** Für API-Calls vom Server auf sich selbst
   reicht `http://127.0.0.1:8000/…` — aber auch das wrappt iOS manchmal.
   Varialben-Trick anwenden.

### Heredoc und mehrzeilige Python-Commands

Termius strippt Newlines beim Paste. `python -c` mit echten Zeilenumbrüchen
bricht mit `IndentationError`. Lösung: **eine Zeile, Semikolons statt
Newlines, kein führendes Leerzeichen**:

```
docker compose exec backend python -c "import asyncio, logging; from app.routers.leads import _generate_and_send_lead_report; logging.basicConfig(level=logging.INFO); asyncio.run(_generate_and_send_lead_report(email='x@y.com', address='...', answers={}, db_url=''))"
```

### Deploy-Flow auf dem Server

- `landing/` ist bind-mounted. Änderungen dort sind **sofort** live — nur
  `git pull` nötig, kein Rebuild.
- Backend-Code (`backend/app/*.py`) ist **ins Image gebaut**. Änderungen
  brauchen Rebuild:
  ```
  cd /opt/bodenbericht && docker compose build backend && docker compose up -d --force-recreate backend
  ```
  Dauert 2–4 Minuten.
- `.env`-Dateien (`/opt/bodenbericht/.env` und `backend/.env`) werden beim
  Container-Start gelesen. Ein `--force-recreate` reicht, kein Rebuild.

### Verlässliche Diagnose-Commands

- Raster-Loader-Status: `docker compose exec backend python -c "from
  app.soil_data import SoilDataLoader; l=SoilDataLoader.get(); print(l.raster_dir, list(l._soilgrids.keys()), l._lucas is not None)"`
- Backend-Logs letzte 50 Zeilen: `docker compose logs backend --tail=50`
- Nach Fehlern suchen: `docker compose logs backend 2>&1 | grep -iE "error|traceback|exception"`
- SMTP-Config prüfen: `docker compose exec backend env | grep -i smtp`

---

## 6. Offene Tickets aus vorheriger Session

- **Pestizid-Branch mergen** (`claude/lucas-pesticides-integration`)
  sobald die xlsx vom PC auf den Server kommt.
- **Server-Git-History:** aktueller Stand ist main@HEAD nach den heutigen
  Merges (Teaser-Rework, Raster-Pfad-Fix, Graphics-Branch).
  Backend-Container läuft mit dem Stand **nach dem Rebuild heute Abend**.

---

## 7. Was heute live ging

- Teaser-PDF komplett überarbeitet (Logo-Header, „Gesamtbewertung für
  …"-Body, 4 Paywall-Kacheln mit Blur, CTA mit Satelliten-Deko).
- Raster-Pfad-Fix: Server lädt seit heute Abend **echte SoilGrids- und
  LUCAS-Daten** statt leerer Fallbacks — die alten Reports ohne
  Bodendaten sind Geschichte.
- Admin-Dashboard-KPI umbenannt zu „Berichte erstellt".
- Preview-Seite für die neue Landing unter `/_preview-graphics.html` live.
- 3 handgezeichnete SVG-Grafiken + 2 Pexels-Fotos (Download-Script) im
  Repo.
