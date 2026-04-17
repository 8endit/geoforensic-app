# Cursor-Task: Premium-Teaser + FAQ auf der Landing

**Ziel:** Landing um einen ehrlichen "Premium-Bericht in Entwicklung"-Teaser
erweitern. Lead-Magnet "Benachrichtige mich wenn verfügbar" plus eine neue
FAQ-Frage.

**Dieser Plan ist bindend.** Nicht interpretieren, nicht erweitern, nicht
neue Features dazudichten. Bei Unklarheit → zurückfragen.

---

## Regeln (für alle Tasks)

1. **Nur die hier genannten Dateien bearbeiten.**
2. **Keine neuen Dependencies**, kein npm install, kein pip install.
3. **Keine CSS-Umbauten** außerhalb der neuen Elemente.
4. **Keine Layout-Änderungen** an bestehenden Sektionen.
5. **Backend bleibt unangetastet** — der neue Form-Submit nutzt die bestehende
   `/api/leads`-Route mit `source: "premium-waitlist"`.
6. **Kein Commit bevor alle 4 Tasks durch sind.**
7. **Formulierungen** siehe unten (wortwörtlich verwenden, nicht umformulieren).

---

## Task 1 — Premium-Teaser-Sektion auf `landing/index.html`

**Datei:** `landing/index.html`

**Wo einfügen:** Direkt **nach** dem FAQ-Abschnitt (`<div id="faq">...</div>`),
**vor** dem Footer. Wenn es keinen klaren Einschub-Punkt gibt, bitte zuerst per
Grep den schließenden `</section>`-Tag des FAQ-Abschnitts finden und direkt
danach einfügen.

**Code (wortwörtlich einfügen):**

```html
<!-- ============================================ -->
<!-- PREMIUM TEASER                               -->
<!-- ============================================ -->
<section id="premium" class="py-16 md:py-24 bg-navy-900 text-white relative overflow-hidden">
  <div class="absolute inset-0 opacity-5">
    <svg class="w-full h-full" xmlns="http://www.w3.org/2000/svg"><defs><pattern id="premium-grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M 40 0 L 0 0 0 40" fill="none" stroke="white" stroke-width="0.5"/></pattern></defs><rect width="100%" height="100%" fill="url(#premium-grid)"/></svg>
  </div>

  <div class="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="text-center mb-10">
      <div class="inline-flex items-center gap-2 bg-brand-500/15 backdrop-blur-sm text-brand-300 text-xs font-semibold tracking-wide uppercase px-4 py-1.5 rounded-full mb-6 border border-brand-500/20">
        <span class="w-2 h-2 bg-brand-400 rounded-full animate-pulse"></span>
        In Entwicklung
      </div>
      <h2 class="text-3xl md:text-4xl font-extrabold leading-tight tracking-tight mb-4">
        Der Premium-Bericht kommt bald.
      </h2>
      <p class="text-lg text-gray-300 max-w-2xl mx-auto leading-relaxed">
        Der kostenlose Bodenbericht ist der Anfang. Am umfassenden Premium-Bericht arbeiten wir gerade &mdash; mit allen Datenschichten, die ein Hauskauf wirklich verlangt.
      </p>
    </div>

    <div class="grid md:grid-cols-2 gap-3 mb-10">
      <!-- Diese Liste darf auf eine finale Auswahl gekürzt werden, siehe Hinweis unten. -->
      <div class="flex items-center gap-3 bg-white/5 border border-white/10 rounded-lg px-4 py-3">
        <svg class="w-5 h-5 text-brand-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75"/></svg>
        <span class="text-sm text-gray-200">Altlasten-Verdachtsflächen (BBodSchG)</span>
      </div>
      <div class="flex items-center gap-3 bg-white/5 border border-white/10 rounded-lg px-4 py-3">
        <svg class="w-5 h-5 text-brand-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75"/></svg>
        <span class="text-sm text-gray-200">Hochwasser-Gefahrenzonen (EU-HWRM)</span>
      </div>
      <div class="flex items-center gap-3 bg-white/5 border border-white/10 rounded-lg px-4 py-3">
        <svg class="w-5 h-5 text-brand-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75"/></svg>
        <span class="text-sm text-gray-200">Radon-Vorsorgegebiete (BfS)</span>
      </div>
      <div class="flex items-center gap-3 bg-white/5 border border-white/10 rounded-lg px-4 py-3">
        <svg class="w-5 h-5 text-brand-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75"/></svg>
        <span class="text-sm text-gray-200">Bergbau-Risiko &amp; Altbergbau</span>
      </div>
      <div class="flex items-center gap-3 bg-white/5 border border-white/10 rounded-lg px-4 py-3">
        <svg class="w-5 h-5 text-brand-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75"/></svg>
        <span class="text-sm text-gray-200">Pestizid-Indikatoren (ESDAC)</span>
      </div>
      <div class="flex items-center gap-3 bg-white/5 border border-white/10 rounded-lg px-4 py-3">
        <svg class="w-5 h-5 text-brand-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75"/></svg>
        <span class="text-sm text-gray-200">Bodenrichtwerte &amp; Markt-Kontext</span>
      </div>
    </div>

    <!-- Waitlist form -->
    <form id="premium-waitlist-form" class="max-w-md mx-auto">
      <label class="sr-only" for="premium-email">E-Mail-Adresse</label>
      <div class="flex flex-col sm:flex-row gap-3">
        <input
          id="premium-email"
          name="email"
          type="email"
          required
          placeholder="Ihre E-Mail-Adresse"
          class="flex-1 px-4 py-3 rounded-lg bg-white/10 backdrop-blur-sm border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-400 focus:border-transparent"
        />
        <button
          type="submit"
          class="bg-brand-500 hover:bg-brand-400 text-white font-semibold px-6 py-3 rounded-lg transition shadow-lg shadow-brand-500/20"
        >
          Benachrichtigen
        </button>
      </div>
      <p class="text-xs text-gray-400 mt-3 text-center">
        Wir melden uns, sobald der Premium-Bericht verfügbar ist. Kein Newsletter, keine Werbung. Jederzeit kündbar.
      </p>
      <div id="premium-waitlist-success" class="hidden mt-4 text-center">
        <div class="inline-flex items-center gap-2 bg-brand-500/20 text-brand-300 px-4 py-2 rounded-lg text-sm font-medium">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
          Eingetragen. Wir melden uns.
        </div>
      </div>
      <div id="premium-waitlist-error" class="hidden mt-4 text-center">
        <p class="text-sm text-red-300">Fehler beim Eintragen. Bitte später erneut versuchen oder an team@geoforensic.de schreiben.</p>
      </div>
    </form>
  </div>
</section>
```

