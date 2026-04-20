# Gregor Landing Page Integration

Designer: Gregor  
Date: 2026-04-16

## Files

| File | Location in repo | Purpose |
|---|---|---|
| `index.html` | `landing/index.html` | Marketing landing page (Tailwind CDN, Inter font) |
| `quizindex.html` | `landing/quiz.html` | 4-question quiz funnel + email capture |

## Funnel Flow

```
landing/index.html
  └── CTA buttons → landing/quiz.html
        └── handleSubmit() → POST /api/leads
              └── on success → redirect to /register (main app)
```

## Backend Changes

### New model: `Lead` (backend/app/models.py)
```
id          UUID PK
email       VARCHAR(255) indexed
quiz_answers JSONB
source      VARCHAR(100) default "quiz"
created_at  TIMESTAMPTZ server default now()
```
Table is auto-created at startup via `Base.metadata.create_all`.

### New router: `POST /api/leads` (backend/app/routers/leads.py)
- No auth required (public endpoint — lead capture is pre-registration)
- Rate-limited: 30/hour per IP (via slowapi)
- Accepts: `{ email, answers, timestamp, source }`
- Returns 201: `{ id, email, created_at }`
- Registered in `main.py`

## HTML Wiring

### quiz.html — replace `handleSubmit()`

Replace the `console.log`-only version with:

```javascript
async function handleSubmit(e) {
  e.preventDefault();
  const email = document.getElementById("email").value;
  try {
    const res = await fetch("/api/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        answers,
        timestamp: new Date().toISOString(),
        source: "quiz",
      }),
    });
    if (!res.ok) throw new Error("submit failed");
    window.location.href = "/register";
  } catch (err) {
    console.error(err);
    // show inline error to user
  }
}
```

### index.html — CTA buttons

Replace all `href="#cta"` occurrences with `href="quiz.html"`.

## Deployment Notes

- `landing/` is static HTML — served by the FastAPI app via a static mount (see `backend/app/main.py`). In production it lives on the Contabo VPS behind Caddy; see `docs/TEAM_HANDBOOK.md` for the operational runbook.
- If served from a different origin than the API, set `CORS_ORIGINS` in backend `.env` accordingly.
- No Alembic migration needed: `Base.metadata.create_all` creates the `leads` table on startup.
