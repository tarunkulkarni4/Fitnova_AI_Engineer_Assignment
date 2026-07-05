# FitNova Sales Intelligence Platform Startup Script
# This script configures the local environment, runs database migrations, seeds initial demo data, and starts the services.

$ErrorActionPreference = "Stop"

Write-Host "=================================================="
Write-Host " Starting FitNova Sales Intelligence Platform Setup "
Write-Host "=================================================="

# 1. Verify required tools are available
Write-Host "Checking system prerequisites..."

if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is required but not found in your PATH. Please install Python 3.11+."
    Exit 1
}

if (-not (Get-Command "node" -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js is required but not found in your PATH. Please install Node.js (v18+)."
    Exit 1
}

if (-not (Get-Command "npm" -ErrorAction SilentlyContinue)) {
    Write-Error "npm is required but not found in your PATH."
    Exit 1
}

Write-Host "System prerequisites verified successfully."

# 2. Setup backend virtual environment if missing
if (-not (Test-Path "backend\venv")) {
    Write-Host "Python virtual environment not found. Creating virtual environment in 'backend/venv'..."
    python -m venv backend\venv
}

# 3. Install backend dependencies if needed
Write-Host "Installing/verifying backend dependencies..."
& backend\venv\Scripts\pip.exe install -r backend\requirements.txt

# 4. Install frontend dependencies if needed
Write-Host "Installing/verifying frontend dependencies..."
Push-Location frontend
npm install
Pop-Location

# 5. Database setup & migrations
Write-Host "Applying database migrations..."
Push-Location backend
try {
    # Run alembic migrations
    & .\venv\Scripts\alembic.exe upgrade head
    Write-Host "Migrations applied successfully."
} catch {
    Write-Warning "Failed to apply database migrations automatically. Please ensure PostgreSQL is running and your .env configuration is correct."
    Write-Warning "Error Details: $_"
    Pop-Location
    Exit 1
}

# 6. Seed required demo data (Idempotent check inside python script)
Write-Host "Seeding demo data (idempotent)..."
try {
    & .\venv\Scripts\python.exe seed.py
} catch {
    Write-Warning "Database seeding failed. Please check backend database connection."
    Write-Warning "Error Details: $_"
    Pop-Location
    Exit 1
}
Pop-Location

# 7. Start the backend & frontend in parallel console windows
Write-Host "Launching services in separate terminal windows..."

# Launch Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\python.exe -m uvicorn app.main:app --reload"

# Launch Frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

# 8. Print details
Write-Host "`n=================================================="
Write-Host "   FitNova Sales Intelligence Platform Started!   "
Write-Host "=================================================="
Write-Host " Backend API Server:     http://localhost:8000"
Write-Host " Frontend Application:   http://localhost:5173"
Write-Host "=================================================="
Write-Host "Note: If port 5173 is already in use, check the newly opened frontend terminal for the allocated port (e.g., http://localhost:5174)."
Write-Host "Keep the newly opened console windows running to keep the application active."
