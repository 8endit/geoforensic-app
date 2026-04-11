# GeoForensic API Endpoints

Base URL: `https://geoforensic.de` (production) / `http://localhost:8000` (dev)

Alle Requests mit `Content-Type: application/json`. Auth-Endpoints liefern JWT Token, alle anderen brauchen `Authorization: Bearer <token>` Header.

## Auth

```
POST /api/auth/register
Body: { email, password, company_name?, gutachter_type? }
Response: { access_token, token_type, user: { id, email, company_name, gutachter_type } }

POST /api/auth/login
Body: { email, password }
Response: { access_token, token_type, user }

GET /api/auth/me
Header: Authorization: Bearer <token>
Response: { id, email, company_name, gutachter_type, created_at }
```

## Reports (Auth required)

```
POST /api/reports/create
Body: { address: string, radius_m: int (100-2000), aktenzeichen?: string }
Response: { id, address_input, status: "processing", latitude, longitude, ... }
Note: Report wird im Hintergrund generiert. Status pollen via GET.

GET /api/reports
Response: [ { id, address_input, status, ampel, paid, geo_score, created_at } ]

GET /api/reports/:id
Response: { id, address_input, status, ampel, paid, geo_score, pdf_available,
            report_data: { analysis, geology, flood, slope, geo_score, raw_points } }

GET /api/reports/:id/pdf
Response: PDF file (nur wenn paid=true, sonst 402)

GET /api/reports/:id/raw.csv
Response: CSV file (nur wenn paid=true, sonst 402)
```

## Free Preview (kein Auth)

```
POST /api/reports/preview
Body: { address: string }
Response: { ampel: "gruen"|"gelb"|"rot", point_count, address_resolved, latitude, longitude }
Rate-Limited: 10 Requests/Stunde pro IP
```

## Payments (Auth required)

```
POST /api/payments/checkout
Body: { report_id: UUID }
Response: { checkout_url: string }
Note: Redirect User zu checkout_url (Stripe). Nach Zahlung redirect zurueck mit ?paid=1

POST /api/payments/webhook
Note: Stripe ruft das auf. Setzt report.paid=1 bei checkout.session.completed.
```

## Health

```
GET /api/health
Response: { status: "ok", service: "geoforensic-api", version: "0.1.0" }
```

## Report Status Flow

```
create -> status:"processing" -> (Pipeline laeuft) -> status:"completed" / status:"failed"
completed + !paid -> "Report kaufen" Button -> Stripe Checkout -> paid=true -> PDF Download
```

## Ampel-Klassifikation

| Ampel | Velocity | Bedeutung |
|-------|----------|-----------|
| gruen | < 2 mm/a | Unauffaellig |
| gelb | 2-5 mm/a | Auffaellig, beobachten |
| rot | > 5 mm/a | Signifikant, Gutachter hinzuziehen |

## GeoForensic Score

| Score | Bedeutung |
|-------|-----------|
| 85-100 | Top-Standort, minimales Risiko |
| 60-84 | Moderate Risiken, weitere Pruefung |
| 0-59 | Erhoehtes Risiko, Gutachter hinzuziehen |
