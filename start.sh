#!/bin/bash
set -e

echo "=== Insider Risk Investigation Assistant ==="
echo ""

# Backend
echo "[1/3] Setting up backend..."
cd backend
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt
echo "      Backend dependencies installed."

# Start backend in background
PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "      Backend started (PID $BACKEND_PID) → http://localhost:8000"
echo "      API Docs → http://localhost:8000/api/docs"

cd ..

# Frontend
echo "[2/3] Setting up frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
  npm install --silent
fi
echo "      Frontend dependencies installed."

echo "[3/3] Starting frontend..."
npm run dev &
FRONTEND_PID=$!
echo "      Frontend started (PID $FRONTEND_PID) → http://localhost:3000"

echo ""
echo "=== Ready ==="
echo "  App:     http://localhost:3000"
echo "  API:     http://localhost:8000/api/docs"
echo ""
echo "  Quick start — import sample data:"
echo "  1. Go to http://localhost:3000/import"
echo "  2. Select 'HR System' → upload backend/sample_data/01_hr_users.csv"
echo "  3. Select 'Microsoft Purview DLP' → upload backend/sample_data/02_purview_dlp.csv"
echo "  4. Select 'Entra ID' → upload backend/sample_data/03_entra_id_login.csv"
echo "  5. Select 'Cloud Upload' → upload backend/sample_data/04_cloud_upload.csv"
echo "  6. Select 'Email Log' → upload backend/sample_data/05_email_log.csv"
echo "  7. Go to http://localhost:3000 — Dashboard should show alerts and cases."
echo ""
echo "Press Ctrl+C to stop all services."
wait
