# tools/reset_autogen.ps1
# Reset nuclear: borra TODO lo autogenerado (arte, mÃƒÂºsica, manifests, prompts cache, caches de python)
# Ejecutar desde la raÃƒÂ­z del repo.

$ErrorActionPreference = "SilentlyContinue"

Write-Host "== RESET AUTOGEN: starting =="

# Carpetas tÃƒÂ­picas de autogenerados (ajusta si tu repo usa otras)
$paths = @(
  "game\assets\sprites\cards",
  "game\assets\sprites\enemies",
  "game\assets\sprites\biomes",
  "game\assets\music",
  "game\assets\sfx\generated",`r`n  # Legacy compatibility (older root asset tree)`r`n  "assets\sprites\cards",`r`n  "assets\sprites\enemies",`r`n  "assets\sprites\biomes",`r`n  "assets\music",`r`n  "assets\sfx\generated",
  "game\data\generated",
  "game\generated",
  "game\data\card_prompts.json",
  "game\data\art_manifest.json",
  "game\data\bgm_manifest.json",
  "game\data\biome_manifest.json"
)

foreach ($p in $paths) {
  if (Test-Path $p) {
    Remove-Item -Recurse -Force $p
    Write-Host "Deleted: $p"
  }
}

# Limpieza de caches python
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -File -Filter "*.pyc" | Remove-Item -Force

Write-Host "== RESET AUTOGEN: done. Next run will regenerate =="