**JavaScript für Form-Submit:**

Am Ende des bestehenden `<script>`-Blocks in `index.html` (der bereits den
Haupt-Lead-Form handled — such nach dem `fetch('/api/leads', ...)` Aufruf
und füge direkt danach den neuen Handler ein):

```javascript
// Premium waitlist form
const premiumForm = document.getElementById('premium-waitlist-form');
if (premiumForm) {
  premiumForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('premium-email').value.trim();
    if (!email) return;
    const btn = premiumForm.querySelector('button[type="submit"]');
    const originalText = btn.textContent;
    btn.textContent = 'Wird gesendet...';
    btn.disabled = true;
    try {
      const res = await fetch('/api/leads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, source: 'premium-waitlist' }),
      });
      if (!res.ok) throw new Error('Request failed');
      document.getElementById('premium-waitlist-form').querySelector('.flex.flex-col').classList.add('hidden');
      document.getElementById('premium-waitlist-success').classList.remove('hidden');
    } catch (err) {
      document.getElementById('premium-waitlist-error').classList.remove('hidden');
    } finally {
      btn.textContent = originalText;
      btn.disabled = false;
    }
  });
}
```

**Akzeptanzkriterium:**
- Die neue Sektion rendert zwischen FAQ und Footer.
- Form-Submit liefert `source: "premium-waitlist"` an `/api/leads`.
- Erfolgreiche Submission zeigt grüne "Eingetragen"-Bestätigung.
- Im Admin-Dashboard (admin.html) erscheinen die Einträge mit Quelle `premium-waitlist`.

---

## Task 2 — Anker-Link im Header-Nav auf `landing/index.html`

**Datei:** `landing/index.html`

**Was tun:** In der Desktop- und Mobile-Navigation einen zusätzlichen Link
"Premium" hinzufügen, der zum neuen `#premium`-Anker springt.

**Desktop Nav** (suchen nach dem Block der Links `So funktioniert's`, `Leistungen`,
`Bewertungen`, `FAQ` enthält): einen Eintrag `<a href="#premium">Premium</a>`
direkt vor dem `FAQ`-Link einfügen. Styling identisch zu den anderen Nav-Links.

**Mobile Nav** (in der gleichen Datei, separater Block): dieselbe Zeile mit
identischem Styling einfügen, an der gleichen logischen Position.

**Akzeptanzkriterium:**
- Klick auf "Premium" scrollt smooth zur neuen Sektion.
- Mobile Nav zeigt den Link ebenfalls.

---

## Task 3 — Neue FAQ-Frage auf `landing/index.html`

**Datei:** `landing/index.html`

