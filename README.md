# NestFinder Web

Companion web application for the **NestFinder** verified accommodation platform for **Atomic North Pvt Ltd** (Billawar, Jammu and Kashmir).

## Tech Stack
- **Backend:** Python 3.11+ / Flask 3.x
- **Database & Auth:** Firebase Authentication + Google Cloud Firestore (`asia-south1`)
- **Media Storage:** Cloudinary (`khan-developers`)
- **Frontend:** Vanilla HTML5, CSS3 with CSS custom properties (Teal `#0F766E` brand), modular vanilla JS, mobile-first responsive architecture.

---

## 1. Local Development Setup (Windows / Powershell / Git Bash)

### Prerequisites
- Python 3.11+ (`python --version` or `py --version`)
- Git with Git Bash

### Step 1: Create and Activate Virtual Environment
```bash
# In Git Bash or PowerShell from the project root (d:\ANPL\web):
python -m venv .venv

# On Windows Git Bash:
source .venv/Scripts/activate

# On Windows PowerShell:
# .\.venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```bash
pip install -r requirements-dev.txt
```

### Step 3: Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Ensure your `GOOGLE_APPLICATION_CREDENTIALS` points to your Firebase Service Account JSON file (e.g. `../service-account.json`).

### Step 4: Run Development Server
```bash
flask --app wsgi run --debug --port 5000
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## 2. Running Automated Tests

Run pytest across policy unit tests and route authorization suites:
```bash
pytest -v
```

With coverage report:
```bash
pytest --cov=app tests/
```

---

## 3. Security Architecture
- **Deny by default:** All authorization logic is defined in pure functions in `app/services/policy.py`.
- **Firebase Session Cookie:** Exchanges client-side Firebase Auth ID tokens for HTTP-Only, Secure, SameSite=Lax session cookies (5-day lifespan).
- **Single Source of Truth:** On every request, user role and ban status are verified against Firestore `users/{uid}` (backed by a 60-second in-memory TTL cache).
- **Quota Watcher:** Shared Spark quota (50k reads/day) is protected by in-memory caching and tracked via the admin read counter.
