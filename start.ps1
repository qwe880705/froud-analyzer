# Insider Risk Investigation Assistant - Windows PowerShell Startup
# Run with: powershell -ExecutionPolicy Bypass -File start.ps1

Write-Host "=== Insider Risk Investigation Assistant ===" -ForegroundColor Cyan
Write-Host ""

# ── Backend ──────────────────────────────────────────────────────────
Write-Host "[1/2] Setting up Backend..." -ForegroundColor Yellow

Set-Location backend

if (-not (Test-Path ".venv")) {
    Write-Host "      Creating Python virtual environment..."
    python -m venv .venv
}

Write-Host "      Installing dependencies..."
& .\.venv\Scripts\pip install -q -r requirements.txt

Write-Host "      Starting FastAPI on http://localhost:8000" -ForegroundColor Green
$backend = Start-Process -FilePath "cmd" `
    -ArgumentList "/k title Backend - Insider Risk API && .venv\Scripts\python -m uvicorn app.main:app --reload --port 8000" `
    -PassThru

Set-Location ..

# ── Frontend ─────────────────────────────────────────────────────────
Write-Host "[2/2] Setting up Frontend..." -ForegroundColor Yellow

Set-Location frontend

if (-not (Test-Path "node_modules")) {
    Write-Host "      Installing npm packages (first run ~2 min)..."
    npm install
}

Write-Host "      Starting React on http://localhost:3000" -ForegroundColor Green
$frontend = Start-Process -FilePath "cmd" `
    -ArgumentList "/k title Frontend - Insider Risk UI && npm run dev" `
    -PassThru

Set-Location ..

# ── Done ─────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== Servers Starting ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "  App:      " -NoNewline; Write-Host "http://localhost:3000" -ForegroundColor Green
Write-Host "  API Docs: " -NoNewline; Write-Host "http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host ""
Write-Host "  Import sample data at http://localhost:3000/import" -ForegroundColor Yellow
Write-Host "  Import order:"
Write-Host "    1. HR System    -> backend\sample_data\01_hr_users.csv"
Write-Host "    2. Purview DLP  -> backend\sample_data\02_purview_dlp.csv"
Write-Host "    3. Entra ID     -> backend\sample_data\03_entra_id_login.csv"
Write-Host "    4. Cloud Upload -> backend\sample_data\04_cloud_upload.csv"
Write-Host "    5. Email Log    -> backend\sample_data\05_email_log.csv"
Write-Host ""
Write-Host "Two CMD windows opened. Close them to stop servers." -ForegroundColor Gray
Read-Host "Press Enter to exit this window"
