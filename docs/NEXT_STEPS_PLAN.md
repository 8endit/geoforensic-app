# Nächste Schritte — Monitoring + offene Sprint-Tasks

**Stand:** 2026-04-17 (nach Sprint 2 Landing-Zielgruppen-Refactor + Karte-Redirect)

Zwei Kategorien offener Arbeit:
1. **Monitoring** (Gregors Anfrage vom Vormittag) — 4 Alert-Szenarien
2. **Brief-Tasks** #08 / #10 / #11

---

## 1. Monitoring — Sentry + Better Stack

### Ziel

Gregor will Alerts für:
1. Report-Generierung failed (Backend-Exception)
2. Backend-Service down (Container gecrasht)
3. E-Mail-Versand failed (Brevo rejected, Quota erschöpft)
4. Homepage unreachable (Caddy/DNS-Probleme)

### Stack

| Werkzeug | Wofür | Free-Tier |
|---|---|---|
| **Sentry** (EU-Region) | Backend-Exceptions (#1, #3) | 5k Events/Monat |
| **Better Stack** | HTTP-Uptime-Checks (#2, #4) | 10 Monitore, 3-Min-Intervall |

Beides separate Anmeldung, DSGVO-konform (Sentry EU-Region, Better Stack EU).

### 1a. Sentry-Setup (User + ich gemeinsam)

**Was du machen musst (5 Min):**
1. https://sentry.io/signup/ → **Region: European Union** wählen
2. Organization: `Tepnosholding` · Projekt anlegen:
   - Platform: **Python / FastAPI**
   - Projektname: `bodenbericht-backend`
3. Auf dem Onboarding-Screen erscheint der **DSN** (`https://abc...@o123.ingest.de.sentry.io/456`)
4. DSN kopieren → mir schicken

**Was ich dann mache (parallel vorbereitet):**
- `sentry-sdk[fastapi]` zur `backend/requirements.txt` hinzufügen
- In `backend/app/main.py` die SDK-Init vor App-Start einhängen
- `SENTRY_DSN` als ENV-Variable in docker-compose.yml + .env.example
- Test: `curl` auf einen synthetischen 500-Endpoint, check ob in Sentry-Dashboard ankommt

**Was Gregor in Sentry konfiguriert (5 Min):**
- Alert Rule → Event-Type: `error` → Issue is new → Mail an `gregor@...` + `team@geoforensic.de`

### 1b. Better Stack Uptime (reine User-Aktion)

**Was du machen musst (10 Min):**
1. https://betterstack.com/users/sign-up → EU-Region
2. Team: `Bodenbericht` · **Monitoring → Create Monitor**:

   **Monitor 1 — Homepage**
   - Name: `Bodenbericht Homepage`
   - URL: `https://bodenbericht.de/`
   - Check frequency: 3 Minuten
   - Expected status: 200
   - Keyword match (optional): `Bodenbericht` im Body
   - Alert after: 2 failed checks hintereinander

   **Monitor 2 — Backend API Health**
   - Name: `Bodenbericht Backend Health`
   - URL: `https://bodenbericht.de/api/health`
   - Check frequency: 3 Minuten
   - Expected status: 200
   - Alert after: 2 failed checks hintereinander

3. **Notification Channels** (oben → Settings → Notification channels):
   - E-Mail: Gregor + Ben
   - Optional: SMS für Homepage-Monitor (Free-Tier hat 5 SMS/Monat)

Ich brauche **nichts** von Better Stack — läuft rein extern, fertig.

### Deploy-Reihenfolge

1. Du legst Sentry-Account an → schickst DSN
2. Ich baue SDK-Integration + push (du pullst auf Server + restart backend)
3. Du legst Better-Stack-Monitore an (parallel, unabhängig)
4. Alles läuft — nächste 24h beobachten

---

## 2. Brief-Task #08 — Premium-Warteliste Anreiz (30 Min)

### Ziel

Premium-Sektion auf Landing hat aktuell nur "kommt bald" / "in Entwicklung". Domenico (Brief): ohne konkreten Zeitrahmen oder Anreiz ist Eintragungsrate niedrig.

### Umsetzung

**Variante C aus Brief = Kombination** (Zeit + Anreiz):

- Launch-Zeitrahmen: **Q3/2026**
- Early-Bird-Vorteil: **30% dauerhafter Rabatt für Pilot-Anmelder**

Text-Änderung in der Premium-Sektion von `landing/index.html`:

> **Alt:** "Kommt bald." / "In Entwicklung."
>
> **Neu:** "Launch geplant für Q3/2026. Pilot-Anmelder erhalten dauerhaften 30% Rabatt auf die erste Premium-Version."

### Umfang

- Nur Copy-Änderung, kein Backend
- Kein Counter ("Bereits X auf der Warteliste") — wir haben noch nicht genug Eintragungen, das wäre peinlich
- Falls Counter später: per JS aus `/api/_admin/leads?source=premium_waitlist&limit=1000` zählen

### Ich mache das direkt parallel zu Monitoring.

---

## 3. Brief-Task #10 — Accessibility-Basics (1–2 h)

### Ziel

Lighthouse-Accessibility-Score ≥ 90. BFSG greift ab 28.06.2025 für B2C-Onlineshops — noch nicht verpflichtend für uns, aber für Seriosität der Marke + SEO relevant.

### Was zu prüfen/fixen ist

Alle in `landing/*.html`:
- [ ] Alle `<img>`-Tags haben `alt`-Attribute (dekorative: `alt=""`, inhaltlich: aussagekräftig)
- [ ] Alle `<input>`-Felder haben `<label>` oder `aria-label`
- [ ] Alle Buttons haben sichtbaren Text oder `aria-label`
- [ ] Icon-Buttons (z.B. Mobile-Menü-Hamburger) haben `aria-label`
- [ ] Farbkontraste WCAG AA: Text ≥ 4.5:1, große Headlines ≥ 3:1 (mit Chrome DevTools Contrast-Checker)
- [ ] Tab-Reihenfolge ist logisch, `:focus`-Styles sichtbar (nicht `outline: none` ohne Ersatz)
- [ ] `<html lang="de">` auf allen Seiten (bereits ✅ geprüft)

### Ich mache nach Monitoring + #08 — wenn Zeit.

---

## 4. Brief-Task #11 — Performance / Core Web Vitals (2–3 h)

### Ziel

LCP < 2.5 s, INP < 200 ms, CLS < 0.1, PageSpeed Mobile ≥ 85.

### Abhängigkeit

Braucht **Lighthouse-Lauf auf Live-Server** (nicht localhost), idealerweise in Chrome DevTools → Lighthouse → Mobile → Performance.

### Voraussichtliche Arbeit

1. Lighthouse-Audit gegen https://bodenbericht.de/ laufen lassen (Chrome DevTools)
2. Fixes je nach Befund, typisch:
   - `loading="lazy"` für images below-the-fold (teilweise schon gesetzt)
   - WebP/AVIF statt JPEG (Logo ist PNG, Testimonials JPEG)
   - `preload`/`preconnect` für Google Fonts
   - Unnötiges JS entfernen (z.B. unbenutzten Chart.js-Teil in Quiz)

### Priorität: Niedrig, nach Marketing-Push relevant. Heute nicht.

---

## Reihenfolge heute

1. **Plan schreiben** (dieser Datei) ✅
2. **Task #08 ausführen** — 30 Min, direkt, kein externer Blocker
3. **Sentry SDK ins Backend vorbereiten** — 20 Min, aber **ohne deinen DSN** erstmal nicht live-schaltbar. Ich stage den Code und schreibe DSN als ENV-Var-Platzhalter
4. **Ende für heute** — Rest wenn du mir DSN + Better-Stack-Konto-Status zurückmeldest

Blocker für heute-Abschluss:
- [ ] **DU:** Sentry-Account erstellen (EU-Region) + DSN schicken
- [ ] **DU:** Better-Stack-Account erstellen + 2 Monitore konfigurieren (rein extern, kein Code-Commit)
