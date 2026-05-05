# Rebuild landing/tailwind.css and landing/tailwind-quiz.css from the source HTMLs.
# Run this after changing Tailwind classes in any *.html file.
#
# Usage (from repo root):
#   ./scripts/build_landing.ps1
#
# 2026-05-05 verlegt aus landing/build.ps1 nach scripts/build_landing.ps1
# weil das alte Skript per FastAPI-StaticFiles-Mount unter
# https://bodenbericht.de/build.ps1 öffentlich abrufbar war.
#
# Tailwind-CLI-Erstinstallation in landing/:
#   curl -L -o landing/tailwindcss.exe https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.15/tailwindcss-windows-x64.exe
# (landing/tailwindcss.exe ist .gitignored; jeder Dev lädt sich seine Kopie.)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $RepoRoot 'landing')
try {

if (-not (Test-Path "./tailwindcss.exe")) {
  Write-Host "tailwindcss.exe not found. Downloading v3.4.15..."
  Invoke-WebRequest -Uri "https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.15/tailwindcss-windows-x64.exe" -OutFile "./tailwindcss.exe"
}

if (-not (Test-Path "./klaro/klaro.js")) {
  Write-Host "klaro.js not found. Downloading v0.7.22..."
  New-Item -ItemType Directory -Force -Path "./klaro" | Out-Null
  Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/npm/klaro@0.7.22/dist/klaro.js" -OutFile "./klaro/klaro.js"
}

Write-Host "Building tailwind.css (index, muster-bericht, datenquellen, admin)..."
./tailwindcss.exe -c tailwind.config.js -i input.css -o tailwind.css --minify

Write-Host "Building tailwind-quiz.css (quiz)..."
./tailwindcss.exe -c tailwind.quiz.config.js -i input.css -o tailwind-quiz.css --minify

Write-Host ""
Write-Host "Done. Sizes:"
Get-ChildItem tailwind*.css | Select-Object Name, Length | Format-Table -AutoSize

}
finally {
  Pop-Location
}
