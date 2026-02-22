import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")


# ── API Calls ──────────────────────────────────────────────────────────────────

def api_register(username, password):
    try:
        response = requests.post(f"{API_URL}/auth/register",
            json={"username": username, "password": password})
        return response.status_code == 201, response.json().get("message") or response.json().get("detail")
    except requests.ConnectionError:
        return False, "Cannot connect to the API server. Make sure api.py is running."


def api_login(username, password):
    try:
        response = requests.post(f"{API_URL}/auth/login",
            data={"username": username, "password": password})
        if response.status_code == 200:
            return True, response.json()["access_token"]
        return False, response.json().get("detail", "Invalid username or password.")
    except requests.ConnectionError:
        return False, "Cannot connect to the API server. Make sure api.py is running."


def api_get_weather(city, token):
    try:
        response = requests.get(f"{API_URL}/weather/{city}",
            headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to fetch weather.")
    except requests.ConnectionError:
        return False, "Cannot connect to the API server. Make sure api.py is running."


def api_store_forecast(token):
    try:
        response = requests.post(f"{API_URL}/weather/forecast/store",
            headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to fetch forecast.")
    except requests.ConnectionError:
        return False, "Cannot connect to the API server. Make sure api.py is running."


def api_get_forecast(token):
    try:
        response = requests.get(f"{API_URL}/weather/forecast/london",
            headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "No forecast data found.")
    except requests.ConnectionError:
        return False, "Cannot connect to the API server. Make sure api.py is running."


# ── Pages ──────────────────────────────────────────────────────────────────────

def show_forecast_dashboard(token):
    st.divider()
    st.subheader("🇬🇧 London 5-Day Forecast Dashboard")

    if st.button("Fetch & Store Forecast", use_container_width=True):
        success, result = api_store_forecast(token)
        if success:
            st.success(f"Stored {len(result)} days of forecast for London.")
        else:
            st.error(result)

    success, forecast = api_get_forecast(token)
    if not success:
        st.info("No forecast stored yet. Click 'Fetch & Store Forecast' to load data.")
        return

    # ── Summary metrics ──────────────────────────────────────
    temps  = [d["temperature_c"] for d in forecast]
    humids = [d["humidity_pct"]  for d in forecast]
    winds  = [d["wind_speed_kmh"] for d in forecast]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔺 Highest Temp", f"{max(temps)}°C")
    c2.metric("🔻 Lowest Temp",  f"{min(temps)}°C")
    c3.metric("💧 Avg Humidity", f"{round(sum(humids)/len(humids))}%")
    c4.metric("💨 Max Wind",     f"{max(winds)} km/h")

    st.divider()

    # ── Temperature line chart ────────────────────────────────
    st.markdown("**🌡️ Temperature Trend (°C)**")
    temp_data = {d["forecast_date"]: d["temperature_c"] for d in forecast}
    st.line_chart(temp_data)

    # ── Humidity + Wind bar charts ────────────────────────────
    col_h, col_w = st.columns(2)
    with col_h:
        st.markdown("**💧 Humidity (%)**")
        hum_data = {d["forecast_date"]: d["humidity_pct"] for d in forecast}
        st.bar_chart(hum_data)
    with col_w:
        st.markdown("**💨 Wind Speed (km/h)**")
        wind_data = {d["forecast_date"]: d["wind_speed_kmh"] for d in forecast}
        st.bar_chart(wind_data)

    st.divider()

    # ── Daily cards (one column per day) ─────────────────────
    st.markdown("**📅 Daily Summary**")
    day_cols = st.columns(len(forecast))
    for col, day in zip(day_cols, forecast):
        with col:
            st.markdown(f"**{day['forecast_date'][5:]}**")  # show MM-DD
            st.markdown(f"### {day['icon']}")
            st.markdown(f"_{day['condition']}_")
            st.metric("Temp", f"{day['temperature_c']}°C", f"{day['feels_like_c']}°C")
            st.caption(f"💧 {day['humidity_pct']}%  💨 {day['wind_speed_kmh']} km/h")
            st.caption(f"👁️ {day['visibility_km']} km")

def show_auth_page():
    st.title("🌤️ Weather Update App")
    st.subheader("Hello, Welcome to the Weather Update App")
    st.divider()

    tab_login, tab_register = st.tabs(["Sign In", "Register"])

    with tab_login:
        st.subheader("Sign In")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Sign In", use_container_width=True):
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                success, result = api_login(username, password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.token = result   # store JWT token
                    st.rerun()
                else:
                    st.error(result)

    with tab_register:
        st.subheader("Create an Account")
        new_username = st.text_input("Choose a username", key="reg_username")
        new_password = st.text_input("Choose a password", type="password", key="reg_password")
        confirm_password = st.text_input("Confirm password", type="password", key="reg_confirm")

        if st.button("Register", use_container_width=True):
            if not new_username or not new_password or not confirm_password:
                st.error("All fields are required.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                success, msg = api_register(new_username, new_password)
                if success:
                    st.success(msg + " You can now sign in.")
                else:
                    st.error(msg)


def show_weather_page():
    with st.sidebar:
        st.title("🌤️ Weather App")
        st.write(f"Logged in as **{st.session_state.username}**")
        st.divider()
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.token = ""
            st.rerun()

    st.title("🌍 Weather Update")
    st.write(f"Welcome back, **{st.session_state.username}**!")
    st.divider()

    city = st.text_input("Enter a city name", placeholder="e.g. New York, Tokyo, London")

    if st.button("Get Weather", use_container_width=True):
        if not city.strip():
            st.warning("Please enter a city name.")
        else:
            success, result = api_get_weather(city, st.session_state.token)
            if success:
                weather = result
                st.subheader(f"{weather['icon']} {weather['city']}")
                st.markdown(f"**Condition:** {weather['condition']}")
                st.divider()

                col1, col2, col3 = st.columns(3)
                col1.metric("🌡️ Temperature", f"{weather['temperature_c']}°C", f"Feels like {weather['feels_like_c']}°C")
                col2.metric("💧 Humidity", f"{weather['humidity_pct']}%")
                col3.metric("💨 Wind Speed", f"{weather['wind_speed_kmh']} km/h")

                col4, col5 = st.columns(2)
                col4.metric("👁️ Visibility", f"{weather['visibility_km']} km")
                col5.metric("📍 City", weather['city'])
            else:
                st.error(result)

    show_forecast_dashboard(st.session_state.token)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Weather Update App",
        page_icon="🌤️",
        layout="centered",
    )

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.token = ""

    if st.session_state.logged_in:
        show_weather_page()
    else:
        show_auth_page()


if __name__ == "__main__":
    main()
