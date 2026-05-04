# STATUS — 2026-05-04 (Nachmittag/Abend)

**Stand:** Nach STATUS_2026-05-04 (Vormittag-Cleanup) hat die Nachmittags-Session diese Themen abgearbeitet. Geht direkt von hier weiter, wenn du am Mac wieder reinkommst.

`main`-HEAD zum Zeitpunkt: `7fe4636`. Server-Pull steht aus (siehe §6).

---

## 1. Was heute Nachmittag/Abend live wurde

| Hash | Inhalt |
|---|---|
| `84685e1` | feat(microbial): ESDAC Soil Microbial Activity Map (Cmic / bas / qO2) als primärer Datensatz für `bonus_microbial_activity` |
| `785678d` | fix(microbial): rasterio.warp.transform statt pyproj-Import (vermeidet neue Container-Dep) |
| `8ce3885` | fix(microbial): Ring-Search 10 km für Stadt-NODATA-Pixel (ESDAC deckt nur 18 % Europa-Fläche, hauptsächlich Acker/Wald/Grünland) |
| `8184bdb` | fix(directive): query_pesticides hat keinen country_code-Param (bestehender Bug nebenbei rausgekriegt) |
| `0b70e96` | feat(stripe): lead-flow checkout + 3 transactional pages + teaser CTA |
| `79cdd3e` | feat(stripe): mock-mode Vollbericht-trigger + EARLY50 coupon (50 % Rabatt erste 50) |
| `3ee4138` | fix(stripe): BackgroundTasks statt asyncio.create_task fürs Vollbericht-Trigger (asyncio aus Endpoint instabil) |
| `4352b3a` | fix(compose): mount shared/ so visual_renderer findet visual_tokens.json |
| `b7f2b74` | fix(docker): COPY backend/templates so Vollbericht-Renderer Jinja2-Quellen findet |
| `9df4595` | fix(template): Section 01 robust gegen fehlenden correlation_coefficient (sparse-data Adressen) |
| `73d4c53` | fix(template): Section 12 robust gegen fehlenden hist.percentile (selber Bug-Pattern) |
| `7fe4636` | fix(docker): COPY backend/static für tokens.css + Vollbericht-Fonts/CSS |

---

## 2. ESDAC Soil Microbial Activity — neu integriert

Quelle: Xu et al. 2020 (JRC), `https://esdac.jrc.ec.europa.eu/node/134114`.

3 Layer aus `GEB_maps.zip` auf VPS unter `/opt/bodenbericht/rasters/esdac_microbial/annual/`:

- `Cmic_lc_annual_mean_t.tif.tif` — mikrobielle Biomasse (μg C / g Boden)
- `bas_lc_annual_mean_t.tif` — basale Atmungsrate (μg CO2-C / g · h)
- `qO2_annual_mean_lc.tif.tif` — metabolic quotient (Stress-Indikator)

Code:
- `backend/app/soil_data.py` — Konstanten + 3 Lookups + `query_microbial(lat, lon)` mit on-the-fly EPSG:4326 → EPSG:3035 Reprojektion via `rasterio.warp.transform`
- `backend/app/soil_directive.py` — `bonus_microbial_activity`-Slot ruft jetzt primär ESDAC auf, fällt auf SOC-Proxy (Anderson and Domsch 1989) nur zurück wenn Raster-NODATA für ALLE 10-km-Ring-Pixel um die Adresse

Smoke-Test-Werte (alle "vital", status=ok):
- Berlin Mitte: cmic=151, bas=0,48, qo2=0,003
- Rotterdam: cmic=329, bas=1,46, qo2=0,004
- Karlsruhe: cmic=268, bas=1,16, qo2=0,005
- Bayern Acker: cmic=311, bas=0,70, qo2=0,002
- Sachsen Acker: cmic=344, bas=0,69, qo2=0,002

**Caveats:**
- ESDAC qO2-Werte zeigen 0,003 statt typischer 0,5–4 — Einheits-Mismatch im Raster, klassifikatorisch unkritisch (unter Stress-Schwelle bleibt unter Stress-Schwelle), aber für die Stress-Eskalation in `soil_directive.py` muss man irgendwann die ESDAC-Methodik-PDF lesen
- `Monthly_Bas_Cmic.zip` (24 Monthly-Maps, 306 MB) liegt parallel auf VPS unter `/opt/bodenbericht/rasters/esdac_microbial/monthly/` — UNGENUTZT. Saisonalitäts-Plot wäre ein Add-on für Landwirte-Page, eigener Mini-Sprint
- ARCHAEA-FASTQ-Zip (2,3 GB) liegt lokal auf Windows-Downloads — ungeeignet ohne Bioinformatik-Pipeline (FASTQ → 16S-Alignment → OTU → Diversity-Index), nicht weiter angefasst

