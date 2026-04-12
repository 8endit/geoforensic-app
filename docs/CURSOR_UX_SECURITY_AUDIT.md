# UX & Security Audit — Aufgaben für Cursor

Stand: 2026-04-12, nach erstem End-to-End-Durchklick.
Alle Änderungen in Cozy's Design System (siehe CLAUDE.md).

---

## SECURITY — Muss vor Go-Live gefixt werden

### S1: Passwort-Bestätigungsfeld bei Registrierung
**Datei:** `frontend/.../app/register/page.tsx`
**Problem:** Nur ein Passwort-Feld. Tippfehler → User locked out.
**Fix:** Zweites Feld `confirmPassword` hinzufügen. Submit nur wenn `password === confirmPassword`. Fehlermeldung: "Passwörter stimmen nicht überein."

### S2: Passwort-Stärke-Anzeige
**Datei:** `frontend/.../app/register/page.tsx`
**Problem:** Backend validiert min 8 Zeichen, aber User sieht keine Anforderungen.
**Fix:** Unter dem Passwortfeld anzeigen: "Mindestens 8 Zeichen". Optional: Stärkeindikator (schwach/mittel/stark) basierend auf Länge + Zeichenvielfalt.

### S3: JWT Token Expiry Handling
**Datei:** `frontend/.../lib/auth-context.tsx`
**Problem:** Token ist 24h gültig (1440 Min). Wenn er abläuft, bekommt der User kryptische Fehler statt eines Logouts.
**Fix:** In `getMe()` catch-Block: wenn 401 zurückkommt → Token aus localStorage löschen, User auf `/login` redirecten, Toast "Sitzung abgelaufen, bitte erneut einloggen."

### S4: Rate-Limit Feedback im Frontend
**Problem:** Preview hat 10/hour Rate-Limit. Wenn das greift, bekommt der User "429" ohne Erklärung.
**Fix:** Im `previewReport` Error-Handler: wenn Status 429 → Toast "Zu viele Anfragen. Bitte warten Sie einige Minuten."

---

## UX — Nutzererlebnis verbessern

### U1: Sprache konsistent machen (aktuell Deutsch/Englisch gemischt)
**Problem:** Buttons sagen "Preview berechnen" (Deutsch) aber Placeholder sagt "Street + house number" (Englisch). "Check your property" ist Englisch. Dashboard zeigt "paid/unpaid" auf Englisch.
**Fix:** Alles auf Deutsch ODER alles auf Englisch. Für NL-Markt später: `/nl/` Route mit niederländischen Texten. Für jetzt: komplett Deutsch.

Konkrete Änderungen:
- `property-form.tsx` Zeile 71: "Check your property" → "Grundstück prüfen" (oder für NL-Version: "Check je adres")
- `property-form.tsx` Zeile 77: "Street + house number" → "Straße + Hausnummer"
- `property-form.tsx` Zeile 85: "Postal code + city" → "PLZ + Stadt"
- `property-form.tsx` Zeile 96: "Loading..." → "Lädt..."
- `preview-result.tsx` Zeile 30: "Login/Register für vollständigen Report" → "Anmelden für vollständigen Report"
- `register/page.tsx` Zeile 41: "Register" → "Registrieren"
- `register/page.tsx` Zeile 43-66: Alle Placeholder auf Deutsch
- `dashboard/page.tsx` Zeile 57: "paid"/"unpaid" → "Bezahlt"/"Offen"
- `reports/[id]/page.tsx` Zeile 79: JSON dump → menschenlesbare Darstellung (siehe U4)

### U2: Paywall-Flow klarer machen
**Problem:** User erstellt Report → sieht "Report kaufen" Button → klickt → wird auf Dashboard redirected mit `?paid=1` (Mock-Modus ohne Stripe). Aber der Report ist trotzdem nicht als "paid" markiert weil der Webhook nicht feuert.
**Fix für Mock-Modus:** Wenn `STRIPE_SECRET_KEY` leer ist (Mock): der Checkout-Redirect sollte den Report automatisch als `paid=true` markieren. Aktuell passiert das nur über den Webhook, der im Mock-Modus nie kommt.

Konkret in `backend/app/routers/payments.py`:
- Nach dem Mock-Checkout (`cs_mock_*`): Report direkt auf `paid=True` setzen.
- Oder: einen separaten `/api/payments/mock-complete` Endpoint für Dev/Test.

### U3: Report-Detail-Seite — rohen JSON ersetzen
**Datei:** `frontend/.../app/reports/[id]/page.tsx` Zeile 78-82
**Problem:** Report-Daten werden als roher JSON-Dump angezeigt: `JSON.stringify(report.report_data, null, 2)`. Das ist nicht nutzerfreundlich.
**Fix:** Strukturierte Darstellung der Analyse-Daten:

