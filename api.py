import hashlib
import os
import sqlite3

from datetime import datetime, timedelta

import requests as http_requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────

DB_FILE = "users.db"
SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
OPENWEATHER_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

CONDITION_ICONS = {
    "Clear": "☀️",
    "Clouds": "☁️",
    "Rain": "🌧️",
    "Drizzle": "🌦️",
    "Thunderstorm": "⛈️",
    "Snow": "❄️",
    "Mist": "🌫️",
    "Fog": "🌫️",
    "Haze": "🌫️",
    "Dust": "🌪️",
    "Sand": "🌪️",
    "Smoke": "🌫️",
    "Tornado": "🌪️",
}

app = FastAPI(title="Weather Update API", version="1.0.0")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Schemas ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class WeatherResponse(BaseModel):
    city: str
    condition: str
    icon: str
    temperature_c: int
    feels_like_c: int
    humidity_pct: int
    wind_speed_kmh: int
    visibility_km: float


class DailyForecast(BaseModel):
    forecast_date: str
    city: str
    condition: str
    icon: str
    temperature_c: int
    feels_like_c: int
    humidity_pct: int
    wind_speed_kmh: int
    visibility_km: float


# ── Database ───────────────────────────────────────────────────────────────────

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def init_forecast_table():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weather_forecasts (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                city           TEXT NOT NULL,
                forecast_date  TEXT NOT NULL,
                condition      TEXT,
                icon           TEXT,
                temperature_c  INTEGER,
                feels_like_c   INTEGER,
                humidity_pct   INTEGER,
                wind_speed_kmh INTEGER,
                visibility_km  REAL,
                fetched_at     TEXT NOT NULL,
                UNIQUE(city, forecast_date)
            )
        """)
        conn.commit()


init_forecast_table()


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 260000
    ).hex()


def create_user(username: str, password: str):
    salt = os.urandom(16).hex()
    password_hash = hash_password(password, salt)
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                (username, password_hash, salt),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def authenticate_user(username: str, password: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT password_hash, salt FROM users WHERE username = ?", (username,)
        ).fetchone()
    return bool(row and row[0] == hash_password(password, row[1]))


# ── JWT ────────────────────────────────────────────────────────────────────────

def create_access_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest):
    """Register a new user account."""
    if not body.username.strip() or not body.password.strip():
        raise HTTPException(status_code=400, detail="Username and password cannot be empty.")
    if not create_user(body.username.strip(), body.password):
        raise HTTPException(status_code=409, detail="Username already exists.")
    return {"message": f"Account created successfully for '{body.username}'."}


@app.post("/auth/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()):
    """Authenticate and receive a JWT access token."""
    if not authenticate_user(form.username, form.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
    token = create_access_token(form.username)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/weather/{city}", response_model=WeatherResponse)
def get_weather(city: str, current_user: str = Depends(get_current_user)):
    """Get real weather for a city from OpenWeatherMap. Requires authentication."""
    if not city.strip():
        raise HTTPException(status_code=400, detail="City name cannot be empty.")

    response = http_requests.get(OPENWEATHER_URL, params={
        "q": city.strip(),
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    })

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found.")
    if response.status_code == 401:
        raise HTTPException(status_code=500, detail="Invalid OpenWeatherMap API key.")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Weather service unavailable. Try again later.")

    data = response.json()
    main_condition = data["weather"][0]["main"]

    return WeatherResponse(
        city=data["name"],
        condition=data["weather"][0]["description"].title(),
        icon=CONDITION_ICONS.get(main_condition, "🌡️"),
        temperature_c=round(data["main"]["temp"]),
        feels_like_c=round(data["main"]["feels_like"]),
        humidity_pct=data["main"]["humidity"],
        wind_speed_kmh=round(data["wind"]["speed"] * 3.6),
        visibility_km=round(data.get("visibility", 0) / 1000, 1),
    )


@app.get("/me")
def get_me(current_user: str = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return {"username": current_user}


@app.post("/weather/forecast/store", response_model=list[DailyForecast])
def store_london_forecast(current_user: str = Depends(get_current_user)):
    """Fetch 5-day forecast for London and store daily summaries in the database."""
    response = http_requests.get(OPENWEATHER_FORECAST_URL, params={
        "q": "London,UK",
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    })

    if response.status_code == 401:
        raise HTTPException(status_code=500, detail="Invalid OpenWeatherMap API key.")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Weather service unavailable. Try again later.")

    data = response.json()
    city_name = data["city"]["name"]
    fetched_at = datetime.utcnow().isoformat()

    # Group 3-hour slots by date, pick the slot closest to 12:00
    slots_by_date: dict = {}
    for slot in data["list"]:
        date = slot["dt_txt"][:10]
        time = slot["dt_txt"][11:]
        if date not in slots_by_date:
            slots_by_date[date] = slot
        else:
            current_best = slots_by_date[date]["dt_txt"][11:]
            if abs(int(time[:2]) - 12) < abs(int(current_best[:2]) - 12):
                slots_by_date[date] = slot

    saved = []
    with get_connection() as conn:
        for date, slot in sorted(slots_by_date.items()):
            main_condition = slot["weather"][0]["main"]
            row = DailyForecast(
                forecast_date=date,
                city=city_name,
                condition=slot["weather"][0]["description"].title(),
                icon=CONDITION_ICONS.get(main_condition, "🌡️"),
                temperature_c=round(slot["main"]["temp"]),
                feels_like_c=round(slot["main"]["feels_like"]),
                humidity_pct=slot["main"]["humidity"],
                wind_speed_kmh=round(slot["wind"]["speed"] * 3.6),
                visibility_km=round(slot.get("visibility", 0) / 1000, 1),
            )
            conn.execute("""
                INSERT OR REPLACE INTO weather_forecasts
                (city, forecast_date, condition, icon, temperature_c, feels_like_c,
                 humidity_pct, wind_speed_kmh, visibility_km, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (row.city, row.forecast_date, row.condition, row.icon,
                  row.temperature_c, row.feels_like_c, row.humidity_pct,
                  row.wind_speed_kmh, row.visibility_km, fetched_at))
            saved.append(row)
        conn.commit()

    return saved


@app.get("/weather/forecast/london", response_model=list[DailyForecast])
def get_london_forecast(current_user: str = Depends(get_current_user)):
    """Return stored forecast rows for London from the database."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT forecast_date, city, condition, icon, temperature_c, feels_like_c,
                   humidity_pct, wind_speed_kmh, visibility_km
            FROM weather_forecasts
            WHERE city = 'London'
            ORDER BY forecast_date
        """).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No forecast data found. Fetch it first.")

    return [
        DailyForecast(
            forecast_date=r[0], city=r[1], condition=r[2], icon=r[3],
            temperature_c=r[4], feels_like_c=r[5], humidity_pct=r[6],
            wind_speed_kmh=r[7], visibility_km=r[8],
        )
        for r in rows
    ]
