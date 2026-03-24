# daleel (دليل) — Claude Code Instructions

## Project Overview

CLI tool that scrapes Saudi Arabia business directories using Google Places API (New) v1.

All source code lives in `src/` with `PYTHONPATH=src`.

```
src/
├── main.py              # Entry point — orchestrates the full pipeline
├── cli.py               # argparse argument definitions
├── config.py            # Global settings, API configuration
├── core/
│   ├── grid.py          # Center-first grid point generator
│   ├── planner.py       # Dynamic scrape strategy
│   ├── searcher.py      # Google Places API calls with retry/rate-limit
│   └── dedup.py         # Deduplication by place_id
├── models/
│   ├── regions.py       # All 13 Saudi region profiles
│   └── queries.py       # 3-tier search query lists
├── export/
│   ├── checkpoint.py    # JSON checkpoint save/load for resume
│   ├── exporter.py      # Excel export (4 sheets, professional styling)
│   └── master_db.py     # Persistent cross-run deduplication database
└── utils/
    ├── resolver.py      # Fuzzy region/city name matching (Arabic/English)
    └── estimator.py     # Pre-run cost calculator
```

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