```tsx
{/* Statt JSON dump: */}
<div className="grid grid-cols-2 gap-4">
  <div className="border border-border p-4 text-center">
    <div className="text-2xl font-bold">{report.report_data?.analysis?.point_count ?? 0}</div>
    <div className="text-xs text-foreground/60 uppercase">Messpunkte</div>
  </div>
  <div className="border border-border p-4 text-center">
    <div className="text-2xl font-bold">{report.report_data?.analysis?.max_abs_velocity_mm_yr?.toFixed(1) ?? "—"}</div>
    <div className="text-xs text-foreground/60 uppercase">Max. Geschwindigkeit (mm/a)</div>
  </div>
  <div className="border border-border p-4 text-center">
    <div className="text-2xl font-bold">{report.report_data?.analysis?.weighted_velocity_mm_yr?.toFixed(1) ?? "—"}</div>
    <div className="text-xs text-foreground/60 uppercase">Gewichtet (mm/a)</div>
  </div>
  <div className="border border-border p-4 text-center">
    <div className="text-2xl font-bold">{report.geo_score ?? 0}</div>
    <div className="text-xs text-foreground/60 uppercase">GeoScore</div>
  </div>
</div>
```

Plus: Velocity-Histogram als einfaches Balkendiagramm (report_data.velocity_histogram hat die Bins).

### U4: Ampel-Badge größer und farbiger auf Report-Detail
**Problem:** Auf der Report-Detail-Seite steht nur Text: "Ampel: gruen". Kein visuelles Badge wie bei der Preview.
**Fix:** Gleichen `AMPEL_STYLE` Badge verwenden wie in `preview-result.tsx`, aber größer.

### U5: Leerer Report soll nicht "GRUEN" zeigen
**Problem:** Wenn die DB leer ist, zeigt jede Adresse "GRUEN, 0 Punkte". Das ist irreführend — grün impliziert "alles OK" obwohl wir keine Daten haben.
**Fix:** Wenn `point_count === 0`: Ampel-Badge durch graues "KEINE DATEN" Badge ersetzen. Text: "Für diesen Standort liegen aktuell keine Messpunkte vor."

In `preview-result.tsx`:
```tsx
{data.point_count === 0 ? (
  <div className="inline-flex border px-2 py-1 text-xs uppercase font-mono text-foreground/40 border-foreground/20">
    Keine Daten
  </div>
  <p className="font-mono text-xs text-foreground/50">
    Für diesen Standort liegen aktuell keine Messpunkte vor.
  </p>
) : (
  // normales Ampel-Badge
)}
```

In `backend/app/routers/reports.py` Zeile 259-263: Wenn `points` leer ist, `ampel` auf `None` setzen statt `Ampel.gruen`.

### U6: "Neuer Report" Button im Dashboard geht zu Anchor-Link
**Datei:** `frontend/.../app/dashboard/page.tsx` Zeile 37
**Problem:** "Neuer Report" verlinkt auf `/#contact` — das scrollt auf der Landing Page zum Formular. Funktioniert, ist aber ein komischer Flow wenn man schon eingeloggt ist.
**Fix:** Eigene `/check` Route mit dem PropertyForm direkt, ohne Hero-Section.

### U7: Loading States verbessern
**Problem:** "Lade Report..." und "Lade Reports..." sind nur Text. Kein Spinner, keine Animation.
**Fix:** Einen einfachen Pulsing-Dot oder Skeleton-Loader im Cozy Design (grüner Punkt mit Glow-Animation, `animate-pulse`).

---

## REIHENFOLGE

**Zuerst (Security, vor Go-Live):**
1. S1 — Passwort-Bestätigung
2. S5 — Leerer Report "KEINE DATEN" statt "GRUEN" (= U5, ist auch Security weil irreführend)
3. S3 — Token Expiry
4. S4 — Rate-Limit Feedback

**Dann (UX, vor erstem Kundenkontakt):**
5. U1 — Sprache konsistent
6. U2 — Mock-Paywall fixen
7. U3 — JSON dump → strukturierte Ansicht
8. U4 — Ampel-Badge auf Report-Detail

**Nice-to-have (später):**
9. U6 — Eigene /check Route
10. U7 — Loading States
11. S2 — Passwort-Stärke-Anzeige

---

## NICHT ÄNDERN

- Design System (Farben, Fonts, Buttons, Cards) → bleibt wie von Cozy definiert
- API Schemas → bleiben unverändert
- Auth Flow (JWT + localStorage) → reicht für MVP
- Stripe Integration → bleibt wie es ist, Mock-Modus für Dev
