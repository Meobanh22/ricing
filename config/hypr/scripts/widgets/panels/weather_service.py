#!/usr/bin/env python3
# panels/weather_service.py — Geolocation and weather forecast parsing for desktop widgets.

import datetime
import json
import os
import time
import urllib.request

from panels.common import get_repo_root

DAYS_SHORT_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

WMO_MAP = {
    0: ("Clear", "󰖙", "󰼱"),
    1: ("Mainly clear", "󰖕", "󰼱"),
    2: ("Partly cloudy", "󰖕", "󰼱"),
    3: ("Overcast", "󰖐", "󰖐"),
    45: ("Fog", "󰖑", "󰖑"),
    48: ("Rime fog", "󰖑", "󰖑"),
    51: ("Light drizzle", "󰖗", "󰖗"),
    53: ("Drizzle", "󰖗", "󰖗"),
    55: ("Dense drizzle", "󰖗", "󰖗"),
    56: ("Freezing drizzle", "󰖘", "󰖘"),
    57: ("Freezing drizzle", "󰖘", "󰖘"),
    61: ("Light rain", "󰖗", "󰖗"),
    63: ("Moderate rain", "󰖗", "󰖗"),
    65: ("Heavy rain", "󰖗", "󰖗"),
    66: ("Freezing rain", "󰖘", "󰖘"),
    67: ("Freezing rain", "󰖘", "󰖘"),
    71: ("Light snow", "󰖘", "󰖘"),
    73: ("Snow", "󰖘", "󰖘"),
    75: ("Heavy snow", "󰖘", "󰖘"),
    77: ("Snow grains", "󰖘", "󰖘"),
    80: ("Rain showers", "󰖗", "󰖗"),
    81: ("Rain showers", "󰖗", "󰖗"),
    82: ("Violent rain", "󰖗", "󰖗"),
    85: ("Snow showers", "󰖘", "󰖘"),
    86: ("Heavy snow showers", "󰖘", "󰖘"),
    95: ("Thunderstorm", "󰖓", "󰖓"),
    96: ("Thunderstorm", "󰖓", "󰖓"),
    99: ("Thunderstorm", "󰖓", "󰖓"),
}


def get_weather_icon(desc: str, hour: int) -> str:
    """Return appropriate weather glyph according to description and time."""
    low = desc.lower()
    is_day = 6 <= hour < 17
    if "thunder" in low or "lightning" in low:
        return "󰖓"
    if "snow" in low or "ice" in low or "sleet" in low or "blizzard" in low:
        return "󰖘"
    if "rain" in low or "drizzle" in low or "shower" in low:
        return "󰖗"
    if "fog" in low or "mist" in low or "haze" in low:
        return "󰖑"
    if "partly cloudy" in low or "few clouds" in low:
        return "󰖕" if is_day else "󰼱"
    if "cloud" in low or "overcast" in low:
        return "󰖐"
    if "clear" in low or "sunny" in low:
        return "󰖙" if is_day else "󰼱"
    return "󰖕" if is_day else "󰼱"


