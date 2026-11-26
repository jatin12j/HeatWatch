# 🔥 HeatWatch: Extreme Heatwave Early Warning and Human Thermal Stress Index System

**Theme:** Disaster Management

---

## 📖 Project Overview

HeatWatch is a web application that fetches weather forecast data from a free API
(Open-Meteo), computes human thermal stress indices (Heat Index and Wet-Bulb
Temperature), classifies risk levels, detects upcoming heatwaves, sends alerts
to subscribers, and displays everything on an interactive dashboard with a
color-coded map and charts.

Built with **Django 5.x** (Python), it demonstrates core web development concepts
including Models, Views, Templates, Forms, URL routing, ORM queries, Admin
customization, Authentication, and Testing.

---

## ✨ Features

| Feature | Description |
| --- | --- |
| **Interactive Map** | Leaflet.js map with color-coded markers (green→red) per city |
| **7-Day Forecast** | Hourly temperature, heat index, wet-bulb data from Open-Meteo |
| **Heat Index** | NWS Rothfusz regression with Steadman fallback |
| **Wet-Bulb Temperature** | Stull (2011) approximation |
| **Risk Classification** | 5 levels: Normal, Caution, Extreme Caution, Danger, Extreme Danger |
| **Vulnerable Groups** | 3°C stricter thresholds for elderly, children, outdoor workers |
| **Heatwave Detection** | Automatic detection of 3+ consecutive danger days |
| **Email Alerts** | Console-based notifications to subscribed users |
| **Heat Calculator** | Interactive form to compute risk from any temp + humidity |
| **Cooling Centers** | Map layer showing shelter locations |
| **CSV Export** | Download forecast data per city |
| **JSON API** | Simple API endpoints for locations and forecasts |
| **Safety Tips** | Comprehensive heat safety guidelines by risk level |
| **Admin Panel** | Full Django admin for all models |
| **User Auth** | Signup, Login, Logout with group selection |
| **Subscriptions** | Users subscribe to cities and choose alert levels |

---

## 📸 Screenshots

<!-- Add your screenshots here -->
*Dashboard with interactive map, calculator page, location detail with chart*

---

## 🛠️ Tech Stack

| Component | Technology |
| --- | --- |
| Backend | Python 3.11+, Django 5.x |
| Database | SQLite (zero setup) |
| Weather API | Open-Meteo (free, no API key) |
| HTTP Client | `requests` library |
| Maps | Leaflet.js + OpenStreetMap |
| Charts | Chart.js |
| UI Framework | Bootstrap 5 (CDN) |
| Email | Django Console Email Backend |
| Scheduling | Custom management commands |

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.11 or higher
- pip (Python package manager)

### Step-by-step

```bash
# 1. Clone or download the project
cd heatwave_project

# 2. Create a virtual environment
python -m venv venv

# 3. Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run database migrations
python manage.py migrate

# 6. Seed the database with Indian cities and a demo user
python manage.py seed_locations

# 7. Fetch weather forecast data (requires internet)
python manage.py fetch_forecasts

# 8. (Optional) Create a superuser for admin access
python manage.py createsuperuser

# 9. Start the development server
python manage.py runserver

# 10. Open in browser
# http://127.0.0.1:8000/
```

### Demo User
- **Username:** `demo`
- **Password:** `demo1234`

### Admin Panel
- URL: http://127.0.0.1:8000/admin/
- Use the superuser credentials you created in step 8

---

## 📡 Fetching Forecast Data

```bash
# Fetch for all locations (real live Open-Meteo forecasts)
python manage.py fetch_forecasts

# Fetch for a specific city
python manage.py fetch_forecasts --location Delhi
```

### ☀️ Heatwave Viva Demonstration Simulator

During winter or mild seasons, temperatures are low (no heatwaves). For college viva/evaluations, use the simulation command:

```bash
# Inject realistic summer heatwave scenario (42°C - 46°C) for Delhi, Jaipur, Nagpur, Ahmedabad
python manage.py simulate_heatwave

# Restore real-time live winter forecasts anytime
python manage.py simulate_heatwave --reset
```

### Scheduling with Cron (Linux/macOS)

Run every 6 hours:
```bash
crontab -e
# Add this line:
0 */6 * * * cd /path/to/heatwave_project && /path/to/venv/bin/python manage.py fetch_forecasts
```

