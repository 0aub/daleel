# daleel (دليل)

Saudi Arabia business directory scraper using Google Places API (New).

## Features

- Scrapes businesses across all 13 Saudi regions (~50 cities)
- Dynamic grid strategy — starts from city centers, expands outward
- Pre-run cost estimation with user confirmation
- 3-tier query system for comprehensive coverage
- Deduplication by Google Place ID
- Checkpoint & resume for interrupted runs
- Professional Excel export with multiple sheets

## Prerequisites

- Docker & Docker Compose
- Google Cloud API key with **Places API (New)** enabled

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env and add your GOOGLE_MAPS_API_KEY

# 2. Build
make build

# 3. Run
make run ARGS='--region Riyadh --target 5000'
```

## Usage

```bash
# Basic usage
make run ARGS='--region "Riyadh" --target 5000'

# Cost estimate only (no API calls)
make dry-run ARGS='--region "Riyadh" --target 5000'

# Multiple regions
make run ARGS='--region "Riyadh,Jeddah" --target 10000'

# All of Saudi Arabia
make run ARGS='--region all --target 50000'

# Resume interrupted run
make resume

# List available regions
make list-regions
```

## Commands

| Command | Description |
|---|---|
| `make build` | Build Docker image |
| `make run ARGS='...'` | Run scraper with arguments |
| `make dry-run ARGS='...'` | Show cost estimate only |
| `make resume` | Resume last interrupted run |
| `make list-regions` | Show all regions and cities |
| `make test` | Run test suite |
| `make lint` | Run ruff linter |
| `make shell` | Open shell in container |
| `make clean` | Remove data and cache files |

## Output

Results are exported to `data/output/{region}_{target}_businesses.xlsx` with 4 sheets:

1. **All Businesses** — Full data with formatting
2. **By City** — Business count per city by category
3. **By Category** — Count per primary type
4. **Metadata** — Run details (target, actual count, cost, runtime)

## License

GPL-3.0 — see [LICENSE](LICENSE)
