"""Weather + sunrise/sunset via Open-Meteo (free, keyless)."""
import requests
import config

WEATHER_CODES = {
    0: "Clear", 1: "Mostly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime Fog",
    51: "Light Drizzle", 53: "Drizzle", 55: "Heavy Drizzle",
    61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
    66: "Freezing Rain", 67: "Freezing Rain",
    71: "Light Snow", 73: "Snow", 75: "Heavy Snow", 77: "Snow Grains",
    80: "Rain Showers", 81: "Rain Showers", 82: "Violent Showers",
    85: "Snow Showers", 86: "Snow Showers",
    95: "Thunderstorm", 96: "Thunderstorm/Hail", 99: "Thunderstorm/Hail",
}


def fetch():
    temp_unit = "fahrenheit" if config.WEATHER_UNITS == "imperial" else "celsius"
    wind_unit = "mph" if config.WEATHER_UNITS == "imperial" else "kmh"
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": config.LATITUDE,
                "longitude": config.LONGITUDE,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "daily": "sunrise,sunset,temperature_2m_max,temperature_2m_min",
                "temperature_unit": temp_unit,
                "wind_speed_unit": wind_unit,
                "timezone": config.TIMEZONE,
            },
            timeout=8,
        )
        r.raise_for_status()
        data = r.json()
        cur = data.get("current", {})
        daily = data.get("daily", {})
        code = cur.get("weather_code")
        return {
            "temp": cur.get("temperature_2m"),
            "humidity": cur.get("relative_humidity_2m"),
            "wind": cur.get("wind_speed_10m"),
            "condition": WEATHER_CODES.get(code, "Unknown"),
            "code": code,
            "sunrise": (daily.get("sunrise") or [None])[0],
            "sunset": (daily.get("sunset") or [None])[0],
            "temp_high": (daily.get("temperature_2m_max") or [None])[0],
            "temp_low": (daily.get("temperature_2m_min") or [None])[0],
            "units": config.WEATHER_UNITS,
        }
    except Exception:
        return None
