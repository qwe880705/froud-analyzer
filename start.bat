@echo off
echo === Insider Risk Investigation Assistant ===
echo.

echo [1/2] Starting Backend...
cd backend

if not exist ".venv" (
    echo     Creating Python virtual environment...
    python -m venv .venv
)

echo     Installing dependencies...
.venv\Scripts\pip install -q -r requirements.txt

echo     Starting FastAPI server on http://localhost:8000
start "Backend - Insider Risk API" cmd /k ".venv\Scripts\python -m uvicorn app.main:app --reload --port 8000"

cd ..

echo [2/2] Starting Frontend...
cd frontend

if not exist "node_modules" (
    echo     Installing npm packages (first run takes a few minutes)...
    npm install
)

echo     Starting React dev server on http://localhost:3000
start "Frontend - Insider Risk UI" cmd /k "npm run dev"

cd ..

echo.
echo === Both servers are starting ===
echo.
echo   App:      http://localhost:3000
echo   API Docs: http://localhost:8000/api/docs
echo.
echo   Import sample data at: http://localhost:3000/import
echo   Order:
echo     1. HR System       ^> backend\sample_data\01_hr_users.csv
echo     2. Purview DLP     ^> backend\sample_data\02_purview_dlp.csv
echo     3. Entra ID        ^> backend\sample_data\03_entra_id_login.csv
echo     4. Cloud Upload    ^> backend\sample_data\04_cloud_upload.csv
echo     5. Email Log       ^> backend\sample_data\05_email_log.csv
echo.
echo Two CMD windows have opened for backend and frontend.
echo Close those windows to stop the servers.
pause
