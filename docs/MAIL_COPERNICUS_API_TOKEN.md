# Mail an Copernicus Land Monitoring Service Help-Desk

**An:** `clms-helpdesk@eea.europa.eu`
**Betreff:** API token request for programmatic EGMS access — registered user, B2C application

**Notiz vor Versand:** absenden von einer Adresse die zu deinem Account
gehört (`n00mez0g` ist dein EGMS-Login). Auf Englisch, weil das Help-Desk
EN-first arbeitet. Antwortzeit erfahrungsgemäß 1–3 Wochen.

---

## Body

Dear CLMS Help-Desk team,

I am writing to request an API access token for programmatic, low-volume
access to the EGMS Calibrated (L2b) data products via the
`/insar-api/archive/query` and `/insar-api/archive/download` endpoints
on https://egms.land.copernicus.eu/.

**Background and use case**

I operate Bodenbericht (https://bodenbericht.de), a small commercial
service operated by Tepnosholding GmbH (Germany) that generates
property-specific soil and ground-motion screening reports for German
and Dutch home buyers. Our reports cite EGMS as the data source for
ground-motion velocity and time-series, with the standard CC BY 4.0
attribution ("Generated using European Union's Copernicus Land
Monitoring Service information").

For the velocity-only layer (EGMS L3) we have already imported the
public bulk download into our PostGIS instance. We now want to add the
per-point displacement time-series (EGMS L2b Calibrated, 2019–2023
release) so that buyers see the actual movement history of their
address rather than just the aggregate velocity.

**Why we need a token rather than the bulk download**

EGMS L2b for the whole of Germany is approximately 250 GB across roughly
2,300 Sentinel-1 burst files. The vast majority of those bursts will
never be queried by a paying customer. We therefore want to fetch
bursts *on demand* — when a buyer requests a report for address X, our
backend issues one search query for the small bbox around X and then
downloads only the 2–3 burst files that overlap. After parsing, we
discard the burst CSV and keep only the time-series rows for the
~80 PSI points within 500 m of the address.

This is far less load on the EGMS backend than a one-time full-DE bulk
download would be, and it keeps storage manageable on our side.

**Volume estimate**

- Pilot phase (current): up to ~500 paid reports per month
- Year 2 target: up to ~5,000 paid reports per month
- Per report: 1 search request + 2–3 burst downloads (~300 MB total)
- Reports for the same urban area share bursts and are served from our
  cache after the first request, so realistic upstream egress is far
  below the worst case.

**My account**

EGMS user: `n00mez0g`
Domain: `bodenbericht.de`
Operator: Tepnosholding GmbH (Germany)
Contact: bericht@bodenbericht.de

**What I would need**

If a programmatic API token is available for this kind of use, I would
appreciate guidance on:

1. How to obtain the token (registration form, contract, etc.)
2. The recommended authentication header format for token-based calls
3. Any rate-limit, quota or fair-use policy I should be aware of
4. Whether there is a sandbox endpoint for development/testing

If a formal API token mechanism does not exist for the EGMS Calibrated
product yet, I would also be grateful for a pointer to the right
contact within EEA / ESA — happy to comply with whatever process is in
place, including signing a data-use agreement or providing a more
formal technical description.

Thank you for the great work on EGMS, and for any guidance you can
offer.

Best regards,
[Dein Name]
[Position, Tepnosholding GmbH]
bericht@bodenbericht.de
