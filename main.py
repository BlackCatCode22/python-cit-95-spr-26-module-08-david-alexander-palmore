from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="David Palmore Weather Command Center")

HEADERS = {
    "User-Agent": "FCC-Student-App",
    "Accept": "application/geo+json, application/json",
}

NWS_CITIES = {
    "Fresno, CA": {"lat": 36.7378, "lon": -119.7871, "tagline": "Central Valley weather feed"},
    "New York, NY": {"lat": 40.7128, "lon": -74.0060, "tagline": "East Coast weather feed"},
}

LONDON_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=51.5072&longitude=-0.1276"
    "&current_weather=true"
)


def fahrenheit_to_celsius(temp_f: Optional[float]) -> Optional[float]:
    if temp_f is None:
        return None
    return round((float(temp_f) - 32) * 5 / 9, 1)


def celsius_to_fahrenheit(temp_c: Optional[float]) -> Optional[float]:
    if temp_c is None:
        return None
    return round((float(temp_c) * 9 / 5) + 32)


def get_json(url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    response = requests.get(url, headers=headers, timeout=12)
    response.raise_for_status()
    return response.json()


def get_icon_for_condition(condition: str) -> str:
    condition_lower = condition.lower()

    if "thunder" in condition_lower or "storm" in condition_lower:
        return "⛈️"
    if "snow" in condition_lower or "sleet" in condition_lower:
        return "❄️"
    if "rain" in condition_lower or "showers" in condition_lower or "drizzle" in condition_lower:
        return "🌧️"
    if "fog" in condition_lower or "haze" in condition_lower or "smoke" in condition_lower:
        return "🌫️"
    if "cloud" in condition_lower or "overcast" in condition_lower:
        if "partly" in condition_lower or "mostly sunny" in condition_lower:
            return "⛅"
        return "☁️"
    if "sun" in condition_lower or "clear" in condition_lower:
        return "☀️"

    return "🌡️"


def open_meteo_code_to_condition(code: int) -> str:
    weather_codes = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        56: "Light freezing drizzle", 57: "Dense freezing drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        66: "Light freezing rain", 67: "Heavy freezing rain",
        71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
        85: "Slight snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
    }
    return weather_codes.get(code, f"Weather code {code}")


def normalize_temperature(temp: Optional[float], unit: str) -> Dict[str, Optional[float]]:
    if temp is None:
        return {"f": None, "c": None}

    if unit.upper() == "F":
        return {"f": round(float(temp)), "c": fahrenheit_to_celsius(temp)}

    if unit.upper() == "C":
        return {"f": celsius_to_fahrenheit(temp), "c": round(float(temp), 1)}

    return {"f": None, "c": None}


def get_nws_weather(city: str, lat: float, lon: float, tagline: str) -> Dict[str, Any]:
    point_url = f"https://api.weather.gov/points/{lat},{lon}"
    point_data = get_json(point_url, HEADERS)

    forecast_url = point_data["properties"]["forecast"]
    forecast_data = get_json(forecast_url, HEADERS)

    period = forecast_data["properties"]["periods"][0]
    condition = period.get("shortForecast", "Unavailable")
    normalized = normalize_temperature(period.get("temperature"), period.get("temperatureUnit", "F"))

    return {
        "city": city,
        "source": "National Weather Service",
        "tagline": tagline,
        "temp_f": normalized["f"],
        "temp_c": normalized["c"],
        "condition": condition,
        "icon": get_icon_for_condition(condition),
        "wind": f"{period.get('windSpeed', 'Unknown')} {period.get('windDirection', '')}".strip(),
        "details": period.get("detailedForecast", "No detailed forecast available."),
    }


def get_london_weather() -> Dict[str, Any]:
    data = get_json(LONDON_URL)
    current = data["current_weather"]
    weather_code = int(current.get("weathercode", -1))
    condition = open_meteo_code_to_condition(weather_code)
    normalized = normalize_temperature(current.get("temperature"), "C")

    return {
        "city": "London, UK",
        "source": "Open-Meteo",
        "tagline": "International bonus weather feed",
        "temp_f": normalized["f"],
        "temp_c": normalized["c"],
        "condition": condition,
        "icon": get_icon_for_condition(condition),
        "wind": f"{current.get('windspeed', 'Unknown')} km/h",
        "details": "Bonus city powered by Open-Meteo. This API does not require an API key.",
    }


