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

## 🔑 Secrets & Environment Configuration Guide

TrashPort uses a single root `.env` file and a `serviceAccountKey.json` credentials file for third-party integrations. For security, **real secrets, private keys, and API tokens are never committed to GitHub**.

### 1. Create Your Local `.env` File
Copy the provided dummy template `.env.example` into a new `.env` file:
```bash
cp .env.example .env
```
*(On Windows PowerShell: `Copy-Item .env.example .env`)*

### 2. Configure Your Secrets & API Credentials

| Secret / Environment Variable | Purpose | How to Obtain / Configure |
| :--- | :--- | :--- |
| **`DATABASE_URL`** | PostgreSQL DB connection | Defaults to `postgres://debug:debug@127.0.0.1:5432/trashport` when running local Postgres container. (Or `sqlite:///db.sqlite3` for local SQLite development). |
| **`REDIS_URL`** | Caching & WebSocket channels | Defaults to `redis://127.0.0.1:6379/0` when running local Redis container. |
| **`GOOGLE_OAUTH_CLIENT_ID`<br>`GOOGLE_OAUTH_CLIENT_SECRET`** | Google One-Click Sign-In | 1. Go to [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials).<br>2. Create an **OAuth 2.0 Web Client ID**.<br>3. Add Authorized Redirect URI: `http://localhost:8001/users/google/callback/`.<br>4. Paste your Client ID and Secret into `.env`. |
| **`DJANGO_FIREBASE_CREDENTIALS`<br>`DJANGO_FIREBASE_WEB_API_KEY`** | Firebase Authentication & Admin SDK | 1. Open [Firebase Console](https://console.firebase.google.com/) > **Project Settings** > **Service accounts** tab.<br>2. Click **Generate new private key** and download the `.json` file.<br>3. Save the file as `serviceAccountKey.json` in your project root *(see `serviceAccountKey.example.json` for structure)*.<br>4. Copy the Web API Key from the **General** tab into `DJANGO_FIREBASE_WEB_API_KEY`. |
| **`GROQ_API_KEY`** | AI Assistant / Chatbot | 1. Sign in to [Groq Cloud Console](https://console.groq.com/keys).<br>2. Generate a new API key (`gsk_...`).<br>3. Paste it as `GROQ_API_KEY=gsk_...` in `.env`. |
| **`DJANGO_EMAIL_HOST_USER`<br>`DJANGO_EMAIL_HOST_PASSWORD`** | Email & Password Reset (SMTP) | 1. Go to your Google Account > **Security**.<br>2. Enable **2-Step Verification**.<br>3. Generate an **App Password** (16 characters).<br>4. Set `DJANGO_EMAIL_HOST_USER=your_email@gmail.com` and `DJANGO_EMAIL_HOST_PASSWORD=xxxx-xxxx-xxxx-xxxx`. |
| **`STRIPE_PUBLIC_KEY`<br>`STRIPE_SECRET_KEY`<br>`STRIPE_WEBHOOK_SECRET`** | Online Payments | Obtain test API keys (`pk_test_...`, `sk_test_...`) from [Stripe Dashboard](https://dashboard.stripe.com/test/apikeys). |

> 🛡️ **Security Notice:**
> Both `.env` and `serviceAccountKey.json` (as well as `*.key` and `*.pem`) are strictly listed in `.gitignore`. **Never commit actual API keys, passwords, or private key JSON files to version control.**

---

## 🔐 Google Cloud Console Setup

To prevent `Error 400: redirect_uri_mismatch` during Google Login, ensure your OAuth 2.0 Web Client in [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials) has:

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


---

## 🪪 Aadhaar Verification (Simulated — Collector Signup Only)

> **⚠ DEMO / ACADEMIC PROJECT** — This is a simulated Aadhaar authentication flow implemented for a college/university project. It does **not** connect to UIDAI or any live government authentication system.

### Why this is a Simulated Flow

Real Aadhaar authentication for private applications requires:

1. **AUA/KUA License** — Under the [Aadhaar Act 2016, Section 4](https://uidai.gov.in/en/ecosystem/authentication-devices-documents/developers-page.html), only licensed Authentication User Agencies (AUAs) or KYC User Agencies (KUAs) may initiate Aadhaar authentication. Private developers and students cannot obtain this license without institutional approval from UIDAI.

2. **Puttaswamy Judgment (2018)** — In *Justice K.S. Puttaswamy v. Union of India*, the Supreme Court of India held that mandatory Aadhaar linkage for private entities is unconstitutional. Voluntary use for government-benefit schemes remains permissible, but blanket private entity authentication was struck down.

3. **UIDAI Developer Sandbox** — UIDAI provides a sandbox environment, but access requires institutional credentials and approval — not available for individual college projects.

### What This Implementation Does

| Feature | Implementation |
|---|---|
| Aadhaar format validation | 12 digits, numeric, Verhoeff checksum |
| OTP generation | 6-digit random OTP, logged to console |
| OTP delivery | `[DEMO MODE - OTP: xxxxxx]` in Django logs |
| OTP expiry | 5 minutes |
| Rate limiting | Max 3 attempts per OTP session |
| Raw Aadhaar storage | ❌ **Never stored** |
| Stored data | SHA-256 hash + masked display (`XXXX XXXX 9012`) |
| Scope | Collector role only — Admin/Citizen flows untouched |
| Config flag | `AADHAAR_MODE=demo` in `.env` |

### Data Protection Measures

- **No plaintext storage**: The raw 12-digit Aadhaar number is hashed with SHA-256 immediately after input and never written to the database.
- **Masked display**: Only `XXXX XXXX <last4>` is shown to users and stored — enough for recognition without exposing sensitive digits.
- **Hashed OTP**: OTPs are also stored as SHA-256 hashes; the plaintext OTP is discarded after generation and comparison.
- **Single-use OTP**: After successful verification, `otp_hash`, `otp_expires_at`, and `otp_attempts` are cleared — the OTP cannot be reused.
- **Consent notice**: Users must explicitly consent before their Aadhaar number is accepted.
- **Collector-scoped model**: `CollectorAadhaarProfile` is a separate table from `users.User`, so adding `aadhaar_verified` to a Collector doesn't affect Admin or Citizen records.

### Demo Test Aadhaar Numbers

The following **fictional** numbers are provided for testing. They satisfy the Verhoeff checksum (same algorithm real Aadhaar numbers use), but are **not registered with UIDAI** and **do not belong to any person**.

| Number | Masked |
|---|---|
| `304332181964` | XXXX XXXX 1964 |
| `201338908389` | XXXX XXXX 8389 |
| `837940265421` | XXXX XXXX 5421 |
| `551161559403` | XXXX XXXX 9403 |
| `981618495938` | XXXX XXXX 5938 |

### How to Upgrade to a Real Licensed Provider

To move to production Aadhaar authentication with a licensed provider (e.g., **Signzy**, **Surepass**, **Digio**), replace the mock logic in [`trashport/collectors/aadhaar_service.py`](trashport/collectors/aadhaar_service.py):

1. Replace `generate_demo_otp()` with an API call to the licensed provider's OTP initiation endpoint.
2. Replace the `verhoeff_validate()` pre-check (still useful as a client-side guard) with the provider's own validation.
3. Replace the local OTP hash comparison in `AadhaarVerifyView` with a call to the provider's verification endpoint.
4. Store provider-issued `txn_id` / `auth_token` in `CollectorAadhaarProfile` instead of the local OTP hash.
5. Keep all hashing and masking logic — the privacy measures are provider-agnostic.
6. Remove `AADHAAR_MODE=demo` from `.env` and add provider API keys as environment variables.

### API Endpoints (Collector-Scoped)

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/collectors/aadhaar/` | Aadhaar verification page (HTML) |
| `POST` | `/api/collectors/aadhaar/initiate/` | Validate number, generate OTP |
| `POST` | `/api/collectors/aadhaar/verify/` | Verify OTP, mark `aadhaar_verified=True` |

All endpoints require `Login` and reject non-Collector roles with HTTP 403.
