# daleel (دليل) — Claude Code Instructions

## Project Overview

CLI tool that scrapes Saudi Arabia business directories using Google Places API (New) v1.

- `daleel.py` — CLI entry point (argparse), run via `python daleel.py --region "Riyadh" --target 5000`
- `config.py` — Global settings, API configuration, constants
- `regions.py` — All 13 Saudi region profiles with city bounds, populations, grid steps
- `queries.py` — 3-tier search query lists (Tier 1: common, Tier 2: retail/services, Tier 3: niche)
- `resolver.py` — Fuzzy region/city name matching (handles Arabic, English, misspellings)
- `planner.py` — Dynamic scrape strategy based on target count
- `estimator.py` — Pre-run cost calculator ($32/1000 API calls)
- `grid.py` — Center-first grid point generator using lat/lng bounds
- `searcher.py` — Google Places API calls with rate limiting and retries
- `dedup.py` — Deduplication by place_id
- `checkpoint.py` — JSON checkpoint save/load for resume capability
- `exporter.py` — Excel export with openpyxl (4 sheets: All, By City, By Category, Metadata)

## Development with Docker

All commands run through Docker via the Makefile.

```bash
make build                                        # Build image
make run ARGS='--region Riyadh --target 5000'     # Run scraper
make dry-run ARGS='--region Riyadh --target 5000' # Cost estimate only
make test                                         # Run tests
make lint                                         # Run ruff
make shell                                        # Interactive shell
```

## Key Technical Details

- API: Google Places API (New) v1 — POST to `https://places.googleapis.com/v1/places:searchText`
- Auth: API key via `X-Goog-Api-Key` header (from `GOOGLE_MAPS_API_KEY` env var)
- Field mask: Set via `X-Goog-FieldMask` header (see searcher.py)
- Rate limiting: 0.1-0.2s between requests, exponential backoff on 429
- Dedup key: `places.id` (Google's unique place identifier)
- Checkpoint format: JSON at `data/checkpoints/{region}_checkpoint.json`
- Output: Excel at `data/output/{region}_{target}_businesses.xlsx`

## Conventions

- Type hints on all function signatures
- Docstrings on all public functions
- Use `logging` module (not print) for operational messages — print only for user-facing CLI output
- All coordinates use (latitude, longitude) order
- Region keys use snake_case: `Riyadh_Region`