def load_weather_data() -> Dict[str, Any]:
    cities = []
    errors = []

    for city, info in NWS_CITIES.items():
        try:
            cities.append(get_nws_weather(city, info["lat"], info["lon"], info["tagline"]))
        except Exception as error:
            errors.append(f"{city}: {error}")

    try:
        cities.append(get_london_weather())
    except Exception as error:
        errors.append(f"London, UK: {error}")

    return {
        "updated": datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
        "cities": cities,
        "errors": errors,
    }


def city_card(city: Dict[str, Any]) -> str:
    temp_f = "" if city["temp_f"] is None else city["temp_f"]
    temp_c = "" if city["temp_c"] is None else city["temp_c"]

    return f"""
    <article class="card">
        <div class="card-label">
            <span>{city['tagline']}</span>
            <span>{city['source']}</span>
        </div>

        <div class="city-row">
            <div>
                <h2>{city['city']}</h2>
                <p class="condition">{city['condition']}</p>
            </div>
            <div class="weather-icon" aria-label="{city['condition']}">{city['icon']}</div>
        </div>

        <div class="temperature" data-f="{temp_f}" data-c="{temp_c}">
            <span class="temp-value">{temp_f}</span><span class="temp-unit">°F</span>
        </div>

        <p class="wind">Wind: {city['wind']}</p>
        <p class="details">{city['details']}</p>
    </article>
    """


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    data = load_weather_data()
    cards = "".join(city_card(city) for city in data["cities"])

    error_html = ""
    if data["errors"]:
        error_items = "".join(f"<li>{error}</li>" for error in data["errors"])
        error_html = f"""
        <section class="error-box">
            <strong>Some feeds could not load:</strong>
            <ul>{error_items}</ul>
        </section>
        """

    return f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>David Palmore | Weather Command Center</title>
        <style>
            :root {{
                --card: rgba(15, 23, 42, 0.86);
                --border: rgba(148, 163, 184, 0.22);
                --text: #f8fafc;
                --muted: #cbd5e1;
                --blue: #38bdf8;
                --green: #22c55e;
            }}

            * {{ box-sizing: border-box; }}

            body {{
                margin: 0;
                min-height: 100vh;
                font-family: Arial, Helvetica, sans-serif;
                color: var(--text);
                background:
                    radial-gradient(circle at top left, rgba(56, 189, 248, 0.25), transparent 34rem),
                    radial-gradient(circle at bottom right, rgba(251, 146, 60, 0.22), transparent 32rem),
                    linear-gradient(135deg, #020617, #0f172a 55%, #111827);
            }}

            .page {{
                width: min(1180px, calc(100% - 32px));
                margin: 0 auto;
                padding: 42px 0;
            }}

            .hero, .card, .error-box, .footer {{
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 28px;
                box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
                backdrop-filter: blur(18px);
            }}

            .hero {{
                padding: 34px;
                margin-bottom: 24px;
                display: grid;
                grid-template-columns: 1fr auto;
                gap: 24px;
                align-items: center;
            }}

            .eyebrow {{
                color: var(--blue);
                letter-spacing: 0.18em;
                text-transform: uppercase;
                font-size: 0.8rem;
                font-weight: 800;
            }}

            h1 {{
                font-size: clamp(2.6rem, 7vw, 5.4rem);
                line-height: 0.92;
                margin: 16px 0;
            }}

            .hero p {{
                color: var(--muted);
                max-width: 760px;
                font-size: 1.08rem;
                line-height: 1.7;
            }}

            .unit-panel {{
                border: 1px solid var(--border);
                background: rgba(15, 23, 42, 0.72);
                border-radius: 22px;
                padding: 18px;
                min-width: 220px;
            }}

            .unit-title {{
                color: var(--muted);
                font-size: 0.72rem;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                margin-bottom: 12px;
            }}

            .unit-buttons {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 8px;
            }}

            .unit-button {{
                border: 1px solid var(--border);
                border-radius: 14px;
                padding: 12px;
                cursor: pointer;
                color: var(--text);
                background: rgba(30, 41, 59, 0.9);
                font-size: 1.1rem;
                font-weight: 900;
            }}

            .unit-button.active {{
                background: linear-gradient(135deg, #2563eb, #38bdf8);
                box-shadow: 0 0 28px rgba(56, 189, 248, 0.28);
            }}

            .grid {{
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 20px;
            }}

            .card {{
                padding: 24px;
                overflow: hidden;
                position: relative;
            }}

            .card::before {{
                content: "";
                position: absolute;
                top: -80px;
                right: -80px;
                width: 180px;
                height: 180px;
                background: radial-gradient(circle, rgba(56, 189, 248, 0.28), transparent 70%);
            }}

            .card-label {{
                display: flex;
                justify-content: space-between;
                gap: 12px;
                color: var(--muted);
                font-size: 0.72rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 28px;
                position: relative;
                z-index: 1;
            }}

            .city-row {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 18px;
                position: relative;
                z-index: 1;
            }}

            h2 {{
                font-size: 1.7rem;
                margin: 0;
            }}

            .condition {{
                color: var(--muted);
                margin-top: 8px;
            }}

            .weather-icon {{
                width: 96px;
                height: 96px;
                border-radius: 26px;
                display: grid;
                place-items: center;
                font-size: 4rem;
                background:
                    radial-gradient(circle at 40% 35%, rgba(255, 255, 255, 0.18), transparent 44%),
                    rgba(2, 6, 23, 0.35);
                filter: drop-shadow(0 16px 18px rgba(0, 0, 0, 0.32));
            }}

            .temperature {{
                font-size: 4rem;
                font-weight: 900;
                letter-spacing: -0.08em;
                margin-top: 24px;
                position: relative;
                z-index: 1;
            }}

            .temp-unit {{ letter-spacing: -0.03em; }}

            .wind {{
                color: var(--blue);
                font-weight: 700;
            }}

            .details {{
                color: var(--muted);
                line-height: 1.65;
            }}

            .footer {{
                color: var(--muted);
                display: flex;
                justify-content: space-between;
                gap: 16px;
                margin-top: 24px;
                padding: 18px 24px;
                font-size: 0.95rem;
            }}

            .error-box {{
                padding: 18px 22px;
                border-color: rgba(248, 113, 113, 0.45);
                margin-bottom: 20px;
            }}

            code {{ color: var(--green); }}

            @media (max-width: 900px) {{
                .hero {{ grid-template-columns: 1fr; }}
                .grid {{ grid-template-columns: 1fr; }}
                .footer {{ flex-direction: column; }}
            }}
        </style>
    </head>
    <body>
        <main class="page">
            <section class="hero">
                <div>
                    <div class="eyebrow">CIT-95 Module 8 • FastAPI + JSON APIs</div>
                    <h1>Weather Command Center</h1>
                    <p>
                        Built by David Palmore. This FastAPI dashboard fetches live JSON weather data,
                        parses it into Python dictionaries, and displays Fresno, New York, and London
                        in a polished web interface.
                    </p>
                </div>

                <aside class="unit-panel">
                    <div class="unit-title">Temperature Unit</div>
                    <div class="unit-buttons">
                        <button class="unit-button active" type="button" data-unit="f">°F</button>
                        <button class="unit-button" type="button" data-unit="c">°C</button>
                    </div>
                </aside>
            </section>

            {error_html}

            <section class="grid">
                {cards}
            </section>

            <section class="footer">
                <span>Last updated: {data['updated']}</span>
                <span>API endpoint: <code>/api/weather</code> | Raw NWS JSON: <code>/raw-json</code></span>
            </section>
        </main>

        <script>
            function setUnit(unit) {{
                document.querySelectorAll(".unit-button").forEach((button) => {{
                    button.classList.toggle("active", button.dataset.unit === unit);
                }});

                document.querySelectorAll(".temperature").forEach((tempBox) => {{
                    const value = tempBox.dataset[unit];
                    const valueSpan = tempBox.querySelector(".temp-value");
                    const unitSpan = tempBox.querySelector(".temp-unit");

                    valueSpan.textContent = value;
                    unitSpan.textContent = unit === "f" ? "°F" : "°C";
                }});

                localStorage.setItem("weatherUnit", unit);
            }}

            document.querySelectorAll(".unit-button").forEach((button) => {{
                button.addEventListener("click", () => setUnit(button.dataset.unit));
            }});

            setUnit(localStorage.getItem("weatherUnit") || "f");
        </script>
    </body>
    </html>
    """


@app.get("/api/weather", response_class=JSONResponse)
def api_weather() -> Dict[str, Any]:
    return load_weather_data()


@app.get("/raw-json", response_class=JSONResponse)
def raw_json() -> Dict[str, Any]:
    return {
        city: get_json(f"https://api.weather.gov/points/{info['lat']},{info['lon']}", HEADERS)
        for city, info in NWS_CITIES.items()
    }
