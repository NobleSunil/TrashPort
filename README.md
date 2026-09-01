# TrashPort - On-Demand Smart Waste Collection System

TrashPort is a Django-based on-demand smart waste collection application featuring distinct interfaces for **Citizens**, **Collectors**, and **Administrators**.

> 📄 **Detailed Status & Roadmap:** See [docs/project_summary.md](docs/project_summary.md) for a full breakdown of completed features and the future web development roadmap.

---

## 📁 Repository Folder Structure

Below is an overview of the key directories and files in this codebase, explaining what each component does:

```
TrashPort/
│
├── .vscode/
│   └── launch.json            # VS Code debugging configurations (local SQLite & Docker Postgres)
│
├── config/                    # Global Django settings and configuration
│   ├── settings/
│   │   ├── base.py            # Shared settings base
│   │   ├── local.py           # Development settings overrides
│   │   ├── production.py      # Production settings overrides
│   │   └── test.py            # Test suite execution settings overrides
│   ├── api_router.py          # DRF API ViewSet URL routing registrations
│   ├── urls.py                # Main root URL mappings and entry points
│   └── wsgi.py / asgi.py      # WSGI/ASGI application hooks
│
├── trashport/                 # Main project module containing the application logic
│   ├── users/                 # App for authentication, login/signup/profile views, models & managers
│   ├── citizens/              # App for Citizen dashboard, pickup requests, addresses, and complaints
│   ├── collectors/            # App for Collector dashboard, job claiming, and status updates
│   ├── admins/                # App for Custom Admin dashboard, stats, categories, and assignments
│   ├── static/                # Static assets (custom JavaScript, styles/CSS, images)
│   └── templates/             # Global templates (base layout, pages, and django-allauth overrides)
│
├── waste_management/          # Core data models and REST API viewsets
│   ├── models.py              # Shared database models (Address, WasteCategory, PickupRequest, Complaint)
│   ├── serializers.py         # DRF Serializers for shared waste models
│   ├── views.py               # Dynamic dispatch controllers and standard REST ViewSets
│   └── urls.py                # URL endpoints for waste management views
│
├── manage.py                  # Django administrative script
├── pyproject.toml / uv.lock   # Project dependencies and lock file managed via 'uv'
└── setup_and_run.ps1          # Automated setup PowerShell script for Windows developers
```

---

## 🛠️ Windows Quick Setup

To set up your development environment on Windows, we recommend using the local **SQLite database** to get started without needing a Docker container.

### 1. Automated Setup Script
Run the automated PowerShell script in the root directory:
```powershell
./setup_and_run.ps1
```
This script will:
1. Check if the **`uv`** package manager is installed (and install it if missing).
2. Sync all Python dependencies within a virtual environment.
3. Apply database migrations to a local `db.sqlite3` file.
4. Prompt you to create a Django Superuser account.

---

## 🚀 Running the Project

### Local Development (SQLite)
Once the setup script completes, run the development server locally:
```bash
uv run python manage.py runserver 8001
```
Navigate to `http://127.0.0.1:8001` (or `http://localhost:8001`) in your web browser.

### VS Code Debugging
Pre-configured debug targets are available in the repository. To debug in VS Code:
1. Open the project folder in VS Code.
2. Select the **Run and Debug** tab (`Ctrl+Shift+D`).
3. Choose **`Django (SQLite local)`** from the dropdown configuration list.
4. Press **`F5`** to start debugging with active breakpoints (listens on port `8001`).

---

## 🔐 Google OAuth 2.0 Configuration

TrashPort supports server-side Google OAuth 2.0 authentication for Citizens and Collectors.

### 1. Environment Variables (`.env`)
Ensure your `.env` file contains your Google OAuth Web Client credentials:
```ini
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-your-client-secret
```

### 2. Google Cloud Console Setup
To prevent `Error 400: redirect_uri_mismatch`, configure your OAuth 2.0 Web Client in [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials):

* **Authorised redirect URIs** (Required):
  * `http://localhost:8001/users/google/callback/`
  * `http://127.0.0.1:8001/users/google/callback/`
* **Authorised JavaScript origins** (Optional):
  * `http://localhost:8001`
  * `http://127.0.0.1:8001`

