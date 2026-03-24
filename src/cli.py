"""CLI argument parsing for daleel."""

import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="daleel",
        description="daleel (دليل) — Saudi Arabia Business Directory Scraper",
    )
    parser.add_argument("--region", type=str, help="Region/city name, comma-separated, or 'all'")
    parser.add_argument("--target", type=int, help="Target number of unique businesses")
    parser.add_argument("--api-key", type=str, help="Google API key (or set GOOGLE_MAPS_API_KEY)")
    parser.add_argument("--output", type=str, help="Output filename (default: auto-generated)")
    parser.add_argument("--resume", action="store_true", help="Resume last interrupted run")
    parser.add_argument("--dry-run", action="store_true", help="Show cost estimate only")
    parser.add_argument("--list-regions", action="store_true", help="List all regions and cities")
    parser.add_argument("--lang", type=str, default="ar", choices=["ar", "en", "both"],
                        help="Language for results (default: ar)")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()
