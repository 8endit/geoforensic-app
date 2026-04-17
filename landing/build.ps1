# Rebuild landing/tailwind.css and landing/tailwind-quiz.css from the source HTMLs.
# Run this after changing Tailwind classes in any *.html file.
#
# Usage (from repo root):
#   cd landing
#   ./build.ps1
#
# First-time setup: download the Tailwind standalone CLI into this folder:
#   curl -L -o tailwindcss.exe https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.15/tailwindcss-windows-x64.exe
# (tailwindcss.exe is .gitignored; every dev downloads their own copy.)

$ErrorActionPreference = "Stop"

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