def get_user_location(force_refresh=False):
    """Get user coordinates (lat, lon, city_name) with VPN sanity checks and Hanoi fallback."""
    repo_root = get_repo_root()
    candidate_confs = [
        os.path.expanduser("~/.config/hypr/weather_location.json"),
        os.path.join(repo_root, "config", "hypr", "weather_location.json") if repo_root else "",
    ]
    cfg = None
    for user_conf in candidate_confs:
        if user_conf and os.path.exists(user_conf):
            try:
                with open(user_conf, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    break
            except Exception:
                pass

    if cfg and isinstance(cfg, dict) and not cfg.get("auto_detect", True):
        if "latitude" in cfg and "longitude" in cfg:
            return float(cfg["latitude"]), float(cfg["longitude"]), cfg.get("city", "Hanoi")

    geo_cache = os.path.expanduser("~/.cache/user_geo_location.json")
    if not force_refresh and os.path.exists(geo_cache):
        try:
            if time.time() - os.path.getmtime(geo_cache) < 3600:
                with open(geo_cache, "r", encoding="utf-8") as f:
                    cdata = json.load(f)
                    if "lat" in cdata and "lon" in cdata:
                        return float(cdata["lat"]), float(cdata["lon"]), cdata.get("city", "Hanoi")
        except Exception:
            pass

    local_offset = -time.timezone if (time.localtime().tm_isdst == 0) else -time.altzone

    try:
        req = urllib.request.Request("http://ip-api.com/json", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get("status") == "success" and "lat" in data and "lon" in data:
                lat, lon = float(data["lat"]), float(data["lon"])
                city = data.get("city", "Hanoi")
                ip_tz = data.get("timezone", "")
                is_vpn = False
                if abs(local_offset - 25200) < 1800:
                    if not (ip_tz.startswith("Asia/Ho_Chi_Minh") or ip_tz.startswith("Asia/Bangkok") or data.get("countryCode") == "VN"):
                        is_vpn = True
                if not is_vpn:
                    try:
                        with open(geo_cache, "w", encoding="utf-8") as f:
                            json.dump({"lat": lat, "lon": lon, "city": city}, f)
                    except Exception:
                        pass
                    return lat, lon, city
    except Exception:
        pass

    try:
        req = urllib.request.Request("https://ipinfo.io/json", headers={'User-Agent': 'curl/8.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if "loc" in data:
                lat_str, lon_str = data["loc"].split(",")
                lat, lon = float(lat_str), float(lon_str)
                city = data.get("city", "Hanoi")
                if data.get("country") == "VN" or abs(local_offset - 25200) > 1800:
                    try:
                        with open(geo_cache, "w", encoding="utf-8") as f:
                            json.dump({"lat": lat, "lon": lon, "city": city}, f)
                    except Exception:
                        pass
                    return lat, lon, city
    except Exception:
        pass

    if cfg and "latitude" in cfg and "longitude" in cfg:
        return float(cfg["latitude"]), float(cfg["longitude"]), cfg.get("city", "Hanoi")

    return 21.0285, 105.8542, "Hanoi"


def parse_open_meteo_forecast(data: dict):
    curr = data.get("current", {})
    hour = datetime.datetime.now().hour
    is_day = bool(curr.get("is_day", 1 if 6 <= hour < 18 else 0))
    code = curr.get("weather_code", 0)
    desc, ico_d, ico_n = WMO_MAP.get(code, ("Clear", "󰖙", "󰼱"))
    curr_icon = ico_d if is_day else ico_n
    temp_c = str(int(round(curr.get("temperature_2m", 0))))

    daily = data.get("daily", {})
    dates = daily.get("time", [])[:3]
    codes = daily.get("weather_code", [])[:3]
    maxs = daily.get("temperature_2m_max", [])[:3]
    mins = daily.get("temperature_2m_min", [])[:3]

    forecast_list = []
    for i in range(len(dates)):
        try:
            dt = datetime.datetime.strptime(dates[i], "%Y-%m-%d")
            day_name = "Today" if i == 0 else DAYS_SHORT_EN[dt.weekday()]
        except Exception:
            day_name = f"Day {i + 1}"
        d_code = codes[i] if i < len(codes) else 0
        _, d_ico, _ = WMO_MAP.get(d_code, ("Clear", "󰖙", "󰼱"))
        d_max = str(int(round(maxs[i]))) if i < len(maxs) else "--"
        d_min = str(int(round(mins[i]))) if i < len(mins) else "--"
        forecast_list.append({
            "day": day_name,
            "icon": d_ico,
            "max": d_max,
            "min": d_min,
            "full_desc": WMO_MAP.get(d_code, ("Clear",))[0],
        })

    return temp_c, curr_icon, desc, forecast_list


def parse_forecast_day(day_data: dict, day_index: int) -> dict:
    """Parse wttr.in daily forecast item into day name, icon, short condition, max & min temp."""
    date_str = day_data.get('date', '')
    try:
        dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        day_name = "Today" if day_index == 0 else DAYS_SHORT_EN[dt.weekday()]
    except Exception:
        day_name = f"Day {day_index + 1}"

    max_c = day_data.get('maxtempC', '--')
    min_c = day_data.get('mintempC', '--')

    hourly = day_data.get('hourly', [])
    desc = hourly[4]['weatherDesc'][0]['value'] if len(hourly) > 4 else (hourly[0]['weatherDesc'][0]['value'] if hourly else 'Clear')

    low = desc.lower()
    if "thunder" in low or "lightning" in low:
        icon, short = "󰖓", "Thunder"
    elif "snow" in low or "ice" in low or "sleet" in low or "blizzard" in low:
        icon, short = "󰖘", "Snow"
    elif "rain" in low or "drizzle" in low or "shower" in low:
        icon, short = "󰖗", "Rain"
    elif "fog" in low or "mist" in low or "haze" in low:
        icon, short = "󰖑", "Fog"
    elif "partly cloudy" in low or "few clouds" in low:
        icon, short = "󰖕", "P.Cloud"
    elif "cloud" in low or "overcast" in low:
        icon, short = "󰖐", "Cloudy"
    elif "clear" in low or "sunny" in low:
        icon, short = "󰖙", "Sunny"
    else:
        icon, short = "󰖕", "Clear"

    return {
        "day": day_name,
        "icon": icon,
        "short_desc": short,
        "max": max_c,
        "min": min_c,
        "full_desc": desc,
    }
