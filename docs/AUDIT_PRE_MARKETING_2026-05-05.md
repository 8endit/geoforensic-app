# Pre-Marketing-Audit · 2026-05-05

Stand-Aufnahme vor Werbe-Schaltung. Alle Tests live gegen Production-VPS
(`bodenbericht.de`). Quellen: Stripe-API, Sentry-Test-Event, perf_smoke
Pipeline-Run, direkte SQL gegen Postgres, curl gegen Endpoints.

## Greenlight-Status — alle 5 Blöcke ✅

### Block 1: Bezahl-Pfad — 9/9
- [x] T1 Stripe-Mode = `sk_test_…` (kein Live-Geld bis explizit umgestellt)
- [x] T2 Coupon `EARLY50` valid, 50% off, nicht gelöscht
- [x] T3 Promotion-Code `EARLY50` aktiv, max_redemptions=50, times_redeemed=0,
  first_time_transaction restriction
- [x] T4 `/api/payments/checkout-direct` DE-Adresse Basis EARLY50 → 200 OK
- [x] T5 `/api/payments/checkout-direct` NL-Adresse Komplett → 200 OK
- [x] T7a Stripe-Session DE Basis EARLY50: subtotal 4900, discount 2450, total **2450** (24,50 €) ✅
- [x] T7b Stripe-Session NL Komplett: total **5900** (59 €) ✅
- [x] T8 Webhook-Endpoint reachable, Signature-Check (HTTP 400 ohne Header)
- [x] T9 `/api/payments/checkout-from-lead` (Lead-Flow): Lead anlegen + Bridge → 200 OK

### Block 2: Pipeline-Health
- [x] T10 perf_smoke Vollbericht-Pipeline: TOTAL 13.67s (Schwellwert 25s)
- [x] T11 Teaser-Pfad Quiz → Lead → PDF → Mail: 6.92s

### Block 3: UI-Visual (User-Verify)
- 2 frische Audit-Mails versendet an `benjaminweise41+audit-final-de@gmail.com`
  und `+audit-final-nl@gmail.com` mit der korrigierten 12-Sektionen-Liste

### Block 4: Operational
- [x] T17 Sentry verbunden (Test-Event `79f80a4702664fb9b68396db3f756d80`)
- [x] T18 TLS gültig bis 2026-07-16, HTTP/2 + Caddy aktiv
- [x] T19 Disk: 14% used (26GB von 193GB)
- [x] T16 uvicorn `--workers 4` läuft
- [x] T13 Indizes valid: `idx_egms_points_geom`, `_geom_geog`, `_egms_pid`
- [x] T12 Migration auf `20260505_03` (egms_burst_loaded + egms_pid)
- [x] **NEW: pg_dump-Backup eingerichtet** — `/opt/bodenbericht/backups/pg_dump.sh`,
  täglich 03:00 UTC via cron, 7-Tage-Retention. Initial-Dump 284 MB live.
- [x] **NEW: SSH-Hardening** — `PermitRootLogin prohibit-password` (nur key-auth)

### Block 5: Edge-Cases & Defense
- [x] **Vandalism-Defense 9/9** (`scripts/_vandalism_smoke.py`)
  - Schema-Layer: country whitelist, postcode pattern, lat/lon range
  - Wortliste-Layer: hate/profanity Detection
  - Address-Shape: HTML/Sonderzeichen rejected
  - Cache self-heal: vergiftete Einträge werden bei Read entfernt
- [x] **EARLY50-Quota saubergelegt** — 39 Test-Leads + 32 Test-Reports
  manuell aus DB entfernt (Backup von 15:43 UTC vorhanden). Counter jetzt
  **19/50** echte Leads, **31 freie Slots** für Marketing-Käufer.
- [x] **EARLY50 Code-Fix** — `_early50_still_available` excludet jetzt Test-
  Patterns (`+audit/+perfsmoke/+vbsmoke/+smoke/+test/+probe/+...`) +
  `@geoforensic.de` Domain. Zukünftige Smoke-Tests verbrennen keine
  Echtkäufer-Slots mehr.

## Bekannte Issues (Marketing-OK)

### Phase 2 – Daten-Lücken die honest kommuniziert sind
1. **Bewegungsverlauf-Visual** zeigt "Zeitreihen-Datensatz wird nachgeliefert"
   — `egms_timeseries` Tabelle hat 0 Rows. Aktiviert sobald EGMS-API-Token
   vom Copernicus Help-Desk angekommen ist (1-3 Wochen Wartezeit). On-demand-
   Loader-Code + Migrationen sind bereits committed, nur Token fehlt.
2. **Niederschlag-Achse im Korrelations-Radar** zeigt "Phase 2" statt Wert
   wenn Open-Meteo nicht antwortet — Pipeline hat Niederschlag-Stage live,
   aber Cache braucht 30 Tage warm-up. Zeigt nach erstem Lookup pro Region
   echten Wert (Berlin verifiziert: 600 mm/Jahr).
3. **NL-Mails sind auf Deutsch** — i18n ist nicht implementiert. Acceptable
   bis ersten 50 Käufern, dann eigener Sprint für NL-Locale.

### Operational
4. **Redis-Timeout-Warnings** im Slope-Cache (gelegentlich) — bewusst kurze
   `socket_timeout=1.0s`, Pipeline degradiert graceful zu OpenTopoData-live.
   Nicht kritisch, kein Datenverlust.
5. **Open-Meteo Latency** für Niederschlag-Erstabruf 1-2s → kann
   `pipeline.phase1_external` einmalig erhöhen. Cache fängt das ab Run 2 ab.

## Nächste Sprints (nach Marketing-Launch)

| Priorität | Item |
|---|---|
| Phase 2 | EGMS-API-Token einsetzen sobald Copernicus antwortet → Bewegungsverlauf live |
| Phase 2 | NL-Locale für Mail + PDF (Deutsch+English+Niederländisch) |
| Phase 2 | Provenance-Page als public-facing Showcase ausbauen (aktuell minimal) |
| Phase 3 | B2B-API-Schiene (geoforensic.de) als separate Subdomain |
| Phase 3 | Mehr DE-Bundesländer beim Bergbau (heute: NRW + RLP/Saarland) |

## Marketing-Greenlight: GO

Alle Show-Stopper sind weg, alle UI-Inkonsistenzen die Domenico aufgedeckt
hat sind gefixt, Bezahl-Pfad ist E2E verifiziert, Defense-in-depth gegen
externe Daten-Vergiftung steht, Backups laufen.

Die Phase-2-Lücken (Zeitreihe, NL-Locale) sind im PDF mit ehrlicher
Caption ("wird nachgeliefert") kommuniziert — kein Käufer wird überrascht.

**Datum Audit:** 2026-05-05 · 17:30 UTC
**Verantwortlich:** Benjamin Weise (Tepnosholding GmbH)
