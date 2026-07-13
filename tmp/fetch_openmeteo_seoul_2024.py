#!/usr/bin/env python3
import json, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

BASE = "https://archive-api.open-meteo.com/v1/archive"
COMMON = {
    "latitude": 37.57142,
    "longitude": 126.9658,
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "timezone": "Asia/Seoul",
    "temperature_unit": "celsius",
    "wind_speed_unit": "ms",
    "precipitation_unit": "mm",
    "cell_selection": "land",
}
PRIMARY_VARS = [
    "temperature_2m", "relative_humidity_2m", "dew_point_2m",
    "apparent_temperature", "wet_bulb_temperature_2m", "precipitation",
    "rain", "snowfall", "snow_depth", "weather_code", "pressure_msl",
    "surface_pressure", "cloud_cover", "cloud_cover_low", "cloud_cover_mid",
    "cloud_cover_high", "et0_fao_evapotranspiration", "vapour_pressure_deficit",
    "wind_speed_10m", "wind_speed_100m", "wind_direction_10m",
    "wind_direction_100m", "wind_gusts_10m", "soil_temperature_0_to_7cm",
    "soil_temperature_7_to_28cm", "soil_temperature_28_to_100cm",
    "soil_temperature_100_to_255cm", "soil_moisture_0_to_7cm",
    "soil_moisture_7_to_28cm", "soil_moisture_28_to_100cm",
    "soil_moisture_100_to_255cm", "boundary_layer_height",
    "total_column_integrated_water_vapour", "is_day", "sunshine_duration",
    "shortwave_radiation", "direct_radiation", "diffuse_radiation",
    "direct_normal_irradiance", "terrestrial_radiation",
    "shortwave_radiation_instant", "direct_radiation_instant",
    "diffuse_radiation_instant", "direct_normal_irradiance_instant",
    "terrestrial_radiation_instant"
]
ERA5_VARS = [
    "temperature_2m", "relative_humidity_2m", "dew_point_2m",
    "precipitation", "pressure_msl", "wind_speed_10m", "cloud_cover"
]

class BadVariable(Exception):
    pass

def request_group(variables, model=None):
    params = dict(COMMON)
    params["hourly"] = ",".join(variables)
    if model:
        params["models"] = model
    url = BASE + "?" + urllib.parse.urlencode(params, safe=",")
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "seoul-weather-export/1.0"})
            with urllib.request.urlopen(req, timeout=180) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            if exc.code == 400:
                raise BadVariable(body) from exc
            last = RuntimeError(f"HTTP {exc.code}: {body[:500]}")
        except Exception as exc:
            last = exc
        if attempt < 4:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"request failed: {last}; {url}")

def merge(parts):
    parts = [p for p in parts if p]
    base = {k: v for k, v in parts[0].items() if k not in ("hourly", "hourly_units")}
    base["hourly"] = {"time": parts[0]["hourly"]["time"]}
    base["hourly_units"] = {"time": parts[0].get("hourly_units", {}).get("time", "iso8601")}
    for part in parts:
        if part["hourly"]["time"] != base["hourly"]["time"]:
            raise RuntimeError("timestamp mismatch between chunks")
        for key, values in part["hourly"].items():
            if key != "time":
                base["hourly"][key] = values
                base["hourly_units"][key] = part.get("hourly_units", {}).get(key, "")
    return base

def fetch_isolated(variables, model, unsupported):
    try:
        return request_group(variables, model)
    except BadVariable as exc:
        if len(variables) == 1:
            unsupported.append({"model": model or "best_match", "variable": variables[0], "reason": str(exc)})
            print("UNSUPPORTED", model or "best_match", variables[0], str(exc)[:300])
            return None
        mid = len(variables) // 2
        left = fetch_isolated(variables[:mid], model, unsupported)
        right = fetch_isolated(variables[mid:], model, unsupported)
        return merge([left, right]) if left or right else None

out = Path("raw")
out.mkdir(exist_ok=True)
unsupported = []
primary = fetch_isolated(PRIMARY_VARS, None, unsupported)
era5 = fetch_isolated(ERA5_VARS, "era5", unsupported)
if primary is None or era5 is None:
    raise SystemExit("required dataset could not be fetched")
for name, payload in (("primary.json", primary), ("era5.json", era5)):
    (out / name).write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
(out / "unsupported.json").write_text(json.dumps(unsupported, ensure_ascii=False, indent=2), encoding="utf-8")
print("PRIMARY_ROWS", len(primary["hourly"]["time"]))
print("PRIMARY_VARIABLES", sorted(k for k in primary["hourly"] if k != "time"))
print("ERA5_ROWS", len(era5["hourly"]["time"]))
print("UNSUPPORTED", unsupported)
