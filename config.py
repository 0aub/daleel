"""Global configuration and settings for daleel."""

import os
from dataclasses import dataclass

__all__ = ["Config", "load_config"]


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment."""

    api_key: str
    language: str = "ar"
    request_delay: float = 0.15
    max_retries: int = 5
    checkpoint_dir: str = "data/checkpoints"
    raw_dir: str = "data/raw"
    output_dir: str = "data/output"

    # Google Places API (New) v1
    api_base_url: str = "https://places.googleapis.com/v1/places:searchText"
    cost_per_1000_calls: float = 32.0
    max_results_per_call: int = 20

    # Field mask for API requests
    field_mask: str = (
        "places.id,places.displayName,places.formattedAddress,"
        "places.nationalPhoneNumber,places.internationalPhoneNumber,"
        "places.location,places.rating,places.userRatingCount,"
        "places.types,places.websiteUri,places.googleMapsUri,"
        "places.businessStatus,places.currentOpeningHours,"
        "places.primaryType,places.primaryTypeDisplayName"
    )


def load_config(api_key: str | None = None, language: str = "ar") -> Config:
    """Load configuration from environment and CLI arguments."""
    key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not key:
        raise ValueError(
            "API key required. Set GOOGLE_MAPS_API_KEY environment variable "
            "or pass --api-key argument."
        )
    return Config(api_key=key, language=language)
