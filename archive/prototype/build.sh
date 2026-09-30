#!/bin/bash
set -e
cd /home/claude/app
OUT=family-archive.html
{
cat <<'H'
<!doctype html>
<html lang="uz">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Oilaviy arxiv</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Spectral:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<style>
H
cat style.css
echo "</style></head><body><div id=\"app\"></div><div id=\"toast\" role=\"status\" aria-live=\"polite\" hidden></div><script>"
cat i18n.js uz.js core.js demo.js tree.js views.js search.js accounts.js forms.js
echo "</script></body></html>"
} > $OUT
echo built $(wc -c < $OUT) bytes