### Scheduling with Task Scheduler (Windows)

```cmd
schtasks /create /sc hourly /mo 6 /tn "HeatWatch Fetch" /tr "cd C:\path\to\heatwave_project && C:\path\to\venv\Scripts\python.exe manage.py fetch_forecasts"
```

---

## 🧪 Running Tests

```bash
python manage.py test warning
```

Tests cover:
- Temperature conversions
- Heat index calculation (NWS algorithm)
- Wet-bulb temperature (Stull formula)
- Risk classification (all levels + vulnerable groups)
- Heatwave detection (multiple scenarios)
- Alert creation (with and without duplicates)
- All view responses (status codes)
- Forecast fetching (mocked API — no real network calls)

---

## 🌡️ Heat Index Formula

The **Heat Index (HI)** is computed using the NWS Rothfusz regression:

1. **Steadman formula** (simple estimate):
   `HI = 0.5 × (T + 61.0 + (T − 68.0) × 1.2 + RH × 0.094)`

2. If the average of HI and T ≥ 80°F, apply the **full Rothfusz regression**:
   `HI = −42.379 + 2.049T + 10.143RH − 0.225T·RH − 0.007T² − 0.055RH² + 0.001T²·RH + 0.0009T·RH² − 0.000002T²·RH²`

3. **Low-humidity adjustment** (RH < 13%, 80 ≤ T ≤ 112°F)
4. **High-humidity adjustment** (RH > 85%, 80 ≤ T ≤ 87°F)

The **Wet-Bulb Temperature** uses the Stull (2011) approximation, which estimates
the lowest temperature reachable by evaporative cooling.

### Risk Thresholds

| Heat Index (°C) | Risk Level | Color |
| --- | --- | --- |
| < 27 | Normal | 🟢 Green |
| 27 – 32 | Caution | 🟡 Yellow |
| 32 – 39 | Extreme Caution | 🟠 Orange |
| 39 – 51 | Danger | 🔴 Red |
| ≥ 51 | Extreme Danger | ⚫ Dark Red |

> **Vulnerable groups** (Elderly, Children, Outdoor Workers) have all thresholds
> lowered by 3°C for earlier warnings.

---

## 📂 Project Structure

```
heatwave_project/
├── manage.py
├── requirements.txt
├── README.md
├── heatwave_project/
│   ├── __init__.py
│   ├── settings.py          # Django settings + HeatWatch config
│   ├── urls.py               # Project URL routing
│   ├── wsgi.py
│   └── asgi.py
└── warning/
    ├── __init__.py
    ├── apps.py
    ├── models.py              # 6 models (Location, ForecastRecord, Alert, etc.)
    ├── views.py               # All views (dashboard, calculator, API, etc.)
    ├── urls.py                # App URL patterns
    ├── admin.py               # Admin configuration for all models
    ├── forms.py               # Calculator, Signup, Subscription, Filter forms
    ├── tests.py               # Comprehensive test suite
    ├── services/
    │   ├── __init__.py
    │   ├── indices.py         # Heat Index, Wet-Bulb, Risk Classification
    │   ├── forecast.py        # Open-Meteo API fetcher
    │   └── alerts.py          # Heatwave detection & notifications
    ├── management/
    │   └── commands/
    │       ├── seed_locations.py    # Seeds 12 Indian cities + shelters
    │       └── fetch_forecasts.py   # Fetches data + generates alerts
    ├── templatetags/
    │   └── warning_tags.py    # Custom template filters
    └── templates/
        └── warning/
            ├── base.html              # Base template with navbar + footer
            ├── dashboard.html         # Map + summary + alerts
            ├── location_detail.html   # Charts + daily table + subscribe
            ├── calculator.html        # Heat risk calculator form
            ├── alerts_list.html       # Paginated alert history
            ├── subscriptions.html     # Manage subscriptions
            ├── safety.html            # Safety guidelines
            ├── signup.html            # User registration
            └── login.html             # Login page
```

---

## 📄 License

MIT License — Free to use for educational purposes.

---

## 👨‍💻 Developed As

A college project demonstrating Django web development for the
**Disaster Management** theme. All syllabus units (I–VI) are covered:
project structure, views & URLs, templates & DTL, forms & CSRF,
models & ORM, and authentication & sessions.