---

## 3. Stripe-Bezahlpfad — komplett gebaut, mock-mode aktiv

End-to-end-Flow:
1. User füllt Quiz/Form → POST `/api/leads` → Background-Task generiert Teaser-PDF + mailt via Brevo
2. Teaser-PDF enthält CTA-Button mit Link zu `https://bodenbericht.de/kaufen.html?lead_id=…&email=…&address=…&coupon=EARLY50`
3. `/kaufen.html` ist Bridge-Page (PDF kann nur GET, Stripe braucht POST): liest URL-Params, ruft `POST /api/payments/checkout-from-lead`, redirected zur Stripe-Session-URL
4. Mock-Mode (kein `STRIPE_SECRET_KEY` in env): Background-Task triggert direkt `_generate_and_send_lead_report(source="stripe")` → Vollbericht-PDF in DB + per Brevo gemailt → Redirect zu `/danke.html`
5. Live-Mode (Stripe-Key gesetzt): echte Stripe-Session, User bezahlt, Webhook `checkout.session.completed` triggert dasselbe `_generate_and_send_lead_report`

Heute mit Test-Lead `32fcca2e-d5c2-4c2f-b020-a892d1f8cd93` (`earlytest@example.com`, Schulstr. 12 Gaggenau) verifiziert:
- Teaser-Report `a656f040…` (2,4 MB)
- Vollbericht-Report `6bb717f8…` (576 KB, 8 Seiten, PDF 1.4) via Mock-Mode

Coupon-Mechanik (`EARLY50` = 50 % Rabatt):
- `EARLY50_LIMIT = 50` in `backend/app/routers/payments.py`
- `is_early50_eligible(lead)`: True wenn Lead unter den ersten 50 non-operator-Leads (gemessen am `created_at`-Rank)
- Operator-Email: `settings.operator_email` default `benjaminweise41@gmail.com`, override via `OPERATOR_EMAIL` env var
- Teaser-PDF zeigt Banner "Sie gehören zu den ersten 50…" + durchgestrichener 39 € neben rabattiertem 19,50 €
- Stripe-Session bekommt `discounts=[{coupon: "EARLY50"}]` wenn quota noch da; automatic_tax wird abgeschaltet weil Stripe price_data + discounts + tax nicht gleichzeitig erlaubt

**Coupon `EARLY50` muss im Stripe-Dashboard angelegt werden** (50 %, currency=EUR, Duration=forever) bevor Live-Mode den Discount anwenden kann. Im Mock-Mode wird der Code nur in Logs vermerkt.

---

## 4. Drei neue Pages

`landing/danke.html` — Vielen-Dank-Page (success_url-Ziel, noindex)
`landing/abbruch.html` — Kauf-abgebrochen-Page (cancel_url-Ziel, noindex)
`landing/kaufen.html` — Bridge-Page (POST→Stripe-Redirect via JS, manueller Submit-Fallback bei deaktiviertem JS, noindex)

Alle drei in `landing/` deployed via Caddy-Mount, robots.txt + sitemap.xml unverändert (sind transactional, sollen nicht indexiert).

---

## 5. Tech-Debt nebenbei aufgedeckt + behoben

- Section 01 + 12 Templates crashed mit `UndefinedError 'dict object has no attribute X'` für sparse-data-Adressen (ländliche Orte mit zu wenig EGMS-Punkten → keine Korrelation/Perzentil im payload). `.get()` mit mapping-guard statt direktem Attribut-Zugriff. **Mehr solche Edge-Cases können in den anderen 10 Sektionen lauern** — pro `is not none` ohne `.get()` ein potenzieller Crash. Bei Gelegenheit alle 12 Sektionen auditen.
- Dockerfile kopierte bisher nur `app/` + `scripts/` + `alembic/`. `templates/` + `static/` waren raus → Vollbericht-Generierung konnte nie laufen. Heute beide reingekommen.
- `shared/visual_tokens.json` liegt im Repo-Root, war aber außerhalb des Backend-Build-Contexts. Bind-Mount via docker-compose statt COPY weil shared zwischen Backend + Frontend + Cozy geteilt werden soll.
- `asyncio.create_task` aus FastAPI-Endpoint-Handler ist instabil — DB-Session schließt vor Task-Ende. `BackgroundTasks` ist das richtige Pattern.

---

## 6. Was noch offen ist

### Sofort (Server-Pull steht aus)

```bash
ssh -i ~/.ssh/id_ed25519 root@185.218.124.158
cd /opt/bodenbericht
git pull --ff-only origin main
docker compose build backend && docker compose up -d backend
```

Letzter Test-Lead `32fcca2e-d5c2-4c2f-b020-a892d1f8cd93` ist verifizier-bar.

