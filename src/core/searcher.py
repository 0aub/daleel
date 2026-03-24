"""Google Places API (New) v1 search client.

Handles API requests, rate limiting, retries, and error handling.
"""

import logging
import sys
import time
from dataclasses import dataclass

import requests

from config import Config

__all__ = ["Place", "SearchResult", "search"]

logger = logging.getLogger(__name__)


@dataclass
class Place:
    """A business place returned from the API."""

    place_id: str
    name: str
    name_language: str
    address: str
    latitude: float
    longitude: float
    types: list[str]
    primary_type: str
    primary_type_display: str
    phone_local: str
    phone_intl: str
    rating: float | None
    review_count: int
    website: str
    google_maps_url: str
    business_status: str
    hours: str
    region: str
    city: str
    query: str


@dataclass
class SearchResult:
    """Result of a single API search call."""

    places: list[Place]
    api_calls: int


def search(
    config: Config,
    query: str,
    latitude: float,
    longitude: float,
    radius: float,
    region_name: str,
    city_name: str,
) -> SearchResult:
    """Execute a Google Places text search and return parsed results.

    Args:
        config: Application configuration with API key and settings.
        query: Search text (e.g., "restaurant", "مطعم").
        latitude: Center latitude for location bias.
        longitude: Center longitude for location bias.
        radius: Search radius in meters.
        region_name: Region name for tagging results.
        city_name: City name for tagging results.

    Returns:
        SearchResult with parsed places and API call count.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": config.api_key,
        "X-Goog-FieldMask": config.field_mask,
    }

    body = {
        "textQuery": query,
        "locationBias": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": float(radius),
            }
        },
        "languageCode": config.language,
        "maxResultCount": config.max_results_per_call,
    }

    data = _request_with_retry(config, headers, body)
    if data is None:
        return SearchResult(places=[], api_calls=1)

    places = _parse_places(data, region_name, city_name, query)
    return SearchResult(places=places, api_calls=1)


def _request_with_retry(
    config: Config,
    headers: dict,
    body: dict,
) -> dict | None:
    """Make an API request with exponential backoff retry logic."""
    for attempt in range(config.max_retries):
        try:
            time.sleep(config.request_delay)
            response = requests.post(
                config.api_base_url, headers=headers, json=body, timeout=30
            )

            if response.status_code == 200:
                return response.json()

            # Fatal auth errors — stop immediately, no point retrying
            if response.status_code in (401, 403):
                logger.error("API key error (%d): %s", response.status_code, response.text)
                sys.exit(1)

            # Check for API_KEY_INVALID in 400 responses (expired/invalid key)
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    reason = error_data.get("error", {}).get("details", [{}])[0].get("reason", "")
                    if reason == "API_KEY_INVALID":
                        logger.error("API key invalid or expired: %s",
                                     error_data["error"].get("message", ""))
                        sys.exit(1)
                except (ValueError, KeyError, IndexError):
                    pass
                logger.error("Bad request (400): %s", response.text)
                return None

            if response.status_code == 429:
                wait = min(2**attempt, 60)
                logger.warning("Rate limited. Waiting %ds (attempt %d)", wait, attempt + 1)
                time.sleep(wait)
                continue

            if response.status_code >= 500:
                logger.warning("Server error %d. Retrying in 2s...", response.status_code)
                time.sleep(2)
                continue

            logger.error("Unexpected status %d: %s", response.status_code, response.text)
            return None

        except requests.exceptions.Timeout:
            logger.warning("Request timeout (attempt %d)", attempt + 1)
            time.sleep(5)
            continue
        except requests.exceptions.ConnectionError:
            logger.warning("Connection error (attempt %d)", attempt + 1)
            time.sleep(5)
            continue

    logger.error("Max retries (%d) exceeded", config.max_retries)
    return None


def _parse_places(data: dict, region_name: str, city_name: str, query: str) -> list[Place]:
    """Parse API response into Place objects."""
    places = []
    for item in data.get("places", []):
        display_name = item.get("displayName", {})
        location = item.get("location", {})
        primary_type_display = item.get("primaryTypeDisplayName", {})
        hours_list = item.get("currentOpeningHours", {}).get("weekdayDescriptions", [])

        places.append(
            Place(
                place_id=item.get("id", ""),
                name=display_name.get("text", ""),
                name_language=display_name.get("languageCode", ""),
                address=item.get("formattedAddress", ""),
                latitude=location.get("latitude", 0.0),
                longitude=location.get("longitude", 0.0),
                types=item.get("types", []),
                primary_type=item.get("primaryType", ""),
                primary_type_display=primary_type_display.get("text", ""),
                phone_local=item.get("nationalPhoneNumber", ""),
                phone_intl=item.get("internationalPhoneNumber", ""),
                rating=item.get("rating"),
                review_count=item.get("userRatingCount", 0),
                website=item.get("websiteUri", ""),
                google_maps_url=item.get("googleMapsUri", ""),
                business_status=item.get("businessStatus", ""),
                hours=" | ".join(hours_list),
                region=region_name,
                city=city_name,
                query=query,
            )
        )
    return places
