# 🔑 License Key Manager

A complete, self-hosted license key management system for protecting your Python projects. Generate, manage, and validate license keys through a beautiful admin dashboard and REST API.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![License](https://img.shields.io/badge/License-Private-red)

## ✨ Features

- **🔐 License Key Management** — Generate, revoke, and delete keys
- **⏰ Expiry Dates** — Set custom expiration dates on keys
- **👥 Multi-User Admin** — Add team members with role-based access (Owner/Admin/Moderator)
- **🖥️ HWID Binding** — Lock keys to specific machines
- **📊 Dashboard** — Beautiful dark-themed admin panel with live stats
- **🐍 Python Client** — Drop-in library for your customers
- **🌐 Deploy Free** — One-click deploy to Render.com
- **🔒 Secure** — JWT auth, bcrypt passwords, role-based permissions

## 🚀 Quick Start (Local Development)

### 1. Clone & Setup

```bash
git clone <your-repo-url>
cd license-api

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your settings (especially SECRET_KEY and ADMIN_PASSWORD!)
```

### 3. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Open Dashboard

Visit **http://localhost:8000** in your browser.

Login with the credentials you set in `.env` (default: `admin` / `admin123`).

### 5. API Docs

FastAPI auto-generates interactive API docs:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🌐 Deploy Online (Free)

### Option A: Railway.app (Easiest & Fastest)

1. Push your code to a **GitHub** repository.
2. Go to [Railway.app](https://railway.app) and log in with GitHub.
3. Click **New Project** → **Deploy from GitHub repo**.
4. Select your `license-api` repository.
5. Railway will automatically detect the `railway.toml` file and start building.
6. **Add a Database**: Right-click on the dashboard canvas → **New** → **Database** → **Add PostgreSQL**.
7. **Link Database**: Click your Web Service → **Variables** → **New Variable** → Select `DATABASE_URL` from the reference dropdown.
8. Add your custom variables:
   - `SECRET_KEY` = *(random string — use `python -c "import secrets; print(secrets.token_hex(32))"`)*
   - `ADMIN_USERNAME` = `admin`
   - `ADMIN_PASSWORD` = `YourSecurePassword`
9. Railway will automatically redeploy and your API will be live!

### Option B: Koyeb (Generous Free Forever Tier)

1. Push your code to a **GitHub** repository.
2. Go to [Koyeb](https://www.koyeb.com/) and create an account.
3. First, go to **Database** and create a Free PostgreSQL database. 
   - Click **Copy Connection String**.
4. Go to **Services** and click **Create Web Service**.
5. Select **GitHub** and choose your `license-api` repository.
6. In the configuration:
   - Expand **Environment Variables** and add:
     - `DATABASE_URL` = *(paste the connection string you copied)*
     - `SECRET_KEY` = *(random string)*
     - `ADMIN_USERNAME` = `admin`
     - `ADMIN_PASSWORD` = `YourSecurePassword`
   - In **Run Command**, type: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
7. Click **Deploy**!

---

## 🐍 Python Client Library

Give the `client/license_client.py` file to your customers along with their license key.

### Basic Usage

```python
from license_client import LicenseClient

# Initialize with your API URL
client = LicenseClient("https://your-app.onrender.com")

# Activate the license (validates online + binds to this machine)
if client.activate("LIC-ABCD-1234-EFGH-5678"):
    print("✅ License valid!")
    # Your app code here...
else:
    print("❌ Invalid license.")
    exit()
```

### Advanced Usage

```python
from license_client import (
    LicenseClient,
    LicenseExpiredError,
    LicenseRevokedError,
    HWIDMismatchError,
)

client = LicenseClient(
    api_url="https://your-app.onrender.com",
    hwid_lock=True,      # Bind to machine (default: True)
    cache_hours=24,       # Cache validation for offline use (default: 24)
    timeout=10,           # Request timeout in seconds (default: 10)
)

try:
    client.activate("LIC-ABCD-1234-EFGH-5678")
    print(f"✅ License active! Expires: {client.expires_at}")
except LicenseExpiredError:
    print("⏰ Your license has expired. Please renew.")
    exit()
except LicenseRevokedError:
    print("🚫 Your license has been revoked.")
    exit()
except HWIDMismatchError:
    print("🖥️ This license is registered to a different machine.")
    exit()
```

### How HWID Binding Works

When `hwid_lock=True` (default), the first time a key is validated from a machine, the machine's hardware ID is recorded. Future validations from different machines will be rejected. This prevents key sharing.

### Offline Caching

The client caches successful validations locally. If the API is unreachable, it will use the cached result for up to `cache_hours` hours. Set `cache_hours=0` to require online validation every time.

---

## 👥 User Roles

| Permission | Owner | Admin | Moderator |
|------------|:-----:|:-----:|:---------:|
| Generate keys | ✅ | ✅ | ✅ |
| View all keys | ✅ | ✅ | ✅ |
| Revoke keys | ✅ | ✅ | ❌ |
| Delete keys | ✅ | ❌ | ❌ |
| Manage users | ✅ | ❌ | ❌ |
| View stats | ✅ | ✅ | ✅ |
| Change own password | ✅ | ✅ | ✅ |

---

## 📡 API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/login` | POST | — | Login |
| `/api/auth/me` | GET | JWT | Current user info |
| `/api/auth/change-password` | PUT | JWT | Change password |
| `/api/keys/generate` | POST | JWT | Generate keys |
| `/api/keys/list` | GET | JWT | List keys (paginated) |
| `/api/keys/revoke/{key}` | PUT | JWT | Revoke a key |
| `/api/keys/delete/{key}` | DELETE | JWT | Delete a key |
| `/api/keys/update/{key}` | PUT | JWT | Update key details |
| `/api/validate` | POST | — | Validate a key (public) |
| `/api/stats` | GET | JWT | Dashboard stats |
| `/api/users/create` | POST | Owner | Create user |
| `/api/users/list` | GET | Owner | List users |
| `/api/users/delete/{id}` | DELETE | Owner | Delete user |
| `/api/users/update/{id}` | PUT | Owner | Update user |

---

## 🔒 Security Notes

- **Change the default password** immediately after first login
- **Generate a strong SECRET_KEY** for production
- All passwords are hashed with **bcrypt**
- JWT tokens expire after 24 hours (configurable)
- HWID binding prevents license key sharing
- Role-based access control protects admin functions

---

## 📁 Project Structure

```
license-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Settings
│   ├── database.py           # Database setup
│   ├── models.py             # ORM models
│   ├── schemas.py            # Request/response schemas
│   ├── auth.py               # JWT & auth utilities
│   ├── routes/
│   │   ├── auth_routes.py    # Auth endpoints
│   │   ├── key_routes.py     # Key management
│   │   ├── user_routes.py    # User management
│   │   ├── validate_routes.py # Public validation
│   │   └── stats_routes.py   # Statistics
│   └── static/
│       ├── index.html        # Admin dashboard
│       ├── style.css         # Dashboard styles
│       └── app.js            # Dashboard logic
├── client/
│   └── license_client.py    # Customer client library
├── requirements.txt
├── render.yaml              # Render deployment config
├── .env.example             # Environment template
└── README.md
```