**Wo:** Im bestehenden FAQ-Block, als **letzte** FAQ-Item-Box (nach den
aktuell vorhandenen Fragen).

**Genaue Zeilen einfügen:**

```html
<!-- FAQ: Premium -->
<div class="faq-item border border-gray-200 rounded-xl overflow-hidden">
  <button class="faq-toggle w-full flex items-center justify-between px-6 py-5 text-left hover:bg-gray-50 transition">
    <span class="font-semibold text-navy-800 text-sm md:text-base pr-4">Gibt es eine kostenpflichtige Premium-Version?</span>
    <svg class="faq-chevron w-5 h-5 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" /></svg>
  </button>
  <div class="faq-answer px-6 pb-5">
    <p class="text-gray-600 text-sm leading-relaxed">
      Der kostenlose Bodenbericht ist Teil unserer Pilotphase. Eine erweiterte Premium-Version mit Altlasten-Verdachtsflächen, Hochwasser-Zonen, Radon-Daten und weiteren Schichten ist in Entwicklung. Wer sich in unsere <a href="#premium" class="text-brand-600 hover:text-brand-700 underline">Warteliste</a> einträgt, wird informiert, sobald der Premium-Bericht verfügbar ist.
    </p>
  </div>
</div>
```

**Akzeptanzkriterium:**
- Die neue FAQ erscheint als letzte Box im FAQ-Block.
- Chevron-Animation funktioniert wie bei den anderen FAQ-Items.
- Link zur Warteliste springt zum `#premium`-Anker.

---

## Task 4 — Backend: `premium-waitlist` erlauben

**Datei:** `backend/app/routers/leads.py`

**Prüfen:** In `LeadCreate`-Pydantic-Schema steht aktuell `source: str = "quiz"`
als Default. Keine Whitelist, jede String-Source wird akzeptiert.

**Was tun:** Nichts. Das Backend akzeptiert `source: "premium-waitlist"` bereits
ohne Änderung. **NUR bestätigen per Grep**, dass kein Enum/Whitelist die neue
Source ablehnen würde:

```bash
grep -n "quiz\|landing\|premium" backend/app/models.py backend/app/routers/leads.py backend/app/routers/admin.py
```

**Wenn Whitelist existiert:** "premium-waitlist" einfügen. **Wenn keine
Whitelist:** keine Änderung am Backend.

**Zusätzlich:** Prüfen ob `_generate_and_send_lead_report` nur läuft wenn
`address` gesetzt ist. Bei einem Premium-Waitlist-Eintrag ist `address` leer
→ der Background-Task soll **nicht** laufen (kein Report generieren für
Waitlist-Einträge). Bestätigen dass die bestehende Logik

```python
if payload.address and payload.address.strip():
    background_tasks.add_task(...)
```

das schon korrekt handhabt. Wenn ja → keine Änderung.

---

## Hinweis zur Feature-Liste

Die 6 Bullet Points im Premium-Teaser (Task 1) sind **vorläufig**. Ben
entscheidet in den nächsten Tagen welche Datenquellen Phase 1 konkret sind,
basierend auf `docs/DATA_SOURCES_GROUNDSURE_PARITY.md`.

**Für Cursor:** Die 6 Punkte übernehmen wie oben aufgelistet. Änderungen an
der Liste kommen in einem separaten Commit.

---

## Commit

Ein einzelner Commit am Ende:

```
git add landing/index.html
git commit -m "feat(landing): premium teaser + waitlist + FAQ" \
           -m "- New section #premium between FAQ and footer: teaser for upcoming paid product
- Waitlist form posts to /api/leads with source=premium-waitlist
- Nav link 'Premium' in desktop + mobile
- New FAQ entry linking back to waitlist
- Backend requires no change (source field is free-text, address-less leads don't trigger report pipeline)"
```

**Nicht pushen.** Ben reviewed lokal, dann pusht er.

---

## Nicht in Scope (explizit)

- Keine Änderungen an `quiz.html`, `muster-bericht.html`, `datenquellen.html`,
  `impressum.html`, `datenschutz.html`, `404.html`, `admin.html`.
- Keine Änderungen am Backend außer der Grep-Verifikation in Task 4.
- Keine Preis-Angaben auf der Landing ("€29" etc.) — kommt später eigenständig.
- Keine E-Mail-Versand-Änderung (Waitlist-Mails werden später mit separatem
  Template gebaut).
- Kein neuer Tailwind-Build — die genutzten Klassen (`bg-navy-900`, `text-brand-400`,
  `shadow-brand-500/20`) sind in der bestehenden `tailwind.css` bereits enthalten
  weil sie auch im restlichen `index.html` vorkommen.
