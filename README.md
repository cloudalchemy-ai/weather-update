# 🌤️ Weather Update App

A full-stack weather dashboard built with **FastAPI** (backend) and **Streamlit** (frontend).
Features real-time weather lookup and a 5-day London forecast dashboard with trend charts.

---

## Features

- User registration & JWT-based login
- Current weather lookup for any city (via OpenWeatherMap API)
- London 5-day forecast with:
  - Summary metrics (high, low, avg humidity, max wind)
  - Temperature trend line chart
  - Humidity & wind speed bar charts
  - Daily card breakdown

---

## Project Structure

```
.
├── api.py            # FastAPI backend (auth, weather endpoints)
├── app.py            # Streamlit frontend
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variable template
└── README.md
```

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/<your-username>/weather-app.git
cd weather-app
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
```
Edit `.env` and fill in your values:
```
OPENWEATHER_API_KEY=your_openweathermap_api_key
SECRET_KEY=your_strong_random_secret_key
```

---

## Running the App

Open **two terminals**:

**Terminal 1 — Start the API:**
```bash
uvicorn api:app --reload
```

**Terminal 2 — Start the frontend:**
```bash
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Environment Variables

| Variable | Description |
|---|---|
| `OPENWEATHER_API_KEY` | API key from [openweathermap.org](https://openweathermap.org) |
| `SECRET_KEY` | Secret used to sign JWT tokens |
