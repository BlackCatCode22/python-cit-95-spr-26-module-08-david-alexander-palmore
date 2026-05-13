import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Any
from zoneinfo import ZoneInfo

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="David Palmore Weather Command Center")
app.mount("/static", StaticFiles(directory="static"), name="static")

HEADERS = {"User-Agent": "FCC-Student-App", "Accept": "application/geo+json, application/json"}

NWS_CITIES = {
    "Fresno, CA": {"lat": 36.7378, "lon": -119.7871, "timezone": "America/Los_Angeles", "tagline": "Central Valley live weather"},
    "New York, NY": {"lat": 40.7128, "lon": -74.0060, "timezone": "America/New_York", "tagline": "East Coast live weather"},
}

LONDON = {"city": "London, UK", "lat": 51.5072, "lon": -0.1276, "timezone": "Europe/London", "tagline": "International live weather"}
LONDON_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=51.5072&longitude=-0.1276"
    "&current_weather=true"
    "&timezone=Europe/London"
)
WEATHER_ICON_DIR = Path("static/weather-icons")
WEATHER_ICON_NAMES = {path.name for path in WEATHER_ICON_DIR.glob("*.svg")} if WEATHER_ICON_DIR.exists() else set()


def get_json(url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    response = requests.get(url, headers=headers, timeout=12)
    response.raise_for_status()
    return response.json()


def f_to_c(value):
    return None if value is None else round((float(value) - 32) * 5 / 9, 1)


def c_to_f(value):
    return None if value is None else round((float(value) * 9 / 5) + 32)


def kmh_to_mph(value):
    return None if value is None else round(float(value) * 0.621371)


def mph_to_kmh(value):
    return None if value is None else round(float(value) * 1.60934)


def mps_to_mph(value):
    return None if value is None else round(float(value) * 2.23694)


def meters_to_miles(value):
    return None if value is None else round(float(value) / 1609.344, 1)


def beaufort_icon(wind_mph):
    if wind_mph is None:
        return None
    thresholds = [1, 4, 8, 13, 19, 25, 32, 39, 47, 55, 64, 73]
    level = 0
    for index, threshold in enumerate(thresholds, start=1):
        if wind_mph >= threshold:
            level = index
    return f"wind-beaufort-{level}.svg"


def nws_speed_to_mph(speed):
    if not speed or speed.get("value") is None:
        return None
    unit_code = (speed.get("unitCode") or "").lower()
    if "km_h" in unit_code or "km/h" in unit_code:
        return kmh_to_mph(speed["value"])
    if "m_s" in unit_code or "m/s" in unit_code:
        return mps_to_mph(speed["value"])
    return round(float(speed["value"]))


def parse_forecast_wind_mph(wind_speed):
    if not wind_speed:
        return None
    speeds = [int(value) for value in re.findall(r"\d+", str(wind_speed))]
    return speeds[0] if speeds else None


def parse_forecast_gust_mph(text):
    if not text:
        return None
    match = re.search(r"gusts as high as (\d+)\s*mph", str(text), re.IGNORECASE)
    return int(match.group(1)) if match else None


def clean_nws_text(text):
    if not text:
        return "No detailed forecast available."
    cleaned = re.sub(r"\{\{[^}]+\}\}", "", str(text))
    cleaned = re.sub(r"\.\s*\.", ".", cleaned)
    cleaned = re.sub(r"\s+([.,;:])", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def current_observation_details(condition, temperatures, wind_mph, wind_gust_mph, observation):
    parts = [f"Currently {condition.lower()}."]
    if temperatures["f"] is not None:
        parts.append(f"Temperature {temperatures['f']}°F.")
    if wind_mph is not None:
        parts.append(f"Wind near {wind_mph} mph.")
    if wind_gust_mph is not None and (wind_mph is None or wind_gust_mph > wind_mph):
        parts.append(f"Gusts near {wind_gust_mph} mph.")

    humidity = observation.get("relativeHumidity", {}).get("value")
    visibility = observation.get("visibility", {}).get("value")
    if humidity is not None:
        parts.append(f"Humidity {round(float(humidity))}%.")
    if visibility is not None:
        parts.append(f"Visibility {meters_to_miles(visibility)} miles.")
    return " ".join(parts)


def normalize_temperature(temp, unit):
    if temp is None:
        return {"f": None, "c": None}
    if unit.upper() == "F":
        return {"f": round(float(temp)), "c": f_to_c(temp)}
    return {"f": c_to_f(temp), "c": round(float(temp), 1)}


def moon_phase_name(date: datetime) -> str:
    known_new = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    phase = (((date.astimezone(timezone.utc) - known_new).total_seconds() / 86400) % 29.53058867) / 29.53058867
    if phase < 0.03 or phase >= 0.97:
        return "New Moon"
    if phase < 0.22:
        return "Waxing Crescent"
    if phase < 0.28:
        return "First Quarter"
    if phase < 0.47:
        return "Waxing Gibbous"
    if phase < 0.53:
        return "Full Moon"
    if phase < 0.72:
        return "Waning Gibbous"
    if phase < 0.78:
        return "Last Quarter"
    return "Waning Crescent"


def get_astronomy(lat, lon, timezone_name):
    now = datetime.now(ZoneInfo(timezone_name))
    today = now.date().isoformat()
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=sunrise,sunset&timezone={timezone_name}"
        f"&start_date={today}&end_date={today}"
    )
    data = get_json(url)
    sunrise = datetime.fromisoformat(data["daily"]["sunrise"][0]).replace(tzinfo=ZoneInfo(timezone_name))
    sunset = datetime.fromisoformat(data["daily"]["sunset"][0]).replace(tzinfo=ZoneInfo(timezone_name))
    is_night = now < sunrise or now > sunset
    return {
        "timezone": timezone_name,
        "is_night": is_night,
        "sunrise": sunrise.isoformat(),
        "sunset": sunset.isoformat(),
        "moon_phase": moon_phase_name(now),
    }


def cloud_cover_key(text, is_night):
    daypart = "night" if is_night else "day"
    if "mostly clear" in text or "mainly clear" in text or "fair" in text:
        return f"mostly-clear-{daypart}"
    if "partly cloudy" in text or "partly sunny" in text or "few clouds" in text or "scattered clouds" in text:
        return f"partly-cloudy-{daypart}"
    if "mostly sunny" in text:
        return f"mostly-clear-{daypart}"
    if "mostly cloudy" in text or "broken clouds" in text or "considerable cloud" in text:
        return f"overcast-{daypart}"
    if "overcast" in text or "cloudy" in text:
        return f"overcast-{daypart}" if is_night else "cloudy"
    if "clear" in text or "sun" in text:
        return "clear-night" if is_night else "clear-day"
    return "clear-night" if is_night else "clear-day"


def weather_art(kind):
    art_map = {
        "sun": '<div class="art"><div class="sun-core"></div><div class="sun-rays"></div></div>',
        "moon": '<div class="art"><div class="moon-core"></div><div class="star s1"></div><div class="star s2"></div><div class="star s3"></div></div>',
        "night-partly": '<div class="art"><div class="moon-core small-moon"></div><div class="star s1"></div><div class="star s2"></div><div class="cloud c1"></div><div class="cloud c2"></div><div class="cloud c3"></div></div>',
        "partly": '<div class="art"><div class="sun-core small"></div><div class="sun-rays small-rays"></div><div class="cloud c1"></div><div class="cloud c2"></div><div class="cloud c3"></div></div>',
        "cloud": '<div class="art"><div class="cloud big c1"></div><div class="cloud big c2"></div><div class="cloud big c3"></div><div class="cloud-shadow"></div></div>',
        "rain": '<div class="art"><div class="cloud big c1"></div><div class="cloud big c2"></div><div class="cloud big c3"></div><div class="raindrops"><span></span><span></span><span></span><span></span><span></span></div></div>',
        "storm": '<div class="art"><div class="cloud dark c1"></div><div class="cloud dark c2"></div><div class="cloud dark c3"></div><div class="bolt"></div><div class="raindrops"><span></span><span></span><span></span></div></div>',
        "snow": '<div class="art"><div class="cloud big c1"></div><div class="cloud big c2"></div><div class="cloud big c3"></div><div class="snowflakes"><span>✦</span><span>✧</span><span>✦</span><span>✧</span></div></div>',
        "fog": '<div class="art"><div class="cloud big c1"></div><div class="cloud big c2"></div><div class="fog-lines"><span></span><span></span><span></span></div></div>',
    }
    return art_map.get(kind, '<div class="art"><div class="gauge">🌡️</div></div>')


def precipitation_key(text):
    if "sleet" in text or "freezing rain" in text or "wintry mix" in text:
        return "sleet"
    if "snow" in text or "flurr" in text or "blizzard" in text:
        return "snow"
    if "hail" in text:
        return "hail"
    if "drizzle" in text:
        return "drizzle"
    if "rain" in text or "showers" in text:
        return "rain"
    return None


def combo_cloud_key(cloud_key):
    if cloud_key in {"clear-day", "clear-night"}:
        return cloud_key.replace("clear", "mostly-clear")
    if cloud_key == "cloudy":
        return "overcast-day"
    return cloud_key


def icon_file(name, *fallbacks):
    candidates = [name, *fallbacks, "not-available"]
    for candidate in candidates:
        filename = f"{candidate}.svg"
        if filename in WEATHER_ICON_NAMES:
            return filename
    return "not-available.svg"


def weather_visual(condition, is_night, wind_mph=None, details=""):
    text = (condition or "").lower()
    detail_text = (details or "").lower()
    combined = f"{text} {detail_text}"
    daypart = "night" if is_night else "day"
    cloud_key = cloud_cover_key(text, is_night)
    combo_key = combo_cloud_key(cloud_key)
    precip_key = precipitation_key(text) or precipitation_key(detail_text)
    extreme = any(word in combined for word in ["heavy", "severe", "extreme", "violent", "blizzard", "hurricane", "tornado"])
    fallbacks = []

    if "tornado" in combined:
        icon = "tornado"
    elif "hurricane" in combined:
        icon = "hurricane"
    elif "thunder" in combined or "storm" in combined or "lightning" in combined:
        prefix = "extreme-thunderstorms" if extreme else "thunderstorms"
        icon = f"{prefix}-{combo_key}-{precip_key}" if precip_key else f"{prefix}-{combo_key}"
        if precip_key:
            fallbacks = [f"{prefix}-{daypart}-{precip_key}", f"{prefix}-{precip_key}", f"{combo_key}-{precip_key}", precip_key]
    elif "fog" in text or "mist" in text:
        icon = f"fog-{daypart}"
    elif "haze" in text:
        icon = f"haze-{daypart}"
    elif "smoke" in text:
        icon = f"{combo_key}-smoke" if cloud_key != "cloudy" else "smoke"
    elif "dust" in text:
        icon = f"dust-{daypart}"
    elif precip_key:
        icon = f"extreme-{combo_key}-{precip_key}" if extreme else f"{combo_key}-{precip_key}"
        if extreme:
            fallbacks = [f"extreme-{daypart}-{precip_key}", f"extreme-{precip_key}", f"{combo_key}-{precip_key}", precip_key]
        else:
            fallbacks = [precip_key]
    else:
        icon = cloud_key

    wind_icon = beaufort_icon(wind_mph) if wind_mph is not None and wind_mph >= 18 else None
    return {
        "icon": icon_file(icon, *fallbacks, cloud_key, "cloudy"),
        "wind_icon": wind_icon,
        "tone": icon.split("-")[0],
        "label": condition or "Current weather",
        "is_windy": wind_icon is not None,
    }


def weather_art_icon(visual):
    wind = ""
    if visual.get("wind_icon"):
        wind = f'<img class="wind-overlay" src="/static/weather-icons/{visual["wind_icon"]}" alt="Wind overlay">'
    return (
        f'<div class="art icon-art tone-{visual["tone"]}">'
        f'<img class="weather-icon" src="/static/weather-icons/{visual["icon"]}" alt="{visual["label"]}">'
        f'{wind}</div>'
    )


def open_meteo_condition(code):
    return {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle",
        53: "Moderate drizzle", 55: "Dense drizzle", 61: "Slight rain",
        63: "Moderate rain", 65: "Heavy rain", 71: "Slight snow fall",
        73: "Moderate snow fall", 75: "Heavy snow fall", 80: "Slight rain showers",
        81: "Moderate rain showers", 82: "Violent rain showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
    }.get(code, f"Weather code {code}")


def open_meteo_current_details(condition, temperatures, wind_mph):
    parts = [f"Currently {condition.lower()}."]
    if temperatures["f"] is not None:
        parts.append(f"Temperature {temperatures['f']}°F.")
    if wind_mph is not None:
        parts.append(f"Wind near {wind_mph} mph.")
    return " ".join(parts)


def get_nws_forecast(point_data):
    return get_json(point_data["properties"]["forecast"], HEADERS)["properties"]["periods"][0]


def get_nws_city(city, info):
    lat, lon, timezone_name = info["lat"], info["lon"], info["timezone"]
    point_data = get_json(f"https://api.weather.gov/points/{lat},{lon}", HEADERS)
    astronomy = get_astronomy(lat, lon, timezone_name)
    forecast = get_nws_forecast(point_data)
    forecast_temperatures = normalize_temperature(forecast.get("temperature"), forecast.get("temperatureUnit", "F"))
    forecast_wind_mph = parse_forecast_wind_mph(forecast.get("windSpeed"))
    forecast_details = clean_nws_text(forecast.get("detailedForecast"))
    details = "Current station details unavailable. Showing the nearest NWS forecast snapshot."
    forecast_gust_mph = parse_forecast_gust_mph(forecast_details)
    wind_gust_mph = None
    used_observation = False

    try:
        station_data = get_json(point_data["properties"]["observationStations"], HEADERS)
        station_url = station_data["features"][0]["id"]
        station_id = station_url.rstrip("/").split("/")[-1]
        observation = get_json(f"https://api.weather.gov/stations/{station_id}/observations/latest", HEADERS)["properties"]

        condition = observation.get("textDescription") or forecast.get("shortForecast", "Current weather unavailable")
        temperatures = normalize_temperature(observation.get("temperature", {}).get("value"), "C")
        if temperatures["f"] is None:
            temperatures = forecast_temperatures
        wind_gust_mph = nws_speed_to_mph(observation.get("windGust"))
        wind_mph = nws_speed_to_mph(observation.get("windSpeed")) or wind_gust_mph
        source = f"NWS station {station_id}"
        observed_iso = observation.get("timestamp")
        details = current_observation_details(condition, temperatures, wind_mph, wind_gust_mph, observation)
        used_observation = True
    except Exception:
        condition = forecast.get("shortForecast", "Forecast unavailable")
        temperatures = forecast_temperatures
        wind_mph = forecast_wind_mph
        source = "National Weather Service forecast"
        observed_iso = None

    visual_wind_mph = wind_mph if wind_mph is not None and wind_mph >= 18 else None
    gust_for_visual = wind_gust_mph if used_observation else forecast_gust_mph
    if visual_wind_mph is None and gust_for_visual is not None and gust_for_visual >= 25:
        visual_wind_mph = gust_for_visual
    visual = weather_visual(condition, astronomy["is_night"], visual_wind_mph)

    return {
        "city": city,
        "source": source,
        "tagline": info["tagline"],
        "data_mode": "Current Weather",
        "temp_f": temperatures["f"],
        "temp_c": temperatures["c"],
        "wind_mph": wind_mph,
        "wind_kmh": mph_to_kmh(wind_mph),
        "condition": condition,
        "visual": visual,
        "observed_iso": observed_iso,
        "details": details,
        **astronomy,
    }


def get_london_weather():
    astronomy = get_astronomy(LONDON["lat"], LONDON["lon"], LONDON["timezone"])
    data = get_json(LONDON_URL)
    current = data["current_weather"]
    condition = open_meteo_condition(int(current.get("weathercode", -1)))
    temperatures = normalize_temperature(current.get("temperature"), "C")
    wind_kmh = current.get("windspeed")
    wind_mph = kmh_to_mph(wind_kmh)
    details = open_meteo_current_details(condition, temperatures, wind_mph)
    visual = weather_visual(condition, astronomy["is_night"], wind_mph)

    return {
        "city": LONDON["city"],
        "source": "Open-Meteo",
        "tagline": LONDON["tagline"],
        "data_mode": "Current Weather",
        "temp_f": temperatures["f"],
        "temp_c": temperatures["c"],
        "wind_mph": wind_mph,
        "wind_kmh": round(float(wind_kmh)) if wind_kmh is not None else None,
        "condition": condition,
        "visual": visual,
        "observed_iso": None,
        "details": details,
        **astronomy,
    }


def load_weather_data():
    cities = []
    errors = []

    for city, info in NWS_CITIES.items():
        try:
            cities.append(get_nws_city(city, info))
        except Exception as error:
            errors.append(f"{city}: {error}")

    try:
        cities.append(get_london_weather())
    except Exception as error:
        errors.append(f"London, UK: {error}")

    return {"updated_iso": datetime.now(timezone.utc).isoformat(), "cities": cities, "errors": errors}


def city_card(city):
    moon = f"<p class='moon-phase'>Moon: {city['moon_phase']}</p>" if city.get("is_night") else ""
    temp_f = "" if city["temp_f"] is None else city["temp_f"]
    temp_c = "" if city["temp_c"] is None else city["temp_c"]
    wind_mph = "" if city["wind_mph"] is None else city["wind_mph"]
    wind_kmh = "" if city["wind_kmh"] is None else city["wind_kmh"]

    return f"""
    <article class="card condition-{city['visual']['tone']}">
        <div class="card-label"><span>{city['tagline']}</span><span>{city['source']}</span></div>
        <div class="city-row"><h2>{city['city']}</h2><p class="condition">{city['condition']}</p><p class="mode">{city['data_mode']}</p></div>
        {weather_art_icon(city["visual"])}
        <div class="temperature" data-f="{temp_f}" data-c="{temp_c}"><span class="temp-value"></span><span class="temp-unit"></span></div>
        <p class="wind" data-mph="{wind_mph}" data-kmh="{wind_kmh}">Wind: <span class="wind-value"></span> <span class="wind-unit"></span></p>
        {moon}
        <p class="local-time" data-timezone="{city['timezone']}"></p>
        <p class="details">{city['details']}</p>
    </article>
    """


@app.get("/", response_class=HTMLResponse)
def home():
    data = load_weather_data()
    cards = "".join(city_card(city) for city in data["cities"])
    errors = "".join(f"<li>{error}</li>" for error in data["errors"])
    error_html = f"<section class='error-box'><strong>Some feeds could not load:</strong><ul>{errors}</ul></section>" if errors else ""

    return f"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>David Palmore | Weather Command Center</title>
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#0f172a">
<style>
:root{{--card:rgba(15,23,42,.86);--border:rgba(148,163,184,.22);--text:#f8fafc;--muted:#cbd5e1;--blue:#38bdf8;--green:#22c55e}}
*{{box-sizing:border-box}}
body{{margin:0;min-height:100vh;font-family:Arial,Helvetica,sans-serif;color:var(--text);background:radial-gradient(circle at top left,rgba(56,189,248,.25),transparent 34rem),radial-gradient(circle at bottom right,rgba(251,146,60,.22),transparent 32rem),linear-gradient(135deg,#020617,#0f172a 55%,#111827)}}
.page{{width:min(1180px,calc(100% - 32px));margin:0 auto;padding:42px 0}}
.hero,.card,.error-box,.footer{{background:var(--card);border:1px solid var(--border);border-radius:28px;box-shadow:0 24px 80px rgba(0,0,0,.35);backdrop-filter:blur(18px)}}
.hero{{padding:34px;margin-bottom:24px;display:grid;grid-template-columns:1fr auto;gap:24px;align-items:center}}
.eyebrow{{color:var(--blue);letter-spacing:.18em;text-transform:uppercase;font-size:.8rem;font-weight:800}}
h1{{font-size:clamp(2.6rem,7vw,5.4rem);line-height:.92;margin:16px 0}}
.hero p{{color:var(--muted);max-width:780px;font-size:1.08rem;line-height:1.7}}
.unit-panel{{border:1px solid var(--border);background:rgba(15,23,42,.72);border-radius:22px;padding:18px;min-width:250px;display:grid;gap:18px}}
.unit-title{{color:var(--muted);font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;margin-bottom:12px}}
.unit-buttons{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
.unit-button{{border:1px solid var(--border);border-radius:14px;padding:12px;cursor:pointer;color:var(--text);background:rgba(30,41,59,.9);font-size:.95rem;font-weight:900}}
.unit-button.active,.unit-button[aria-pressed="true"]{{background:linear-gradient(135deg,#2563eb,#38bdf8);box-shadow:0 0 28px rgba(56,189,248,.28)}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}}
.card{{padding:24px;overflow:hidden;position:relative;min-height:590px}}
.card::before{{content:"";position:absolute;top:-80px;right:-80px;width:220px;height:220px;background:radial-gradient(circle,rgba(56,189,248,.28),transparent 70%)}}
.condition-clear::before,.condition-mostly::before,.condition-partly::before{{background:radial-gradient(circle,rgba(250,204,21,.24),transparent 70%)}}
.condition-overcast::before,.condition-cloudy::before,.condition-fog::before,.condition-haze::before{{background:radial-gradient(circle,rgba(148,163,184,.28),transparent 70%)}}
.condition-rain::before,.condition-drizzle::before,.condition-sleet::before,.condition-thunderstorms::before{{background:radial-gradient(circle,rgba(14,165,233,.30),transparent 70%)}}
.condition-snow::before{{background:radial-gradient(circle,rgba(191,219,254,.30),transparent 70%)}}
.card-label{{display:flex;justify-content:space-between;gap:12px;color:var(--muted);font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;margin-bottom:28px;position:relative;z-index:2}}
.city-row{{position:relative;z-index:2}}
h2{{font-size:1.7rem;margin:0}}
.condition{{color:var(--muted);margin:8px 0 0}}
.mode{{display:inline-block;color:#bae6fd;font-size:.75rem;margin:10px 0 0;padding:6px 10px;border:1px solid rgba(56,189,248,.28);border-radius:999px;background:rgba(14,165,233,.1)}}
.art{{height:150px;margin:18px 0 8px;position:relative;z-index:1;filter:drop-shadow(0 18px 18px rgba(0,0,0,.35))}}
.icon-art{{height:190px;margin:10px 0 -6px;display:flex;align-items:center;justify-content:center;filter:drop-shadow(0 24px 24px rgba(0,0,0,.42))}}
.weather-icon{{width:min(210px,86%);height:190px;object-fit:contain;animation:floatWeather 6s ease-in-out infinite}}
.wind-overlay{{position:absolute;right:18px;bottom:16px;width:74px;height:74px;padding:10px;border-radius:50%;background:rgba(15,23,42,.72);border:1px solid rgba(186,230,253,.28);box-shadow:0 14px 34px rgba(14,165,233,.25);animation:windPulse 1.8s ease-in-out infinite}}
.sun-core{{position:absolute;width:96px;height:96px;left:34px;top:22px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#fff7ad 0 13%,#fde047 22%,#facc15 54%,#f97316 100%);box-shadow:0 0 32px rgba(250,204,21,.75),0 0 72px rgba(251,146,60,.42)}}
.sun-core.small{{width:86px;height:86px;left:24px;top:24px}}
.sun-rays{{position:absolute;width:142px;height:142px;left:11px;top:-1px;border-radius:50%;background:repeating-conic-gradient(from 0deg,rgba(250,204,21,.95) 0deg 7deg,transparent 7deg 17deg);-webkit-mask:radial-gradient(circle,transparent 0 42%,black 44% 62%,transparent 64%);mask:radial-gradient(circle,transparent 0 42%,black 44% 62%,transparent 64%);animation:spin 18s linear infinite}}
.small-rays{{width:128px;height:128px;left:3px;top:3px}}
.moon-core{{position:absolute;width:96px;height:96px;left:44px;top:24px;border-radius:50%;background:radial-gradient(circle at 35% 28%,#f8fafc 0 10%,#dbeafe 36%,#94a3b8 76%,#64748b 100%);box-shadow:0 0 42px rgba(191,219,254,.45),0 0 82px rgba(56,189,248,.24)}}
.moon-core::after{{content:"";position:absolute;width:78px;height:78px;right:-16px;top:4px;border-radius:50%;background:rgba(15,23,42,.88)}}
.small-moon{{width:86px;height:86px;left:28px;top:24px}}
.star{{position:absolute;width:6px;height:6px;border-radius:50%;background:#e0f2fe;box-shadow:0 0 14px #bae6fd}}
.s1{{left:160px;top:28px}}.s2{{left:205px;top:72px;transform:scale(.7)}}.s3{{left:142px;top:118px;transform:scale(.55)}}
.cloud{{position:absolute;height:52px;width:122px;border-radius:999px;background:radial-gradient(circle at 25% 30%,#fff 0 18%,transparent 19%),radial-gradient(circle at 48% 12%,#f8fafc 0 25%,transparent 26%),radial-gradient(circle at 72% 34%,#dbeafe 0 20%,transparent 21%),linear-gradient(180deg,#f8fafc,#cbd5e1 60%,#94a3b8);box-shadow:inset 10px 14px 24px rgba(255,255,255,.55),inset -14px -14px 24px rgba(15,23,42,.22)}}
.cloud.big{{width:152px;height:62px}}.cloud.dark{{width:150px;height:62px;background:linear-gradient(180deg,#94a3b8,#475569 60%,#1e293b)}}
.c1{{left:68px;top:82px}}.c2{{left:110px;top:64px;transform:scale(.88);opacity:.9}}.c3{{left:28px;top:98px;transform:scale(.72);opacity:.95}}
.cloud-shadow{{position:absolute;width:180px;height:22px;left:38px;top:128px;background:radial-gradient(ellipse,rgba(56,189,248,.28),transparent 70%)}}
.raindrops{{position:absolute;left:62px;top:124px;display:flex;gap:18px}}
.raindrops span{{width:8px;height:24px;border-radius:999px;background:linear-gradient(#38bdf8,#0284c7);transform:rotate(18deg);animation:rain 900ms ease-in-out infinite}}
.bolt{{position:absolute;left:124px;top:108px;width:34px;height:70px;background:linear-gradient(#fef08a,#facc15,#f97316);clip-path:polygon(46% 0,100% 0,62% 42%,100% 42%,24% 100%,44% 54%,8% 54%);filter:drop-shadow(0 0 18px rgba(250,204,21,.85))}}
.snowflakes{{position:absolute;left:58px;top:122px;display:flex;gap:22px;color:#e0f2fe;font-size:1.45rem;text-shadow:0 0 14px rgba(125,211,252,.85)}}
.fog-lines{{position:absolute;left:32px;top:120px;width:210px}}
.fog-lines span{{display:block;height:8px;border-radius:999px;margin:10px 0;background:linear-gradient(90deg,transparent,rgba(226,232,240,.85),transparent);animation:drift 3.2s ease-in-out infinite}}
.gauge{{font-size:5rem;padding:30px 0}}
.temperature{{font-size:4rem;font-weight:900;letter-spacing:-.08em;margin-top:10px;position:relative;z-index:2}}
.temperature.unavailable{{font-size:1.6rem;letter-spacing:0;color:var(--muted)}}
.temp-unit{{letter-spacing:-.03em}}.wind{{color:var(--blue);font-weight:700}}.moon-phase{{color:#c4b5fd;font-weight:700;margin:0 0 12px}}.local-time{{color:var(--text);font-weight:700;margin:0 0 12px}}.details{{color:var(--muted);line-height:1.65}}
.footer{{color:var(--muted);display:flex;justify-content:space-between;gap:16px;margin-top:24px;padding:18px 24px;font-size:.95rem}}
.error-box{{padding:18px 22px;border-color:rgba(248,113,113,.45);margin-bottom:20px}}code{{color:var(--green)}}
@keyframes spin{{from{{transform:rotate(0)}}to{{transform:rotate(360deg)}}}}
@keyframes rain{{0%,100%{{transform:translateY(0) rotate(18deg);opacity:.55}}50%{{transform:translateY(12px) rotate(18deg);opacity:1}}}}
@keyframes drift{{0%,100%{{transform:translateX(-10px);opacity:.45}}50%{{transform:translateX(12px);opacity:1}}}}
@keyframes floatWeather{{0%,100%{{transform:translateY(0) scale(1)}}50%{{transform:translateY(-7px) scale(1.03)}}}}
@keyframes windPulse{{0%,100%{{transform:translateX(0);opacity:.72}}50%{{transform:translateX(8px);opacity:1}}}}
@media(max-width:900px){{.hero{{grid-template-columns:1fr}}.grid{{grid-template-columns:1fr}}.footer{{flex-direction:column}}.card{{min-height:auto}}}}
</style>
</head>
<body>
<main class="page">
<section class="hero">
<div><div class="eyebrow">CIT-95 Module 8 • FastAPI + JSON APIs</div><h1>Weather Command Center</h1><p>Built by David Palmore. This FastAPI dashboard fetches live JSON weather data, parses it into Python dictionaries, and displays Fresno, New York, and London in a polished web interface.</p></div>
<aside class="unit-panel">
<div><div class="unit-title">Unit System</div><div class="unit-buttons"><button class="unit-button active" type="button" data-unit="imperial" aria-pressed="true">Imperial</button><button class="unit-button" type="button" data-unit="metric" aria-pressed="false">Metric</button></div></div>
<div><div class="unit-title">Time Format</div><div class="unit-buttons"><button class="unit-button active" type="button" data-time-format="12" aria-pressed="true">12 hr</button><button class="unit-button" type="button" data-time-format="24" aria-pressed="false">24 hr</button></div></div>
</aside>
</section>
{error_html}
<section class="grid">{cards}</section>
<section class="footer"><span id="updated-time" data-updated="{data['updated_iso']}">Last updated: loading...</span><span>API endpoint: <code>/api/weather</code> | Raw NWS JSON: <code>/raw-json</code></span></section>
</main>
<script>
const validUnits=new Set(["imperial","metric"]);
const validTimeFormats=new Set(["12","24"]);
let currentTimeFormat="12";
function setPressed(selector,attr,value){{document.querySelectorAll(selector).forEach(b=>{{const active=b.dataset[attr]===value;b.classList.toggle("active",active);b.setAttribute("aria-pressed",active?"true":"false")}})}}
function setUnit(unit){{unit=validUnits.has(unit)?unit:"imperial";const imp=unit==="imperial";setPressed("[data-unit]","unit",unit);document.querySelectorAll(".temperature").forEach(t=>{{const value=imp?t.dataset.f:t.dataset.c;t.classList.toggle("unavailable",!value);t.querySelector(".temp-value").textContent=value||"Unavailable";t.querySelector(".temp-unit").textContent=value?(imp?"°F":"°C"):""}});document.querySelectorAll(".wind").forEach(w=>{{const value=imp?w.dataset.mph:w.dataset.kmh;w.querySelector(".wind-value").textContent=value||"Unavailable";w.querySelector(".wind-unit").textContent=value?(imp?"mph":"km/h"):""}});localStorage.setItem("weatherUnit",unit)}}
function formatDateTime(iso){{if(!iso)return "";const d=new Date(iso);const tz=Intl.DateTimeFormat().resolvedOptions().timeZone;return new Intl.DateTimeFormat(undefined,{{year:"numeric",month:"short",day:"numeric",hour:"numeric",minute:"2-digit",hour12:currentTimeFormat==="12",timeZone:tz,timeZoneName:"short"}}).format(d)}}
function formatZoneTime(timeZone){{return new Intl.DateTimeFormat(undefined,{{hour:"numeric",minute:"2-digit",hour12:currentTimeFormat==="12",timeZone,timeZoneName:"short"}}).format(new Date())}}
function refreshTimes(){{const u=document.getElementById("updated-time");u.textContent="Last updated: "+formatDateTime(u.dataset.updated);document.querySelectorAll(".local-time").forEach(i=>{{i.textContent="Local time: "+formatZoneTime(i.dataset.timezone)}})}}
function setTimeFormat(format){{currentTimeFormat=validTimeFormats.has(format)?format:"12";setPressed("[data-time-format]","timeFormat",currentTimeFormat);localStorage.setItem("weatherTimeFormat",currentTimeFormat);refreshTimes()}}
document.querySelectorAll("[data-unit]").forEach(b=>b.addEventListener("click",()=>setUnit(b.dataset.unit)));
document.querySelectorAll("[data-time-format]").forEach(b=>b.addEventListener("click",()=>setTimeFormat(b.dataset.timeFormat)));
setUnit(localStorage.getItem("weatherUnit")||"imperial");
setTimeFormat(localStorage.getItem("weatherTimeFormat")||"12");
setInterval(refreshTimes,60000);
if("serviceWorker" in navigator){{window.addEventListener("load",()=>navigator.serviceWorker.register("/static/sw.js"))}}
</script>
</body>
</html>
    """


@app.get("/api/weather", response_class=JSONResponse)
def api_weather():
    return load_weather_data()


@app.get("/raw-json", response_class=JSONResponse)
def raw_json():
    return {city: get_json(f"https://api.weather.gov/points/{info['lat']},{info['lon']}", HEADERS) for city, info in NWS_CITIES.items()}


@app.get("/raw-observations", response_class=JSONResponse)
def raw_observations():
    out = {}
    for city, info in NWS_CITIES.items():
        point = get_json(f"https://api.weather.gov/points/{info['lat']},{info['lon']}", HEADERS)
        stations = get_json(point["properties"]["observationStations"], HEADERS)
        station_id = stations["features"][0]["id"].rstrip("/").split("/")[-1]
        out[city] = get_json(f"https://api.weather.gov/stations/{station_id}/observations/latest", HEADERS)
    return out
