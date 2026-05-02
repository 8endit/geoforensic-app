# Team-Handbuch — bodenbericht.de

**Stand:** 2026-04-17
**Für:** Gregor, Stefan, Domenico, neue Teammitglieder

Alles was man braucht, um am Projekt zu arbeiten: Zugänge, Deploys, DNS, Notfall-Kommandos.

---

## 1. Was läuft wo

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub (Quellcode)                                          │
│  https://github.com/8endit/geoforensic-app                   │
│  https://github.com/8endit/geoforensic-karte  (Redirect)     │
└────────────┬─────────────────────────────────────────────────┘
             │ git pull (manuell)
             ▼
┌─────────────────────────────────────────────────────────────┐
│  Contabo VPS (185.218.124.158, vmd195593)                    │
│  /opt/bodenbericht/        ← Produktions-Checkout            │
│                                                              │
│  Caddy (Port 80/443)  →  FastAPI (Port 8000 intern)         │
│                              └─ Landing-HTML (Static-Files)  │
│                              └─ /api/* (Leads, Reports, …)   │
│                                                              │
│  PostgreSQL (PostGIS) — Container, nur intern erreichbar    │
└─────────────────────────────────────────────────────────────┘
             │ Let's Encrypt SSL
             ▼
        https://bodenbericht.de
```

**Externe Dienste:**
- **GTM** Container `GTM-KFG5W96X` — https://tagmanager.google.com
- **GA4** Property `G-N9H86S1P8V` — https://analytics.google.com
- **PostHog** EU-Instanz — https://eu.posthog.com
- **Brevo SMTP** — https://app.brevo.com (für Report-Versand)
- **Sentry** EU (Monitoring, sobald aktiviert) — https://sentry.io
- **Better Stack** Uptime (sobald aktiviert) — https://betterstack.com

**Deploy-Modus:** Container werden nur gebaut/gestartet wenn Backend-Code oder `requirements.txt` sich geändert hat. Landing-Änderungen (HTML/CSS/Bilder) gehen **ohne Restart** live, weil FastAPI das `landing/`-Verzeichnis per Read-Only-Bind-Mount serviert.

---

## 2. Zugänge einrichten

### 2.1 GitHub (Code schreiben/lesen)

**Wer einlädt:** Ben oder Domenico (Repo-Owner)

Neue Person bekommt:
1. Einladung per E-Mail auf https://github.com/8endit/geoforensic-app/settings/access
2. Rolle: **Write** (darf pushen) oder **Admin** (wenn sie Zugänge verwalten soll)
3. Person nimmt Einladung an → kann pushen

**Arbeitsweise:**
- Niemand pusht direkt auf `main` ohne Review? → aktuell: Ja, wir pushen direkt (klein genug)
- Ab Team > 3 Personen: Feature-Branches + Pull-Requests

### 2.2 SSH-Zugang zum Server

Für alle Code-Deploys und Betriebsaufgaben.

**Ben/Domenico legen SSH-Key einer neuen Person auf dem Server an:**

```bash
# Auf dem Server (SSH als root):
ssh root@185.218.124.158

# Den öffentlichen SSH-Key der neuen Person anhängen:
mkdir -p /root/.ssh
echo "ssh-ed25519 AAAAC3Nza... gregor@laptop" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
```

**Neue Person generiert ihren Key lokal** (falls noch keiner):
```bash
# Mac/Linux/Windows-Git-Bash:
ssh-keygen -t ed25519 -C "dein-name@laptop"
# Enter drücken (default path), optionales Passwort
cat ~/.ssh/id_ed25519.pub   # ← diesen Inhalt an Ben/Domenico schicken
```

**Test:**
```bash
ssh root@185.218.124.158
# Sollte ohne Passwort einloggen, Prompt root@vmd195593 zeigen
```

**Sicherheits-TODO (später):** Password-Login per SSH abschalten, nur Key-Login erlauben. Aktuell ist ein Passwort-Login für `root` noch erlaubt — siehe `/etc/ssh/sshd_config`, `PasswordAuthentication no` setzen wenn alle Keys drauf sind.

### 2.3 Brevo (Transaktions-Mails)

Gregor: Login-Daten von Ben erfragen (app.brevo.com). SMTP-Key ist im Server-`.env`, nicht im Repo.

### 2.4 Google Workspace / GTM

Gregor hat Inhaber-Zugriff auf GTM + GA4. Andere werden als User in GTM / GA4-Admin eingeladen.

---

## 3. Tägliche Workflows

### 3.1 Code-Änderung deployen (häufigster Fall)

**Lokal auf deinem Rechner:**
```bash
git pull origin main          # neuesten Stand ziehen
# ... Änderungen machen ...
git add <files>
git commit -m "feat(landing): ... beschreibung ..."
git push origin main
```

**Auf dem Server (SSH):**
```bash
ssh root@185.218.124.158
cd /opt/bodenbericht
git pull origin main
```

Das reicht für **reine Landing-/HTML-/Bild-Änderungen**.

### 3.2 Backend-Code geändert → Container rebuild nötig

Wenn sich eine Python-Datei unter `backend/app/` oder `backend/requirements.txt` geändert hat:

```bash
cd /opt/bodenbericht
git pull origin main
docker compose build backend
docker compose up -d
docker compose logs backend --tail 30
```

Erwartung im Log: `Application startup complete.` — dann läuft der neue Backend.

### 3.3 Datenbank-Migration

Aktuell macht FastAPI `Base.metadata.create_all` beim Start (siehe `backend/app/main.py`). Schema-Änderungen brauchen deshalb manchmal Alembic — frage Domenico bevor du `backend/app/models.py` änderst.

### 3.4 Rollback, wenn Deploy kaputt ist

```bash
cd /opt/bodenbericht
git log --oneline -10       # Commit-Hashes anschauen
git reset --hard <letzter-guter-commit-hash>
docker compose build backend && docker compose up -d
```

**Wichtig:** `git reset --hard` ist destruktiv lokal. Für Rollback auf GitHub: `git revert <kaputter-hash>` + push, dann pull auf Server.

---

## 4. DNS-Konfiguration

### 4.1 Aktueller Stand (bei Domain-Registrar)

| Typ | Host | Wert | Status |
|---|---|---|---|
| A | `bodenbericht.de` (`@`) | `185.218.124.158` | ✅ aktiv |
| A | `www.bodenbericht.de` | `185.218.124.158` | ✅ aktiv |

Das reicht, damit die Seite läuft und Let's Encrypt SSL zieht.

### 4.2 Optional aber empfohlen

**AAAA-Record (IPv6):** wenn Contabo IPv6 bereitstellt (in der VPS-Konsole nachsehen). Verbessert Erreichbarkeit für IPv6-only-Netze, kostet nichts.

**CAA-Record (TLS-Härtung):** nur Let's Encrypt darf Zertifikate für die Domain ausstellen. Schutz gegen Mis-Issuance.
```
bodenbericht.de. CAA 0 issue "letsencrypt.org"
```

**MX + SPF/DKIM/DMARC (wenn Mails von `@bodenbericht.de` versendet werden sollen):**

Aktuell sendet Brevo im Namen von `bericht@geoforensic.de` — SPF/DKIM gehört dann zur **geoforensic.de**-Domain, nicht zu bodenbericht.de. Wenn ihr irgendwann auf `bericht@bodenbericht.de` umstellt:

| Typ | Host | Wert |
|---|---|---|
| MX | `bodenbericht.de` | `10 mx1.example.com` (Brevo gibt den Hostname vor) |
| TXT | `bodenbericht.de` | `v=spf1 include:spf.brevo.com ~all` |
| TXT | `mail._domainkey.bodenbericht.de` | DKIM-Key aus Brevo-Panel |
| TXT | `_dmarc.bodenbericht.de` | `v=DMARC1; p=none; rua=mailto:dmarc@bodenbericht.de` |

SPF + DKIM ohne diese Records: Mails landen mit hoher Wahrscheinlichkeit im Spam. **Erst einrichten, wenn Mails tatsächlich von @bodenbericht.de kommen sollen.**

### 4.3 DNS-Test

Von überall (nicht nur dem Server):
```bash
dig +short bodenbericht.de @8.8.8.8        # Google DNS
dig +short bodenbericht.de @1.1.1.1        # Cloudflare DNS
# Beide müssen 185.218.124.158 zeigen
```

Wenn nicht: Propagation-Wartezeit (bis 24h), oder DNS-Einstellungen im Registrar-Panel prüfen.

---

## 5. Monitoring & Ops

### 5.1 Sentry (Backend-Fehler) — LIVE seit 2026-05-02

EU-Region (`ingest.de.sentry.io`), DSN steht in der **Repo-Root `.env`** (NICHT `backend/.env` — siehe `memory/bodenbericht_sentry_config.md`). DSGVO-konform: `send_default_pii=False` plus `before_send`-Hook der E-Mail-Pattern in Strings/Headers/extras scrubbt. Datenschutzerklärung um Sentry-Sektion ergänzt.

Test-Crash: `curl -X POST https://bodenbericht.de/api/_sentry-test` (existiert nur wenn Endpoint registriert; sonst per `docker compose exec backend python -c "import sentry_sdk; sentry_sdk.capture_message('handbook test')"`).

### 5.2 Better Stack (Uptime-Ping) — Setup-Anleitung

**Status:** noch nicht angelegt. Sobald Phase-A-Reststeine (SMTP-Domain) durch sind, einrichten — Outage-Detection ist VOR größerer Werbung essentiell.

**Schritte:**

1. Account anlegen auf https://betterstack.com (Free-Plan reicht: 10 Monitore, 3-min-Intervall, E-Mail-Alerts)
2. Drei Monitore anlegen:

| Name | URL | Methode | Intervall | Erwartung |
|---|---|---|---|---|
| `bodenbericht-homepage` | `https://bodenbericht.de/` | GET | 3 min | HTTP 200, enthält String `Bodenbericht` |
| `bodenbericht-api-health` | `https://bodenbericht.de/api/health` | GET | 3 min | HTTP 200, JSON `{"status":"ok"}` |
| `bodenbericht-cert-expiry` | `https://bodenbericht.de/` | GET (TLS-Check) | 24 h | TLS-Zertifikat ≥ 14 Tage Restlaufzeit |

3. Alert-Channel: E-Mail an `bericht@bodenbericht.de` + Backup an Gregor + Ben
4. Eskalation: 1 Down-Check = stille Notiz, 2 in Folge = E-Mail, 5 in Folge = E-Mail mit `[CRITICAL]`-Prefix
5. Status-Page (optional, kostenlos): https://bodenbericht.betteruptime.com — Link in Footer der bodenbericht.de aufnehmen falls externe Auskunft gewünscht (für B2B-Käufer wichtig)

**Verifikation nach Setup:**
- Container kurz stoppen (`docker compose stop backend`) → innerhalb 6 min Alert
- Container hochfahren (`docker compose up -d backend`) → "Resolved"-Mail innerhalb 6 min

### 5.3 Manuelle Health-Checks

```bash
# Von irgendwo aus:
curl -sI https://bodenbericht.de/ | head -3
curl -sI https://bodenbericht.de/api/health | head -3

# Auf dem Server:
docker compose ps             # alle Container auf Running?
docker compose logs backend --tail 50
docker compose logs db --tail 20
systemctl status caddy --no-pager | head -10
```

### 5.4 Wenn die Seite offline ist

1. **DNS noch ok?** `dig +short bodenbericht.de` → muss 185.218.124.158 zeigen
2. **Server erreichbar?** `ping 185.218.124.158` oder SSH-Versuch
3. **Caddy läuft?** `systemctl status caddy` — wenn nicht: `systemctl restart caddy`
4. **Docker läuft?** `docker compose ps` — wenn ein Container "Exited": Logs prüfen + `docker compose up -d`
5. **Datenbank läuft?** Backend crasht oft weil DB nicht erreichbar — `docker compose logs db`

---

## 6. Notfall-Telefonbuch

| Wer | Verantwortlich für |
|---|---|
| **Ben** | Code-Owner, SSH-Zugang, Server-Root, DNS-Registrar |
| **Domenico** | Infrastruktur (Contabo), Docker, Datenbank, DNS |
| **Gregor** | Marketing, GTM/GA4, Brevo, Domain-Kauf |
| **Stefan** | Produkt, Roadmap, Kunden-Kontakt |

**Wenn Ben und Domenico nicht erreichbar:**
- Contabo-Kundenportal (Zugang bei Ben) — Server neu starten möglich
- Domain-Registrar-Panel (Zugang bei Gregor) — DNS ändern möglich
- GitHub-Repo ist öffentlich lesbar, nicht gelöscht-werden-können

---

## 7. Häufige Fallen

**"Ich hab gepusht aber seh die Änderung nicht auf bodenbericht.de":**
- `git pull` auf dem Server vergessen
- Oder Browser-Cache — Ctrl+Shift+R
- Oder Änderung am Backend → Container-Rebuild nötig

**"Mails kommen nicht an":**
- Backend-Logs prüfen: `docker compose logs backend | grep -i mail`
- SPF/DKIM auf Sender-Domain (aktuell geoforensic.de) prüfen
- Brevo-Quota checken: https://app.brevo.com → Transactional → Statistics
- War's ein Geocoding-Fehler? `docker compose logs backend | grep "422"`

**"Der Container startet nicht":**
- 9 von 10 mal: `requirements.txt` geändert, aber `docker compose build` vergessen
- Fix: `docker compose build --no-cache backend && docker compose up -d`

**"Push abgewiesen wegen merge conflict":**
- Jemand anders hat parallel gepusht
- `git pull --rebase origin main` → Konflikte in Editor lösen → `git rebase --continue` → `git push`

---

## 8. Kurz-Referenz-Karte (zum Ausdrucken)

```
SSH:            ssh root@185.218.124.158
Deploy:         cd /opt/bodenbericht && git pull origin main
Backend-Reload: docker compose build backend && docker compose up -d
Log-Check:      docker compose logs backend --tail 50
Caddy-Log:      journalctl -u caddy -n 30
Rollback:       git reset --hard <letzter-guter-hash>
Health:         curl -sI https://bodenbericht.de/api/health
```
