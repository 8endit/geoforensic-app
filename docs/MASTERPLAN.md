# MASTERPLAN — bodenbericht.de + geoforensic.de

**Stand:** 2026-05-03 (nach Audit-Sweep + Fixes #1–12)
**Eine Quelle der Wahrheit. Alle anderen Plan-Dokumente sind Detail-Pläne, die hier referenziert werden.**

> Wenn ein Detail-Plan und dieser Masterplan in Konflikt geraten, gilt der Masterplan. Detail-Pläne sind Vorhaben in einem bestimmten Sprint; der Masterplan ist die laufende Wahrheit über aktuellen Stand + offene Punkte.

---

## 0. North Star

**Zwei Produkte, ein Repo:**

| Produkt | Domain | Rolle | Status |
|---|---|---|---|
| **bodenbericht.de** | live | Free-Lead-Magnet (DE), Funnel zu Pilot-Vollbericht und Premium-Waitlist | aktiv, Pilotphase |
| **geoforensic.de** | parked | Paid-Produkt (NL #1 + DE #2), Stripe-gated, Cozy-Frontend (`8endit/cozy-frontend`) | nicht gebaut |

**Märkte:**
1. **NL** (Markt #1): seit 1.4.2026 KCAF/FunderMaps-A-E-Label-Pflicht im Taxatierapport. Wir = Zweitmeinung mit Daten-Tiefe.
2. **DE** (Markt #2): EU-Bodenrichtlinie 2025/2360, Umsetzungsfrist Dez 2028 → Käufer-Recht auf Bodendaten.

**Pricing-Sichtbarkeit:** Keine konkreten EUR-Preise auf der Public-Site (nur „kostenlos in der Pilotphase"). Konkrete Preise leben in `.env.example` + diesem Masterplan + internen Memos.

**Forbidden Term:** „Gutachten" nie als Selbstbezeichnung — nur in negierenden Disclaimern. Verifiziert 2026-05-03.

---

## 1. Aktueller Stand der Plattform

### 1.1 bodenbericht.de Live-Surface
- 22 HTML-Pages: index, quiz, muster-bericht, datenquellen, 4 persona-Pages (`fuer-*`), 9 wissen-Pages, 3 legal (impressum/datenschutz/widerruf), 404, admin.
- Tailwind 3 lokal gebuildet (`tailwind.css` 32 KB, gepurged).
- Klaro DSGVO-Consent self-hosted, GTM/GA4/PostHog gated.
- Brevo-SMTP mit DKIM `bodenbericht.de` (umgezogen 3.5.2026 von `geoforensic.de`).
- Caddy (TLS) → FastAPI (8000) auf Contabo VPS `185.218.124.158`, `/opt/bodenbericht`.

### 1.2 Lead-Flow-Routing (verifiziert 2026-05-03)
- **`PAID_SOURCES = {"paid", "checkout", "stripe", "pilot-vollbericht"}`** → Vollbericht
- **`DOI_SOURCES = {"premium-waitlist"}`** → Bestätigungs-Mail mit Token, kein Bericht
- **alles andere** → Teaser-Bericht (deny-by-default)

5 Lead-Forms auf index.html (hero, direct, pilot-vollbericht, live-check-convert, premium-waitlist) + Quiz + 4 Persona-Forms = 10 Eintrittspunkte. Alle senden POST `/api/leads` außer Live-Check (POST `/api/reports/preview`, kein Lead).

### 1.3 Backend-Pipeline (Vollbericht)
12 Sektionen, alle aktiv per 2.5.2026: Bodenbewegung (EGMS), Schwermetalle (LUCAS+SoilGrids), Bergbau (NRW+RLP+Saarland), Hochwasser (BfG HWRM), KOSTRA Starkregen, SoilGrids-Bodenqualität, Nährstoffe, Geländeprofil (SRTM), EU Soil Directive 16-Descriptoren, Pestizide (LUCAS), Altlasten (NL: PDOK / DE: CORINE-Proxy), Individuelle Einschätzung. Sentry EU live (`send_default_pii=False`).

Detaillierter Datenkatalog: [DATA_PROVENANCE.md](DATA_PROVENANCE.md), [DATA_SOURCES_VERIFIED.md](DATA_SOURCES_VERIFIED.md).

### 1.4 Server-State (per STATUS_2026-05-03)
- `main` letzter Commit: `2638b6a` (lokal)
- **Server-Pull steht aus** (blockt darauf, dass Domenico Brevo-SMTP-Credentials bestätigt)
- MX-Record für inbound-Mail (`bericht@`, `info@`) ausstehend (Domenico/DNS, ~30 Min)
- BBSR-Lizenz-Mail ausstehend ([MAIL_BBSR_LIZENZ.md](MAIL_BBSR_LIZENZ.md))
- Provenexpert-Profil ausstehend (Domenico)

---

## 2. Was im Audit-Sweep 2026-05-03 erledigt wurde (Fixes #1–12)

**Frontend-HTML:**
1. **Wissen-Footer-Tags** — 8 von 9 Wissen-Pages hatten kaputte `<footer>`-Tags durch unsichtbares SOH-Steuerzeichen → repariert.
2. **Quiz-Hardcode** — initialer „Mittleres bis erhöhtes Risiko erkannt"-Fallback entfernt, neutralisiert auf „Auswertung wird vorbereitet". `updateResultSnippet()` rechnet weiter dynamisch.
3. **Consent-Texte** auf 3 Forms (`quiz email-form`, `direct-lead-form`, `premium-waitlist-form`) ergänzt mit Verweis auf `/datenschutz.html`.
5. **Stale Q3/2026-Copy** auf [index.html:797](Projects/geoforensic-app/landing/index.html:797) ersetzt durch Klick-Verlinkung auf alle 4 Persona-Pages.
6. **EUR-Preise** auf [fuer-immobilienkaeufer.html](Projects/geoforensic-app/landing/fuer-immobilienkaeufer.html) Vergleichstabelle + FAQ als „Marktübliche Drittpreise" gelabelt mit Footnote-Quellen.
11. **3 neue FAQs** auf [index.html](Projects/geoforensic-app/landing/index.html): NL/KCAF, Baugrundgutachten-Unterschied, Datenschutz.

**JS-Plumbing (geteilter Helper):**
- Neue Datei [landing/static/landing-tracking.js](Projects/geoforensic-app/landing/static/landing-tracking.js):
  - 7. **Conversion-Events** `lead_submitted`, `lead_failed`, `live_check_failed`, `quiz_started`, `quiz_question_answered`, `quiz_completed`, `consent_granted/declined`
  - 8. **UTM-Capture** aus `location.search` mit 90-Min-SessionStorage
- In allen 6 lead-führenden Pages eingebunden: index, quiz, fuer-bautraeger, fuer-gartenbesitzer, fuer-immobilienkaeufer, fuer-landwirte.
- Alle Handler nutzen jetzt `bbBuildPayload()` (UTM-Merge) + `bbTrackLeadResult()` (success/fail-Events).

**Klaro-Consent:**
10. **GA4 + PostHog** in 2 Klaro-Services aufgesplittet (granular per EDPB Guidelines 03/2022). Orchestrator-Service `google-tag-manager` lädt GTM, sobald _einer_ der beiden akzeptiert ist. Banner-Text „anonymisiert" → „pseudonymisiert" (BfDI-Wortwahl).

**Backend (Premium-Waitlist DOI):**
4. **Double-Opt-In für premium-waitlist** (UWG § 7 Abs. 2 Nr. 2) — neue Spalten `confirmation_token` + `confirmed_at` auf `leads`-Tabelle ([Migration 20260503_01](Projects/geoforensic-app/backend/alembic/versions/20260503_01_leads_add_doi_columns.py)), neue Mail-Funktion `send_waitlist_confirmation_email()` in [email_service.py](Projects/geoforensic-app/backend/app/email_service.py), neue Route `GET /api/leads/confirm/{token}` in [leads.py](Projects/geoforensic-app/backend/app/routers/leads.py). DOI-Confirm-URL ist `https://bodenbericht.de/api/leads/confirm/{token}` (hardcoded weil geoforensic.de geparkt ist).

**Caddy:**
9. **Proposal** [scripts/Caddyfile.proposed](Projects/geoforensic-app/scripts/Caddyfile.proposed) — CSP Report-Only, Cache-Control differenziert, `Server`-Header gestrippt, Permissions-Policy, COOP, brotli+zstd. Auf VPS einzuspielen.

**Konsistenz:**
- Persona-Pages + Wissen-Pages Footer auf `text-gray-300` (AAA-Kontrast).
- impressum.html migriert auf Shared-Tailwind-Header/Footer (frühere Session).
- BBodSchV-Link `_2021/` → `_2023/` (frühere Session).
- eu-bodenrichtlinie.html SEO-Title 79→59 Zeichen, Description 190→160 (frühere Session).

**Routing-Verifikation:**
12. CLAUDE.md korrigiert: nicht `TEASER_SOURCES`, sondern `PAID_SOURCES` (deny-by-default). Plus `DOI_SOURCES` neu dokumentiert.

---

## 3. Offene Punkte (geordnet nach Impact)

### 3.1 🔴 Diese Woche / vor Server-Pull

| # | Punkt | Owner | Quelle |
|---|---|---|---|
| 3.1.1 | **Server-Pull** der heutigen Commits + Tailwind-Build neu (impressum.html im Content-Array) + Migration `alembic upgrade head` | Ben (SSH) | STATUS_2026-05-03 |
| 3.1.2 | **Brevo-SMTP-Credentials** für `bodenbericht.de`-Sender bestätigen | Domenico | STATUS_2026-05-03 |
| 3.1.3 | **MX-Record** `bericht@`, `info@`, `team@` auf bodenbericht.de | Domenico (DNS) | STATUS_2026-05-03 |
| 3.1.4 | **Caddyfile-Hardening deployen** ([scripts/Caddyfile.proposed](../scripts/Caddyfile.proposed)) — CSP zunächst Report-Only, 7 Tage beobachten, dann scharf | Ben | Audit Fix #9 |
| 3.1.5 | **GTM-Tags** intern so konfigurieren, dass GA4-Tag nur feuert wenn `klaro`-Cookie `google-analytics-4` enthält, PostHog-Tag nur wenn `posthog` enthält | Domenico | Audit Fix #10 |
| 3.1.6 | **`bericht@bodenbericht.de`** im Server-`.env` setzen (`SMTP_FROM_EMAIL`) | Ben (SSH) | STATUS_2026-05-03 |
| 3.1.7 | **Provenexpert-Profil** anlegen + erste Reviews einsammeln | Domenico | STATUS_2026-05-03 |
| 3.1.8 | **BBSR-Lizenz-Mail** abschicken ([docs/MAIL_BBSR_LIZENZ.md](MAIL_BBSR_LIZENZ.md)) | Ben | NEXT_STEPS_PLAN |

### 3.2 🟡 Sprint S2 — Status (per 2026-05-03 abgearbeitet)

**13 von 17 Items erledigt im S2-Sweep:**

| # | Punkt | Status |
|---|---|---|
| 3.2.1 | datenschutz/widerruf/404 auf Shared-Tailwind | ✅ migriert (S2-04) |
| 3.2.2 | quiz.html-Footer Kontrast + border | ✅ erledigt (S2-01); Farbe `bg-brand-900` ist effektiv identisch zu `bg-navy-900` (#0a1628 vs #0c1d3a) |
| 3.2.3 | `alert()` → Inline-Errors (alle 7 Forms) | ✅ erledigt (S2-07) |
| 3.2.4 | FAQ + Mobile-Menu aria-expanded/aria-controls | ✅ erledigt (S2-05); Persona-Pages nutzen native `<details>/<summary>` |
| 3.2.5 | Honeypot frontend + backend | ✅ erledigt (S2-09); Backend silently-discards bei `website` field |
| 3.2.6 | Lead-Handler-Deduplikation `bbSubmitLead()` | ✅ index.html + quiz.html migriert (S2-08); 4 Persona-Pages nutzen weiterhin Inline-Handler (Refactor offen) |
| 3.2.7 | Live-Check-Result Focus + ARIA | ✅ erledigt (S2-06) |
| 3.2.8 | UI-Schutz `/admin.html` | ⏳ in [scripts/Caddyfile.proposed](../scripts/Caddyfile.proposed) als auskommentierter Block; Login-Daten zwischen Ben+Domenico noch zu teilen |
| 3.2.9 | sitemap.xml `<lastmod>` Build-Skript | ✅ erledigt (S2-12); [scripts/build_sitemap.py](../landing/scripts/build_sitemap.py) — pro Deploy laufen |
| 3.2.10 | SVG-Optimierung 02_property_context_map | ✅ erledigt (S2-11); SVGO 1% (Hauptlast = base64-PNG); `loading="lazy"` war bereits aktiv |
| 3.2.11 | Inter-Font preload | ✅ erledigt (S2-10); 21 Pages haben jetzt preload für 400+600 |
| 3.2.12 | B2B-Pricing-Q3-Copy auf fuer-bautraeger | ✅ verifiziert (S2-03); Q3/2026 ist noch valide |
| 3.2.13 | Persona-Pages visuell differenzieren / Stadtbilder | ⏳ offen (User: „für später") |
| 3.2.14 | Footer-Strapline „Bodenanalysen" → „Bodenrisiko-Screening" | ✅ erledigt (S2-02); 17 Pages aktualisiert |
| 3.2.15 | CTA-Labels diversifizieren | ✅ erledigt (S2-13); Hero=„Meine Adresse prüfen lassen", Direct=„Bericht für meine Adresse anfordern", Live-Check-Convert=„Vollständigen Bericht senden" |
| 3.2.16 | Email-Channel team@bodenbericht.de Alias | ⏳ offen (Domenico — DNS/MX-Side); Code-seitig kann der Switch erst nach DNS erfolgen |
| 3.2.17 | Pilot-vs-Premium-Narrativ entscheiden | ⏳ offen (Strategie-Entscheidung, nicht Code-Sache) |

**Offen aus S2 (4 Items):** 3.2.8 (admin-Login teilen), 3.2.13 (Stadtbilder), 3.2.16 (Email-Alias-DNS), 3.2.17 (Narrativ-Entscheidung).

### 3.3 🟢 Mittelfristig (Phase C, ~1 Monat)

| # | Punkt | Owner | Detail-Plan |
|---|---|---|---|
| 3.3.1 | **NL-Sprachversion** Vollbericht-PDF (NL ist Markt #1) | Cozy | [PLAN_NL_I18N.md](PLAN_NL_I18N.md) |
| 3.3.2 | **AHN WCS für NL** (0,5 m LiDAR statt 30 m SRTM) | Backend | STATUS_2026-05-03 |
| 3.3.3 | **Lokaler SRTM-Tile-Cache** für DE (raus aus OpenTopoData-Cap) | Backend | STATUS_2026-05-03 |
| 3.3.4 | **ESDAC Soil Microbial Biomass + Respiration** anfragen + integrieren | Backend | STATUS_2026-05-03 |
| 3.3.5 | **`/ueber-uns`-Seite** (Foto + Bio + Tepnos-Bezug) als Trust-Page | Domenico | [SEO_BRANDING_ROLLOUT_PLAN.md](SEO_BRANDING_ROLLOUT_PLAN.md) §A.7 |
| 3.3.6 | **Magazin-Artikel + Backlinks** (Domenico-Katalog Phase C) | Domenico | NEXT_STEPS_PLAN |
| 3.3.7 | **Lighthouse-Baseline** + LCP/INP/CLS-Sweep dokumentieren | Ben | SEO_BRANDING_ROLLOUT_PLAN A.10 |
| 3.3.8 | **CSP von Report-Only auf scharf** umstellen nach 7 Tagen Beobachtung | Ben | Audit Fix #9 |

### 3.4 ⚫ geoforensic.de Paid-Flow (Stefan-Sprint)

| # | Punkt | Detail-Plan |
|---|---|---|
| 3.4.1 | **Stripe customer-facing** auf bodenbericht.de schalten (`routers/payments.py` existiert) | [PLAN_GEOFORENSIC_DE.md](PLAN_GEOFORENSIC_DE.md) |
| 3.4.2 | **Country-Routing** für Pricing (NL 39 € / DE 49 € / DE-Premium 89 €) | PLAN_GEOFORENSIC_DE |
| 3.4.3 | **§ 356(5) BGB Doppelbestätigung** im Stripe-Form ("Ausführung sofort + Widerrufsrecht erlischt") — vor erstem kostenpflichtigen Bericht **zwingend** | Audit Legal #10 |
| 3.4.4 | **geoforensic.de** aus GoDaddy-Parking nehmen (zeigt aktuell AdSense-Ads) | Domenico |
| 3.4.5 | **Cozy-Frontend** ([8endit/cozy-frontend](https://github.com/8endit/cozy-frontend)) auf geoforensic.de deployen | Cozy |
| 3.4.6 | **Pflichtversicherung Elementar** beobachten (Koalitionsvertrag 2025, Bundesrats-Vorstoß) — falls Opt-out kommt: B2B-API-Sog erwarten | Strategy |

---

## 4. Permanente Regeln (CLAUDE.md kompakt)

### 4.1 Code & Inhalt
- **Wort „Gutachten"** nie als Selbstbezeichnung — nur in negierenden Disclaimern.
- **Konkrete EUR-Preise** nur in `.env.example` + Memos + diesem Masterplan, **nie** auf Public-Pages (außer als Drittpreis klar gekennzeichnet).
- **Disclaimer in PDF** (`html_report.py` + `full_report.py`) ist legal verpflichtend — nicht abschwächen, nicht entfernen.
- **NL ist Markt #1** — Country-Routing in jedem Datenmodul; PDF muss bald auch NL.
- **Email-Splittung:** `team@geoforensic.de` (Menschen, derzeit), `bericht@bodenbericht.de` (System) — Vereinheitlichung steht (3.2.16).
- **bodenbericht.de**-Hardcoded-URLs nur dort verwenden, wo bewusst (z. B. DOI-Confirm), sonst `public_base_url` aus settings.
- **Footer-Konsistenz:** `bg-navy-900 text-gray-300 py-12 md:py-16 border-t border-navy-700` ist der Standard. quiz.html ist Ausnahme (`bg-brand-900`) — soll harmonisiert werden (3.2.2).

### 4.2 Lead-Routing (deny-by-default)
- `PAID_SOURCES = {"paid", "checkout", "stripe", "pilot-vollbericht"}` → Vollbericht
- `DOI_SOURCES = {"premium-waitlist"}` → Bestätigungs-Mail
- alles andere → Teaser

### 4.3 DSGVO / Consent
- Keine 3rd-party-Domains pre-Consent. Keine Cookies bei First-Visit.
- Klaro: GA4 + PostHog separate Toggles.
- Lead-Forms ohne Consent-Text **nicht akzeptabel** (alle 9 sind heute drin).
- Premium-Waitlist = Marketing-Einwilligung → DOI zwingend (jetzt implementiert).

### 4.4 Datenquellen-Lizenzen
- **EGMS** (Copernicus): CC BY 4.0, kommerziell ok, Attribution Pflicht.
- **bodemdalingskaart.nl** (CC-BY-SA): SA-Copyleft → **nicht** verwenden, sonst sind Berichte open-licensed.
- **BGR BBD**: Lizenz noch ungeklärt ([MAIL_BBSR_LIZENZ.md](MAIL_BBSR_LIZENZ.md)).
- **CORINE / HRL / SoilGrids**: alle CC-BY/Copernicus-FFO, kommerziell ok.

### 4.5 Server / Deploy
- Host: Contabo VPS `185.218.124.158`, `/opt/bodenbericht`.
- Deploy-Cycle: `git pull` → landing hot-reload (bind-mount), backend `docker compose build backend && up -d`.
- Runbook: [TEAM_HANDBOOK.md](TEAM_HANDBOOK.md).

---

## 5. Veraltete Plan-Dokumente (zu archivieren oder löschen)

Die folgenden Pläne sind durch diesen Masterplan oder durch Code-Stand abgelöst. **Nicht mehr als Quelle der Wahrheit zitieren:**

| Doc | Grund | Aktion |
|---|---|---|
| [gregor-landing-integration.md](gregor-landing-integration.md) | Tailwind CDN, /register-Flow, Single-Page-Quiz — alles drei nicht mehr aktuell | archivieren |
| [PRODUKTPLAN.md](PRODUKTPLAN.md) | „Geplant (v2)"-Liste ist live (Hochwasser, Altlasten, Mining, KOSTRA, Vollbericht) | umschreiben oder archivieren |
| [NEXT_SESSION_PLAN.md](NEXT_SESSION_PLAN.md) | bezieht sich auf Pre-V.4.7-Layout | archivieren |
| [BUSINESSPLAN_NOTIZEN.md](BUSINESSPLAN_NOTIZEN.md) §8 (Stack) | nennt WeasyPrint primär; ist nur Fallback | korrigieren |
| [NEXT_STEPS_PLAN.md](NEXT_STEPS_PLAN.md) | Sentry/KOSTRA/CORINE/ESDAC R-Faktor stehen drin als TODO, sind alle live seit 1.5.–2.5.2026 | aktualisieren oder durch Masterplan ersetzen |
| [SEO_BRANDING_ROLLOUT_PLAN.md](SEO_BRANDING_ROLLOUT_PLAN.md) §A | A.7 (`/ueber-uns`) ist offen → 3.3.5; A.6 (Versand-Domain) ist erledigt; A.8 (Source-Routing) wurde anders gelöst (deny-by-default) | aktualisieren oder durch Masterplan ersetzen |
| [CURSOR_TEASER_VS_FULL_REPORT.md](CURSOR_TEASER_VS_FULL_REPORT.md) | nutzt `TEASER_SOURCES`-Begriff; Backend ist umgekehrt (deny-by-default) | korrigieren |
| [CURSOR_UX_SECURITY_AUDIT.md](CURSOR_UX_SECURITY_AUDIT.md) | targets `frontend/.../app/...` — gehört in `cozy-frontend`-Repo | dorthin verschieben oder löschen |
| [CURSOR_LANDING_SPRINT2.md](CURSOR_LANDING_SPRINT2.md) §5.9 | sagt „Sub-Landingpages folgen Q3/2026" — sind seit 3.5.2026 live | korrigieren |
| [STATUS_2026-04-29.md](STATUS_2026-04-29.md), [STATUS_2026-04-30.md](STATUS_2026-04-30.md) | sind historische Status-Snapshots, nicht falsch — bleiben als Audit-Trail | nichts tun |
| [STATUS_2026-05-03.md](STATUS_2026-05-03.md) | aktueller Stand vor diesem Masterplan | bleibt als Audit-Trail |

**Aktive, weiterhin gültige Detail-Pläne:**

| Doc | Rolle |
|---|---|
| [TEAM_HANDBOOK.md](TEAM_HANDBOOK.md) | operative Wahrheit (SSH, Deploy, DNS, Monitoring) |
| [DATA_PROVENANCE.md](DATA_PROVENANCE.md) | bindende Wahrheit pro Datenpunkt (Datenquellen + Lizenzen) |
| [DATA_INVENTORY_AUDIT.md](DATA_INVENTORY_AUDIT.md) | welche Raster nutzbar |
| [DATA_SOURCES_VERIFIED.md](DATA_SOURCES_VERIFIED.md) | Layer-Katalog mit Verifizierungs-Stand |
| [API.md](API.md) | API-Referenz |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Deploy-Schritte |
| [PLAN_NL_I18N.md](PLAN_NL_I18N.md) | NL-Sprachversion (Phase C) |
| [PLAN_GEOFORENSIC_DE.md](PLAN_GEOFORENSIC_DE.md) | Paid-Flow geoforensic.de |
| [MARKET_REALITY_DE_2026.md](MARKET_REALITY_DE_2026.md) | DE-Wettbewerbsrecherche, Strategie-Entscheidung Option B |
| [VISUALS_ROLLOUT_PLAN.md](VISUALS_ROLLOUT_PLAN.md) | 6 Visuals im Vollbericht |
| [REPORT_DESIGN_BRIEF.md](REPORT_DESIGN_BRIEF.md) | Cozy-Brief für Vollbericht-Design |
| [B4_GLOSSAR_DETAILED.md](B4_GLOSSAR_DETAILED.md) | Glossar für wissen-Pages |
| [CURSOR_BACKEND_PIPELINE.md](CURSOR_BACKEND_PIPELINE.md) | Backend-Pipeline-Doku |
| [EU_DIRECTIVE_16_DATA_LAYERS.md](EU_DIRECTIVE_16_DATA_LAYERS.md) | EU-Soil-Directive-Mapping |
| [MAIL_*.md](.) | Mail-Vorlagen (BBSR, BGR BBD, GFZ Erdbeben) |
| [PHASE_D_BUNDESLAENDER.md](PHASE_D_BUNDESLAENDER.md) | DE-Bundesländer-Roadmap |
| [PHASE1_DATA_SOURCES_VERIFIED.md](PHASE1_DATA_SOURCES_VERIFIED.md) | Phase-1-Datenquellen-Verifikation |

---

## 6. Wann der Masterplan aktualisiert wird

Bei **jedem** dieser Trigger:
- Neuer Sprint geplant
- Eine der drei „North-Star"-Aussagen ändert sich (Produkte, Märkte, Pricing-Sichtbarkeit)
- Ein Detail-Plan landet als Code → Eintrag in „Aktueller Stand" verschieben, aus „Offen" entfernen
- Audit-Sweep gemacht → neue Findings als Liste anhängen
- Neuer Detail-Plan entsteht → in Kapitel 5 referenzieren
- CLAUDE.md ändert sich → Konsistenz mit Kapitel 4 prüfen

**Eine Person owned den Masterplan-Sync** — heißt: nicht jeder pusht Änderungen rein, sondern es gibt jemanden der zusammenfasst. Default: Ben.

---

## 7. Glossar (Kurz)

- **EGMS** — European Ground Motion Service, Copernicus, Sentinel-1 InSAR, CC-BY 4.0
- **KCAF/FunderMaps** — NL-Foundation-Risk-Datenbank, A-E-Label im Taxatierapport seit 1.4.2026
- **EU 2025/2360** — EU Soil Monitoring Directive, Umsetzungsfrist Dez 2028
- **BBodSchG/BBodSchV** — Bundes-Bodenschutzgesetz/-Verordnung (DE), 2023 neu erlassen
- **DOI** — Double-Opt-In, UWG § 7(2) Pflicht für Marketing-Mails
- **PAID_SOURCES** — Backend-Set von Lead-Sources, die den Vollbericht auslösen
- **DOI_SOURCES** — Backend-Set von Lead-Sources, die DOI-Mail statt Bericht versenden
- **Pilotphase** — laufender Modus auf bodenbericht.de: kostenlos, Feedback-getrieben
- **Tepnosholding GmbH** — Betreibergesellschaft (Vaihingen a.d. Enz, HRB 801681)
- **Cozy** — Designer für Vollbericht + geoforensic.de-Frontend, eigenes Repo `cozy-frontend`
- **Vollbericht** vs **Teaser** — Vollbericht = 12-Section-PDF (geoforensic.de-Pfad), Teaser = 13-Locked-Cards-Kurzfassung (bodenbericht.de-Pfad)
- **Standortauskunft** / **Bodenrisiko-Screening** — was wir tun. **Nicht** „Gutachten".
