Write-Host "===== BUILD START =====" -ForegroundColor Cyan

Set-Location ..
Set-Location ..

Write-Host "Cleaning old build..." -ForegroundColor Yellow

if (Test-Path app\dist) { Remove-Item app\dist -Recurse -Force }
if (Test-Path app\build) { Remove-Item app\build -Recurse -Force }
if (Test-Path app\dist_encrypted) { Remove-Item app\dist_encrypted -Recurse -Force }

Write-Host "Encrypting..." -ForegroundColor Yellow

python -m pyarmor.cli gen `
--output app\dist_encrypted `
app\main.py `
app\auth `
app\database `
app\Integration `
app\onboarding `
app\scheduler `
app\user_master `
app\core

Write-Host "Building exe..." -ForegroundColor Yellow

python -m PyInstaller `
--name OpsPulseB1 `
--onedir `
--clean `
--noconfirm `
--add-data "app/static;static" `
--add-data "app/.env;." `
--add-data "app/config;config" `
app\main.py

Write-Host "===== BUILD DONE =====" -ForegroundColor Cyan