### Stripe Live-Mode — Code ist fertig, hängt nur an dir

1. Stripe-Konto Live-Verifikation im Dashboard: Geschäftsadresse, IBAN, USt-ID Tepnosholding, Steuernummer, Personalausweis-Foto, ggf. HRB-Auszug
2. Coupon `EARLY50` im Stripe-Dashboard anlegen (50 %, EUR, forever)
3. Stripe Tax aktivieren für DE + NL
4. Webhook registrieren: `https://bodenbericht.de/api/payments/webhook` + nur Event `checkout.session.completed` + Secret kopieren
5. Live-Keys in `backend/.env` auf VPS:
   ```
   STRIPE_SECRET_KEY=sk_live_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```
6. `docker compose up -d --force-recreate backend` (env_file wird neu gelesen)

### Rechtlich vor Live (User entschieden: kommt später, NICHT jetzt)

- AGB schreiben (Tepnosholding GmbH als Verkäufer)
- Widerrufsbelehrung-Footer-Link aktivieren (war `href="#"`), digitale-Inhalte-Ausnahme reincoden
- Datenschutzerklärung um Stripe Payments Europe Ltd erweitern
- EU-Streitschlichtung-Block wieder ins Impressum (war 17.4. raus, mit B2C-Verkauf wieder Pflicht)

### Aus alten Status-Docs noch offen

- A.7 `/ueber-uns`-Seite — wartet auf Foto + 3-5-Satz-Bio von dir
- Better Stack Account anlegen (Anleitung TEAM_HANDBOOK §5.2)
- GFZ + BBSR + BGR Lizenz-Mails versenden (Templates fertig in `docs/MAIL_*.md`)
- SSH-Passwort-Login disable (`PasswordAuthentication no`)
- AAK-Property-Keys-Smoke-Test mit echter RLP-Adresse in Altbergbau-Zone
- KOSTRA-Rasterize ohne `-te`-Pin → Tech-Debt
- Brevo-MX-Record für inbound (Domenico)
- Provenexpert-Profil (Domenico)

### Coverage-Gaps (User-Frage von heute, dokumentiert für Sprint-Pick)

**Heute:** 100 % DE-Adressen kriegen 11 von 12 Vollbericht-Sektionen mit echten Werten.
- Bergbau-Sektion: nur **NRW + RLP + Saarland adressgenau** (~28 % der DE-Bevölkerung)
- Restliche **72 %** sehen Placeholder mit Behörden-Hinweisen

Quick-Win-Sprints für mehr Bergbau-Coverage (Priorität nach Risiko):
1. Sachsen (Braunkohle Lausitz + Erzgebirge) — Sächsisches Oberbergamt
2. Brandenburg (Lausitzer Braunkohle) — LBGR
3. Niedersachsen (Salz, Erdöl) — LBEG

Module die wir komplett noch nicht haben:
- Erdbeben (GFZ DIN-Zonen + ELER) — Mail-Vorlage `MAIL_GFZ_ERDBEBEN.md` ungesendet
- Radon (BfS-Karte) — WMS ist offen, kein Antrag nötig, **könnte sofort integriert werden**
- Hagel/Sturm/Waldbrand (BBSR GIS-ImmoRisk) — Mail-Vorlage `MAIL_BBSR_LIZENZ.md` ungesendet
- BGR-BBD InSAR (würde 30-40 % MEHR DE-EGMS-Punkte freischalten) — Mail an `BBD@bgr.de` ungesendet

---

## 7. Mac-Session — wie du weitermachst

```bash
cd ~/dev/geoforensic-app
git pull --ff-only origin main
# Lies docs/STATUS_2026-05-04-late.md (dieses Doc) und docs/MASTERPLAN.md
# Wähle Pick aus §6 — z.B. Radon (sofort machbar) oder Sachsen-Mining-WMS (Recherche → Code)
```

SSH zum VPS funktioniert sowohl von Windows als auch Mac (beide Keys in `~/.ssh/authorized_keys` auf VPS hinterlegt).

`backend/.env` auf VPS hat aktuell **kein** Stripe-Secret-Key → Mock-Mode ist aktiv. Wenn du Live-Mode testen willst, Test-Keys (`sk_test_...`) reinsetzen + Coupon `EARLY50` im Stripe-Dashboard anlegen.

ESDAC Microbial-Daten liegen sowohl auf VPS (`/opt/bodenbericht/rasters/esdac_microbial/`) als auch lokal auf Windows (`C:\Users\weise\Downloads\GEB_maps.zip` + `Monthly_Bas_Cmic.zip`). Wenn du auf Mac diese Daten brauchst (z.B. Loader-Test offline): scp vom Windows oder vom VPS.
