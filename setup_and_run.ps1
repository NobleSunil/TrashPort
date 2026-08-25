# Setup and Run script for TrashPort on Windows
# This script sets up python dependencies using 'uv', configures local SQLite DB and runs migrations.

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  TrashPort Environment Setup & Runner  " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Check for uv installation
Write-Host "`n[1/4] Checking for uv package manager..." -ForegroundColor Cyan
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv is not installed. Installing uv from astral.sh..." -ForegroundColor Yellow
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    # Update PATH for the current session to find uv immediately
    $env:Path += ";$env:USERPROFILE\.local\bin"
} else {
    Write-Host "uv is already installed." -ForegroundColor Green
}

# 2. Sync dependencies
Write-Host "`n[2/5] Syncing virtual environment and installing dependencies..." -ForegroundColor Cyan
uv sync --frozen
Write-Host "Dependencies synchronized successfully." -ForegroundColor Green

# 3. Start Redis container via Docker
Write-Host "`n[3/5] Starting Redis container via Docker Compose..." -ForegroundColor Cyan
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker compose -f docker-compose.local.yml up -d redis
    Write-Host "Redis service started." -ForegroundColor Green
} else {
    Write-Warning "Docker command not found. Please ensure Docker Desktop is running and run 'docker compose -f docker-compose.local.yml up -d redis' manually."
}

# 4. Database setup (local SQLite database)
Write-Host "`n[4/5] Running database migrations on local SQLite..." -ForegroundColor Cyan
# Temporarily export env variables for the migration run
$env:DATABASE_URL = "sqlite:///db.sqlite3"
$env:DJANGO_READ_DOT_ENV_FILE = "True"
$env:DJANGO_DEBUG = "True"

uv run python manage.py migrate
Write-Host "Migrations completed." -ForegroundColor Green

# 5. Superuser creation
Write-Host "`n[5/5] Prompting for Django Superuser..." -ForegroundColor Cyan
Write-Host "Do you want to create a superuser account now? (y/n): " -NoNewline -ForegroundColor Yellow
$response = Read-Host
if ($response -eq 'y' -or $response -eq 'Y') {
    uv run python manage.py createsuperuser
}

# Summary and instructions
Write-Host "`n=========================================" -ForegroundColor Green
Write-Host "             SETUP COMPLETED             " -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host "To run the project with SQLite database:" -ForegroundColor Cyan
Write-Host "  1. Ensure Redis is running (started automatically above via Docker)" -ForegroundColor Gray
Write-Host "  2. Run: uv run python manage.py runserver 8001" -ForegroundColor White
Write-Host "`nTo run pytest:" -ForegroundColor Cyan
Write-Host "  `$env:DATABASE_URL='sqlite:///db.sqlite3'; `$env:DJANGO_READ_DOT_ENV_FILE='True'; uv run pytest" -ForegroundColor White
Write-Host "`nFor VS Code Debugging:" -ForegroundColor Cyan
Write-Host "  Open VS Code and press F5. Select 'Django (SQLite local)' configuration." -ForegroundColor White
Write-Host "=========================================" -ForegroundColor Green