---

## 🐳 Running with Docker

You can run TrashPort and its PostgreSQL database inside Docker using Docker Compose.

### 1. Local Development (Docker Compose)
Build and start all local containers (Django + PostgreSQL + Redis):
```powershell
docker compose -f docker-compose.local.yml up --build
```
> Add `-d` to run in detached (background) mode:
```powershell
docker compose -f docker-compose.local.yml up -d --build
```
The app will be accessible at `http://localhost:8001`.

### 2. Common Django Commands via Docker Compose
* **Run Database Migrations:**
  ```powershell
  docker compose -f docker-compose.local.yml run --rm django python manage.py migrate
  ```
* **Create Superuser:**
  ```powershell
  docker compose -f docker-compose.local.yml run --rm django python manage.py createsuperuser
  ```
* **Run Tests (pytest):**
  ```powershell
  docker compose -f docker-compose.local.yml run --rm django pytest
  ```
* **View Logs:**
  ```powershell
  docker compose -f docker-compose.local.yml logs -f
  ```
* **Stop Containers:**
  ```powershell
  docker compose -f docker-compose.local.yml down
  ```

### 3. Using `just` Shortcuts
If you have [just](https://github.com/casey/just) installed:
```powershell
just build       # Build images
just up          # Start containers in background
just down        # Stop containers
just logs        # Follow container logs
just manage <cmd># Run manage.py commands (e.g. just manage migrate)
just pytest      # Run pytest test suite
```

### 4. Running a Standalone Docker Image (`docker run`)
If you want to build and run the Django image directly:
```powershell
# 1. Build the image
docker build -t trashport_django -f compose/local/django/Dockerfile .

# 2. Run the container
docker run -p 8001:8001 --env-file .envs/.local/.django trashport_django
```

### 5. Production Environment
To run the full production stack (Django, PostgreSQL, Redis, Traefik, Nginx):
```powershell
docker compose -f docker-compose.production.yml up --build -d
```

---

## 🐳 Running with Docker

You can run TrashPort and its PostgreSQL database inside Docker using Docker Compose.

### 1. Local Development (Docker Compose)
Build and start all local containers (Django + PostgreSQL):
```powershell
docker compose -f docker-compose.local.yml up --build
```
> Add `-d` to run in detached (background) mode:
```powershell
docker compose -f docker-compose.local.yml up -d --build
```
The app will be accessible at `http://localhost:8000`.

### 2. Common Django Commands via Docker Compose
* **Run Database Migrations:**
  ```powershell
  docker compose -f docker-compose.local.yml run --rm django python manage.py migrate
  ```
* **Create Superuser:**
  ```powershell
  docker compose -f docker-compose.local.yml run --rm django python manage.py createsuperuser
  ```
* **Run Tests (pytest):**
  ```powershell
  docker compose -f docker-compose.local.yml run --rm django pytest
  ```
* **View Logs:**
  ```powershell
  docker compose -f docker-compose.local.yml logs -f
  ```
* **Stop Containers:**
  ```powershell
  docker compose -f docker-compose.local.yml down
  ```

### 3. Using `just` Shortcuts
If you have [just](https://github.com/casey/just) installed:
```powershell
just build       # Build images
just up          # Start containers in background
just down        # Stop containers
just logs        # Follow container logs
just manage <cmd># Run manage.py commands (e.g. just manage migrate)
just pytest      # Run pytest test suite
```

### 4. Running a Standalone Docker Image (`docker run`)
If you want to build and run the Django image directly:
```powershell
# 1. Build the image
docker build -t trashport_django -f compose/local/django/Dockerfile .

# 2. Run the container
docker run -p 8000:8000 --env-file .envs/.local/.django trashport_django
```

### 5. Production Environment
To run the full production stack (Django, PostgreSQL, Redis, Traefik, Nginx):
```powershell
docker compose -f docker-compose.production.yml up --build -d
```

---

## 🧪 Testing

To run the entire test suite locally using the SQLite database:
```powershell
$env:DATABASE_URL="sqlite:///db.sqlite3"; $env:DJANGO_READ_DOT_ENV_FILE="True"; uv run pytest
```

