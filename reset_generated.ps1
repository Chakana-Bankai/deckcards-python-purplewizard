Write-Host "Cleaning generated content..."

Remove-Item -Recurse -Force assets\sprites\cards -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force assets\sprites\enemies -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force assets\music -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force game\generated -ErrorAction SilentlyContinue

Write-Host "Done. Generated content will rebuild on next run."