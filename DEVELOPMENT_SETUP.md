# TrashPort Local Development Setup Guide

This guide describes how to set up and run the TrashPort project on a local development environment.

---

## 🛠️ Prerequisites

Ensure you have the following installed on your system:
1. **Python 3.11 or 3.12**
2. **Git**
3. **uv** (Recommended - Astral's fast Python package manager)

---

## 🚀 Step-by-Step Setup

### Step 1: Switch to your branch & pull latest changes

If you already have the repository cloned, switch to your branch, pull latest references, and merge the main branch changes:
```bash
# 1. Switch to your development branch
git checkout <your-branch-name>

# 2. Pull remote changes on your branch
git pull origin <your-branch-name>

# 3. Merge or rebase the main branch to get the latest updates
git fetch origin
git merge origin/main   # Or: git rebase origin/main
```

If you are cloning the repository for the first time:
```bash
git clone <repository-url>
cd TrashPort
git checkout <your-branch-name>
```

### Step 2: Configure Environment Variables (`.env`)
Copy the `.env` file provided by the team to the project root directory:
```bash
# Place the received .env file directly in:
/TrashPort/.env
```

> [!IMPORTANT]
> The `.env` file contains secret keys such as the Google Client Secret and Groq API Key. Do not commit it to Git.

---

### Step 3: Run Setup

You can set up the environment automatically (on Windows) or manually (on all platforms).

#### Option A: Automatic Setup (Windows PowerShell)
Run the built-in setup script in PowerShell:
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
./setup_and_run.ps1
```
*This script will check for/install `uv`, synchronize virtual environment dependencies, run SQLite migrations, and prompt you to create a superuser.*

---

#### Option B: Manual Setup (Cross-Platform)

**1. Create & Activate Virtual Environment**
* **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```
* **macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

**2. Upgrade Pip & Install Dependencies**
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**3. Run Database Migrations**
We use SQLite for local development. Run the migrations to set up the database schema:
```bash
# Windows
$env:DATABASE_URL="sqlite:///db.sqlite3"
$env:DJANGO_READ_DOT_ENV_FILE="True"
$env:DJANGO_DEBUG="True"
python manage.py migrate

# macOS / Linux
export DATABASE_URL="sqlite:///db.sqlite3"
export DJANGO_READ_DOT_ENV_FILE="True"
export DJANGO_DEBUG="True"
python manage.py migrate
```

**4. Create a Django Superuser**
```bash
python manage.py createsuperuser
```

---

## 🏃 Running the Application

To support websockets (for the AI Chatbot) and standard HTTP requests, run the development server via ASGI/Daphne on port `8001`:

```bash
# Windows
$env:DATABASE_URL="sqlite:///db.sqlite3"
$env:DJANGO_READ_DOT_ENV_FILE="True"
$env:DJANGO_DEBUG="True"
python manage.py runserver 8001

# macOS / Linux
export DATABASE_URL="sqlite:///db.sqlite3"
export DJANGO_READ_DOT_ENV_FILE="True"
export DJANGO_DEBUG="True"
python manage.py runserver 8001
```

Once running, navigate to:
* **Application**: `http://127.0.0.1:8001/`
* **Django Admin**: `http://127.0.0.1:8001/admin/`

---

## 🤖 AI Chatbot Local Testing (No Firebase Setup Needed)
During local development, the chatbot's websocket connection uses a **mock Firebase token fallback**. 
* Developers can log in with any local Django user or superuser.
* The chatbot will automatically authenticate and work using Groq (`groq/compound-mini` model) without needing client-side Firebase authentication key initialization.

---

## 🧪 Running Tests
Verify your installation by running the test suite:

```bash
# Windows
$env:DATABASE_URL="sqlite:///db.sqlite3"
$env:DJANGO_READ_DOT_ENV_FILE="True"
pytest

# macOS / Linux
export DATABASE_URL="sqlite:///db.sqlite3"
export DJANGO_READ_DOT_ENV_FILE="True"
pytest
```
