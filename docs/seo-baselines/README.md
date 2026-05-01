# SEO-Baselines — Lighthouse-Reports

Maschinenlesbarer Baseline-Stand zum Phasenwechsel im SEO-Branding-Rollout
(`docs/SEO_BRANDING_ROLLOUT_PLAN.md`). Bei jedem späteren Phasen-Endpunkt
einen neuen Datums-Lauf hier ablegen, damit Änderungen messbar sind.

## Lauf

```bash
# Vom Repo-Root, Preview muss laufen (http://localhost:8001/)
npx -y -p lighthouse@latest lighthouse http://localhost:8001/ \
  --preset=desktop --quiet \
  --chrome-flags="--headless=new --no-sandbox" \
  --output=json \
  --output-path=docs/seo-baselines/lighthouse-desktop-$(date +%F).json

npx -y -p lighthouse@latest lighthouse http://localhost:8001/ \
  --form-factor=mobile --quiet \
  --chrome-flags="--headless=new --no-sandbox" \
  --output=json \
  --output-path=docs/seo-baselines/lighthouse-mobile-$(date +%F).json
```

## Baseline 2026-05-01 — Ende Phase A

### Live (`https://bodenbericht.de/`, post-deploy)

Maßgebliche Baseline gegen Phase B vergleichen.

| Kategorie | Desktop | Mobile |
|---|---|---|
| Performance | 99 | 97 |
| Accessibility | 92 | 87 |
| Best Practices | 100 | 100 |
| SEO | **100** | **100** |

Mobile-LCP 2,4 s liegt bereits im Web-Vitals-„Good"-Bereich (<2,5 s).

### Lokal (Preview, zum Vergleich)

Lokaler Lauf war pessimistischer (kein Brotli, kein HTTP/2, dev-mode-Overhead):

| Kategorie | Desktop | Mobile |
|---|---|---|
| Performance | 98 | 82 |
| Accessibility | 92 | 87 |
| Best Practices | 100 | 100 |
| SEO | **100** | **100** |

### Core Web Vitals — Live Mobile (Throttle 4G/Slow CPU)

| Metrik | Wert | Bewertung |
|---|---|---|
| LCP (Largest Contentful Paint) | 2,4 s | gut (<2,5 s) |
| FCP (First Contentful Paint) | 1,7 s | gut |
| CLS (Cumulative Layout Shift) | 0,005 | gut (<0,1) |
| TBT (Total Blocking Time) | 0 ms | gut |

### Bekannte A11y-Lücken (Mobile)

- `aria-dialog-name` – Klaro-Consent-Modal ohne accessible name
- `button-name` – mind. ein Button ohne Label (vermutlich Mobile-Menu)
- `color-contrast` – Kontrast unter 4.5:1 (vermutlich `text-gray-400` auf weiß
  in Trust-Bar)
- `heading-order` – H2 → H4 ohne H3 in Visual-Sektionen

→ Phase B Sprint kann diese in unter 1 h adressieren. Nicht im Phase-A-Scope.

### Performance-Hebel (Mobile)

Hauptursache LCP 4,5 s ist die große Hero-SVG (Risk-Dashboard) plus
Inline-Tailwind-CSS. Phase B kann hier mit einem critical-CSS-Inline plus
Lazy-Loading der nicht-Hero-Visuals den LCP unter 2,5 s drücken. Nicht im
Phase-A-Scope.

## Wie vergleichen

Beim nächsten Lauf (Phase B / Phase C):

```bash
python - <<'PY'
import json, glob, os
runs = sorted(glob.glob("docs/seo-baselines/lighthouse-*-*.json"))
for r in runs:
    d = json.load(open(r, encoding="utf-8"))
    cats = d["categories"]
    print(os.path.basename(r))
    for k, v in cats.items():
        s = v.get("score")
        print(f"  {k:18s} {int(round(s*100)) if s else 'n/a':>3}")
PY
```
