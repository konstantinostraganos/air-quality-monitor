"""
Air Quality Data Pipeline
Ingests air quality data from OpenAQ API v3 into DuckDB.
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone

import dlt
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Kept under data/ so the docker-compose volume persists it across container restarts
DB_PATH = "data/openaq_pipeline.duckdb"


class OpenAQClient:
    """Client for OpenAQ API v3 with rate limiting and pagination."""

    BASE_URL = "https://api.openaq.org/v3"
    REQUEST_DELAY = 1.0  # seconds between requests

    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})
        self._locations_cache = {}  # country_id -> locations list

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """Make a GET request with retry on rate limiting."""
        url = f"{self.BASE_URL}/{endpoint}"
        max_retries = 7

        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)

                if response.status_code == 429:
                    wait = min(2**attempt, 60)  # cap at 60s
                    logger.warning(f"Rate limited. Waiting {wait}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    logger.error(f"API request failed: {endpoint} — {e}")
                    raise
                time.sleep(2**attempt)

        raise RuntimeError(f"Max retries exceeded for {endpoint}")

    def get_locations(self, country_id: str, limit: int = 100) -> list:
        """Fetch all monitoring stations for a country, with caching."""
        # Return cached results if available
        if country_id in self._locations_cache:
            return self._locations_cache[country_id]

        all_locations = []
        page = 1

        while True:
            logger.info(f"Fetching locations for country {country_id}, page {page}")
            data = self._get(
                "locations",
                params={"countries_id": country_id, "limit": limit, "page": page},
            )
            results = data.get("results", [])
            if not results:
                break

            all_locations.extend(results)
            if len(all_locations) >= 50:
                all_locations = all_locations[:50]
                break
            page += 1
            time.sleep(self.REQUEST_DELAY)

        logger.info(f"Found {len(all_locations)} locations for country {country_id}")
        self._locations_cache[country_id] = all_locations
        return all_locations

    def get_sensor_measurements(self, sensor_id: int, date_from: str, date_to: str) -> list:
        """Fetch daily aggregated measurements for a single sensor."""
        all_measurements = []
        page = 1

        while True:
            data = self._get(
                f"sensors/{sensor_id}/days",
                params={
                    "date_from": date_from,
                    "date_to": date_to,
                    "limit": 100,
                    "page": page,
                },
            )
            results = data.get("results", [])
            if not results:
                break

            all_measurements.extend(results)
            page += 1
            time.sleep(self.REQUEST_DELAY)

        return all_measurements


# ── dlt resources ──


@dlt.resource(name="locations", write_disposition="replace")
def locations_resource(client: OpenAQClient, countries: list[str]):
    """Load monitoring station metadata."""
    for country in countries:
        for loc in client.get_locations(country):
            yield {
                "id": loc["id"],
                "name": loc["name"],
                "locality": loc.get("locality"),
                "timezone": loc.get("timezone"),
                "country_code": (loc.get("country") or {}).get("code"),
                "country_name": (loc.get("country") or {}).get("name"),
                "latitude": (loc.get("coordinates") or {}).get("latitude"),
                "longitude": (loc.get("coordinates") or {}).get("longitude"),
                "is_mobile": loc.get("isMobile", False),
                "is_monitor": loc.get("isMonitor", False),
                "provider_name": (loc.get("provider") or {}).get("name"),
                "first_datetime_utc": (loc.get("datetimeFirst") or {}).get("utc"),
                "last_datetime_utc": (loc.get("datetimeLast") or {}).get("utc"),
            }


@dlt.resource(name="sensors", write_disposition="replace")
def sensors_resource(client: OpenAQClient, countries: list[str]):
    """Load sensor details from each location."""
    for country in countries:
        for loc in client.get_locations(country):
            for sensor in loc.get("sensors", []):
                yield {
                    "sensor_id": sensor["id"],
                    "location_id": loc["id"],
                    "location_name": loc["name"],
                    "country_code": (loc.get("country") or {}).get("code"),
                    "city": loc.get("locality"),
                    "parameter_id": (sensor.get("parameter") or {}).get("id"),
                    "parameter_name": (sensor.get("parameter") or {}).get("name"),
                    "parameter_units": (sensor.get("parameter") or {}).get("units"),
                    "parameter_display": (sensor.get("parameter") or {}).get("displayName"),
                }


@dlt.resource(name="measurements", write_disposition="replace")
def measurements_resource(client: OpenAQClient, countries: list[str], days_back: int = 30):
    """Load daily aggregated measurements for target pollutants."""
    date_to = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_from = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    target_params = {"pm25", "pm10", "no2", "co", "o3", "so2"}

    logger.info(f"Fetching measurements from {date_from} to {date_to}")

    sensor_count = 0
    for country in countries:
        for loc in client.get_locations(country):
            for sensor in loc.get("sensors", []):
                param = sensor.get("parameter") or {}
                if param.get("name", "").lower() not in target_params:
                    continue

                sensor_count += 1
                if sensor_count % 10 == 0:
                    logger.info(f"Processing sensor {sensor_count}...")

                try:
                    for m in client.get_sensor_measurements(sensor["id"], date_from, date_to):
                        period = m.get("period") or {}
                        summary = m.get("summary") or {}
                        yield {
                            "sensor_id": sensor["id"],
                            "location_id": loc["id"],
                            "location_name": loc["name"],
                            "country_code": (loc.get("country") or {}).get("code"),
                            "city": loc.get("locality"),
                            "parameter": param.get("name"),
                            "parameter_display": param.get("displayName"),
                            "units": param.get("units"),
                            "date_from": (period.get("datetimeFrom") or {}).get("utc"),
                            "date_to": (period.get("datetimeTo") or {}).get("utc"),
                            "avg_value": summary.get("avg"),
                            "min_value": summary.get("min"),
                            "max_value": summary.get("max"),
                        }
                except (requests.exceptions.RequestException, RuntimeError) as e:
                    # Skip failed sensors instead of crashing
                    logger.warning(f"Skipping sensor {sensor['id']}: {e}")
                    continue

    logger.info(f"Processed {sensor_count} sensors total")


# ── Main ──


def main():
    """Run the full ingestion pipeline."""
    api_key = os.getenv("OPENAQ_API_KEY")
    if not api_key:
        logger.error("OPENAQ_API_KEY not found. Check your .env file.")
        return

    countries = [c.strip() for c in os.getenv("PIPELINE_COUNTRIES", "80").split(",")]
    days_back = int(os.getenv("PIPELINE_DAYS_BACK", "7"))

    logger.info(f"Starting pipeline for countries: {countries}")
    client = OpenAQClient(api_key)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    pipeline = dlt.pipeline(
        pipeline_name="openaq_pipeline",
        destination=dlt.destinations.duckdb(DB_PATH),
        dataset_name="air_quality",
    )

    logger.info("Loading locations and sensors...")
    load_info = pipeline.run([locations_resource(client, countries), sensors_resource(client, countries)])
    logger.info(f"Locations/sensors loaded: {load_info}")

    logger.info("Loading measurements...")
    load_info = pipeline.run(measurements_resource(client, countries, days_back))
    logger.info(f"Measurements loaded: {load_info}")

    logger.info("Pipeline completed successfully!")


if __name__ == "__main__":
    main()
