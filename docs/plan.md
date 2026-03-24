# daleel (دليل) — Saudi Arabia Business Directory Scraper

## Objective

Build a **single, dynamic Python CLI tool** called **daleel** that:

1. Takes a **region name** (or city name) and a **target business count** as input
2. **Calculates** the estimated cost and API calls needed
3. **Asks the user to confirm** before spending any money
4. **Runs the scraper** and stops once the target is reached
5. **Exports** a professionally formatted `.xlsx` file

---

## 1. Google Cloud Setup (User Must Do Before Running)

### APIs to Enable

In **Google Cloud Console → APIs & Services → Library**, enable:

1. **Places API (New)** — the newer version, NOT the legacy "Places API"
2. **Geocoding API** — optional, for reverse-geocoding neighborhoods

### Create an API Key

1. **APIs & Services → Credentials → Create Credentials → API Key**
2. Restrict to the APIs above
3. Set as environment variable: `export GOOGLE_MAPS_API_KEY="your_key_here"`

### Set a Billing Alert

Go to **Billing → Budgets & Alerts** and set an alert at $50 and $200. Google gives $200/month free credit for new projects.

---

## 2. CLI Interface

### Usage

```bash
# Basic usage
python daleel.py --region "Riyadh" --target 5000

# With API key inline
python daleel.py --region "Qaseem" --target 3000 --api-key "AIza..."

# Multiple regions
python daleel.py --region "Riyadh,Jeddah" --target 10000

# Specific city within a region
python daleel.py --region "Buraidah" --target 2000

# All of Saudi Arabia
python daleel.py --region "all" --target 50000

# Resume an interrupted run
python daleel.py --resume

# List available regions
python daleel.py --list-regions

# Dry run (show cost estimate only, don't scrape)
python daleel.py --region "Riyadh" --target 5000 --dry-run
```

### Arguments

| Argument | Required | Description |
|---|---|---|
| `--region` | Yes | Region name, city name, comma-separated list, or "all" |
| `--target` | Yes | Target number of unique businesses to collect |
| `--api-key` | No | Google API key (can also use env var `GOOGLE_MAPS_API_KEY`) |
| `--output` | No | Output filename (default: `{region}_{target}_businesses.xlsx`) |
| `--resume` | No | Resume the last interrupted run from checkpoint |
| `--dry-run` | No | Only show cost estimate, don't make API calls |
| `--list-regions` | No | Print all available regions and cities |
| `--lang` | No | Primary language: `ar` (default), `en`, or `both` |

---

## 3. Pre-Run Cost Estimator

Before making ANY API calls, the script MUST display a cost estimate and ask for confirmation.

### Estimation Logic

```python
def estimate_cost(region_profile: dict, target_count: int) -> dict:
    """
    Calculate estimated API calls and cost based on region and target.
    
    Key assumptions (based on Google Places API behavior in Saudi Arabia):
    - Average unique results per API call in dense urban areas: ~8-12
    - Average unique results per API call in sparse areas: ~4-6
    - Deduplication ratio (raw → unique): ~55-65% are unique
    - Cost per 1,000 Text Search (New) calls: $32
    """
    
    # Determine city density tier
    total_population = sum(city["population"] for city in region_profile["cities"].values())
    
    if total_population > 2_000_000:  # Mega city (Riyadh, Jeddah)
        avg_unique_per_call = 10
        dedup_ratio = 0.55
    elif total_population > 500_000:  # Large city
        avg_unique_per_call = 8
        dedup_ratio = 0.60
    elif total_population > 100_000:  # Medium city
        avg_unique_per_call = 6
        dedup_ratio = 0.65
    else:  # Small city/town
        avg_unique_per_call = 5
        dedup_ratio = 0.70
    
    # How many raw results do we need to get `target_count` unique?
    raw_results_needed = int(target_count / dedup_ratio)
    
    # How many API calls to get that many raw results?
    # Each call returns up to 20 results, but avg is lower
    avg_results_per_call = 14  # typical for text search
    estimated_api_calls = int(raw_results_needed / avg_results_per_call)
    
    # Add 15% buffer for empty/low-result calls
    estimated_api_calls = int(estimated_api_calls * 1.15)
    
    # Cost
    cost_per_call = 0.032  # $32 per 1,000
    estimated_cost = estimated_api_calls * cost_per_call
    
    # Time estimate (0.15s avg per call + processing)
    estimated_minutes = (estimated_api_calls * 0.2) / 60
    
    return {
        "target_unique": target_count,
        "estimated_raw_results": raw_results_needed,
        "estimated_api_calls": estimated_api_calls,
        "estimated_cost_usd": round(estimated_cost, 2),
        "estimated_time_minutes": round(estimated_minutes, 1),
        "within_free_tier": estimated_cost <= 200
    }
```

### Pre-Run Display

```
╔══════════════════════════════════════════════════════════╗
║   daleel (دليل) — Cost Estimate                        ║
╠══════════════════════════════════════════════════════════╣
║                                                         ║
║   Region:          Riyadh                               ║
║   Target:          5,000 unique businesses               ║
║                                                         ║
║   Estimated API calls:    ~650                          ║
║   Estimated cost:         ~$20.80                       ║
║   Estimated time:         ~2.2 minutes                  ║
║   Free tier ($200/mo):    ✅ Within free tier            ║
║                                                         ║
║   Cities to cover:                                      ║
║     • Riyadh (main) — 35 grid points, Tier 1+2 queries ║
║     • Kharj — 4 grid points, Tier 1 queries            ║
║                                                         ║
║   Strategy: Will cover high-density commercial areas    ║
║   first, expanding outward until target is reached.     ║
║                                                         ║
╚══════════════════════════════════════════════════════════╝

Proceed? [Y/n]: 
```

---

## 4. Dynamic Grid & Query Strategy

The script should NOT use a fixed grid. Instead, it dynamically decides how many grid points and which query tiers to use based on the target count.

### Strategy Selection Algorithm

```python
def plan_scrape(region_profile: dict, target_count: int) -> ScrapePlan:
    """
    Dynamically determine grid density and query depth based on target.
    
    Strategy:
    - Start from city centers (highest commercial density)
    - Use concentric expansion: center first, then outward rings
    - Begin with Tier 1 queries (most results per query)
    - Add Tier 2 if needed, then Tier 3
    - Stop planning once estimated yield >= target
    """
    
    plan = ScrapePlan()
    estimated_yield = 0
    
    # Sort cities by population (largest first)
    cities_sorted = sorted(
        region_profile["cities"].items(),
        key=lambda x: x[1]["population"],
        reverse=True
    )
    
    for city_name, city_config in cities_sorted:
        if estimated_yield >= target_count * 1.2:  # 20% buffer
            break
        
        # Phase 1: Core grid + Tier 1 queries
        core_grid = generate_grid(
            city_config["bounds"],
            step_km=city_config["base_grid_step_km"],
            strategy="center_first"  # Start from center, expand outward
        )
        
        tier1_yield = len(core_grid) * len(TIER_1_QUERIES) * avg_unique_per_call
        plan.add(city_name, core_grid, TIER_1_QUERIES)
        estimated_yield += tier1_yield
        
        if estimated_yield >= target_count * 1.2:
            break
        
        # Phase 2: Same grid + Tier 2 queries
        tier2_yield = len(core_grid) * len(TIER_2_QUERIES) * avg_unique_per_call * 0.5
        # 0.5 factor because Tier 2 queries have more overlap with Tier 1
        plan.add(city_name, core_grid, TIER_2_QUERIES)
        estimated_yield += tier2_yield
        
        if estimated_yield >= target_count * 1.2:
            break
        
        # Phase 3: Denser grid + Tier 1 (fill gaps)
        dense_grid = generate_grid(
            city_config["bounds"],
            step_km=city_config["base_grid_step_km"] * 0.6,  # 60% of original spacing
            strategy="fill_gaps",
            exclude=core_grid
        )
        plan.add(city_name, dense_grid, TIER_1_QUERIES)
        estimated_yield += len(dense_grid) * len(TIER_1_QUERIES) * avg_unique_per_call * 0.3
        # 0.3 factor because gap-filling finds fewer new results
        
        if estimated_yield >= target_count * 1.2:
            break
        
        # Phase 4: Dense grid + Tier 3 (niche categories)
        plan.add(city_name, core_grid, TIER_3_QUERIES)
        estimated_yield += len(core_grid) * len(TIER_3_QUERIES) * avg_unique_per_call * 0.3
    
    return plan
```

### Center-First Grid Generation

Instead of a uniform grid, generate points starting from the city center and spiraling outward:

```python
def generate_grid(bounds: dict, step_km: float, strategy: str = "center_first") -> list:
    """
    Generate grid points starting from city center, expanding outward.
    This ensures we hit the most business-dense areas first.
    """
    center_lat = (bounds["north"] + bounds["south"]) / 2
    center_lng = (bounds["east"] + bounds["west"]) / 2
    
    # Convert km to degrees (approximate at Saudi latitude)
    lat_step = step_km / 111.0  # 1° lat ≈ 111 km
    lng_step = step_km / (111.0 * cos(radians(center_lat)))
    
    # Generate all grid points
    points = []
    lat = bounds["south"]
    while lat <= bounds["north"]:
        lng = bounds["west"]
        while lng <= bounds["east"]:
            points.append((lat, lng))
            lng += lng_step
        lat += lat_step
    
    if strategy == "center_first":
        # Sort by distance from center (nearest first)
        points.sort(key=lambda p: (p[0]-center_lat)**2 + (p[1]-center_lng)**2)
    
    return points
```

### Runtime Stop Condition

```python
# During scraping, check after every API call:
if unique_count >= target_count:
    print(f"\n✅ Target reached! {unique_count} unique businesses collected.")
    print("Finishing up and exporting...")
    break
```

This is critical — the script MUST stop making API calls once the target is hit. Do not continue just because there are more grid points or queries remaining.

---

## 5. Region Profiles Database

Store all region data in `regions.py`. The script uses this to look up any region or city the user types.

### Lookup Logic

The `--region` argument should be flexible. The script must match against:
1. Exact region name (e.g., "Riyadh Region")
2. Short region name (e.g., "Riyadh")  
3. City name within a region (e.g., "Buraidah" → resolves to Qaseem Region, but only scrapes Buraidah)
4. Arabic name (e.g., "الرياض", "القصيم")
5. Case-insensitive
6. Common misspellings (e.g., "Jeddah" / "Jiddah" / "Jedda")

```python
# Each region profile structure:
REGIONS = {
    "Riyadh_Region": {
        "name_en": "Riyadh Region",
        "name_ar": "منطقة الرياض",
        "aliases": ["riyadh", "الرياض", "riyad"],
        "cities": {
            "Riyadh": {
                "name_ar": "الرياض",
                "aliases": ["riyadh city", "riad"],
                "population": 7_500_000,
                "bounds": {"north": 24.85, "south": 24.55, "west": 46.55, "east": 46.85},
                "base_grid_step_km": 1.5,
                "radius": 1500,
            },
            "Kharj": {
                "name_ar": "الخرج",
                "aliases": ["al kharj", "alkharj"],
                "population": 425_000,
                "bounds": {"north": 24.18, "south": 24.12, "west": 47.28, "east": 47.35},
                "base_grid_step_km": 2.5,
                "radius": 2500,
            },
            "Dawadmi": {
                "name_ar": "الدوادمي",
                "aliases": ["al dawadmi", "dawadmi"],
                "population": 75_000,
                "bounds": {"north": 24.52, "south": 24.48, "west": 44.37, "east": 44.42},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            },
            "Majmaah": {
                "name_ar": "المجمعة",
                "aliases": ["al majmaah", "majma"],
                "population": 60_000,
                "bounds": {"north": 25.92, "south": 25.88, "west": 45.33, "east": 45.38},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            },
            "Afif": {
                "name_ar": "عفيف",
                "aliases": [],
                "population": 45_000,
                "bounds": {"north": 23.93, "south": 23.89, "west": 42.90, "east": 42.95},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            },
            "Wadi_Aldawaser": {
                "name_ar": "وادي الدواسر",
                "aliases": ["wadi dawasir"],
                "population": 50_000,
                "bounds": {"north": 20.48, "south": 20.43, "west": 44.82, "east": 44.88},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            },
            "Shaqra": {
                "name_ar": "شقراء",
                "aliases": [],
                "population": 35_000,
                "bounds": {"north": 25.26, "south": 25.22, "west": 45.24, "east": 45.29},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            },
            "Hotat_Bani_Tamim": {
                "name_ar": "حوطة بني تميم",
                "aliases": ["hotat tamim"],
                "population": 30_000,
                "bounds": {"north": 23.55, "south": 23.51, "west": 46.84, "east": 46.89},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            }
        }
    },

    "Makkah_Region": {
        "name_en": "Makkah Region",
        "name_ar": "منطقة مكة المكرمة",
        "aliases": ["makkah", "mecca", "مكة", "مكة المكرمة"],
        "cities": {
            "Jeddah": {
                "name_ar": "جدة",
                "aliases": ["jiddah", "jedda", "jeda", "جده"],
                "population": 4_700_000,
                "bounds": {"north": 21.72, "south": 21.38, "west": 39.10, "east": 39.28},
                "base_grid_step_km": 1.5,
                "radius": 1500,
            },
            "Makkah": {
                "name_ar": "مكة المكرمة",
                "aliases": ["mecca", "makkah city"],
                "population": 2_000_000,
                "bounds": {"north": 21.46, "south": 21.38, "west": 39.79, "east": 39.90},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Taif": {
                "name_ar": "الطائف",
                "aliases": ["al taif", "altaif", "الطايف"],
                "population": 700_000,
                "bounds": {"north": 21.30, "south": 21.23, "west": 40.48, "east": 40.55},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Rabigh": {
                "name_ar": "رابغ",
                "aliases": [],
                "population": 70_000,
                "bounds": {"north": 22.82, "south": 22.77, "west": 38.96, "east": 39.01},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            },
            "Al_Qunfudhah": {
                "name_ar": "القنفذة",
                "aliases": ["qunfudhah", "kunfuda"],
                "population": 60_000,
                "bounds": {"north": 19.15, "south": 19.11, "west": 41.07, "east": 41.12},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            }
        }
    },

    "Madinah_Region": {
        "name_en": "Madinah Region",
        "name_ar": "منطقة المدينة المنورة",
        "aliases": ["madinah", "medina", "المدينة", "المدينة المنورة"],
        "cities": {
            "Madinah": {
                "name_ar": "المدينة المنورة",
                "aliases": ["medina", "madinah city", "al madinah"],
                "population": 1_500_000,
                "bounds": {"north": 24.52, "south": 24.40, "west": 39.55, "east": 39.70},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Yanbu": {
                "name_ar": "ينبع",
                "aliases": ["yanbu al bahr"],
                "population": 300_000,
                "bounds": {"north": 24.12, "south": 24.05, "west": 38.03, "east": 38.10},
                "base_grid_step_km": 2.5,
                "radius": 2500,
            },
            "AlUla": {
                "name_ar": "العلا",
                "aliases": ["al ula", "alola"],
                "population": 40_000,
                "bounds": {"north": 26.65, "south": 26.60, "west": 37.90, "east": 37.95},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            }
        }
    },

    "Eastern_Region": {
        "name_en": "Eastern Region",
        "name_ar": "المنطقة الشرقية",
        "aliases": ["eastern", "الشرقية", "sharqiyah"],
        "cities": {
            "Dammam": {
                "name_ar": "الدمام",
                "aliases": ["aldammam"],
                "population": 1_300_000,
                "bounds": {"north": 26.48, "south": 26.38, "west": 50.05, "east": 50.15},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Khobar": {
                "name_ar": "الخبر",
                "aliases": ["al khobar", "alkhobar"],
                "population": 600_000,
                "bounds": {"north": 26.33, "south": 26.26, "west": 50.17, "east": 50.24},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Dhahran": {
                "name_ar": "الظهران",
                "aliases": ["al dhahran"],
                "population": 150_000,
                "bounds": {"north": 26.32, "south": 26.27, "west": 50.10, "east": 50.15},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Jubail": {
                "name_ar": "الجبيل",
                "aliases": ["al jubail"],
                "population": 400_000,
                "bounds": {"north": 27.02, "south": 26.94, "west": 49.62, "east": 49.70},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Hofuf": {
                "name_ar": "الهفوف",
                "aliases": ["al hofuf", "al ahsa", "الأحساء", "الاحساء", "ahsa"],
                "population": 700_000,
                "bounds": {"north": 25.42, "south": 25.32, "west": 49.55, "east": 49.65},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Qatif": {
                "name_ar": "القطيف",
                "aliases": ["al qatif"],
                "population": 200_000,
                "bounds": {"north": 26.57, "south": 26.51, "west": 50.00, "east": 50.05},
                "base_grid_step_km": 2.5,
                "radius": 2500,
            }
        }
    },

    "Qaseem_Region": {
        "name_en": "Qaseem Region",
        "name_ar": "منطقة القصيم",
        "aliases": ["qaseem", "qassim", "القصيم", "قصيم"],
        "cities": {
            "Buraidah": {
                "name_ar": "بريدة",
                "aliases": ["buraydah", "buraidah city"],
                "population": 750_000,
                "bounds": {"north": 26.40, "south": 26.28, "west": 43.92, "east": 44.05},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Unaizah": {
                "name_ar": "عنيزة",
                "aliases": ["onaizah", "unayzah"],
                "population": 180_000,
                "bounds": {"north": 26.12, "south": 26.06, "west": 43.97, "east": 44.03},
                "base_grid_step_km": 2.5,
                "radius": 2500,
            },
            "Ar_Rass": {
                "name_ar": "الرس",
                "aliases": ["al rass", "rass"],
                "population": 130_000,
                "bounds": {"north": 25.88, "south": 25.84, "west": 43.48, "east": 43.53},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            },
            "Al_Mithnab": {
                "name_ar": "المذنب",
                "aliases": ["mithnab"],
                "population": 40_000,
                "bounds": {"north": 25.48, "south": 25.44, "west": 44.24, "east": 44.29},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            },
            "Al_Bukayriyah": {
                "name_ar": "البكيرية",
                "aliases": ["bukayriyah"],
                "population": 35_000,
                "bounds": {"north": 26.15, "south": 26.11, "west": 43.76, "east": 43.81},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            }
        }
    },

    "Aseer_Region": {
        "name_en": "Aseer Region",
        "name_ar": "منطقة عسير",
        "aliases": ["aseer", "asir", "عسير"],
        "cities": {
            "Abha": {
                "name_ar": "أبها",
                "aliases": [],
                "population": 500_000,
                "bounds": {"north": 18.25, "south": 18.19, "west": 42.48, "east": 42.54},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Khamis_Mushait": {
                "name_ar": "خميس مشيط",
                "aliases": ["khamis mushait", "khamis"],
                "population": 600_000,
                "bounds": {"north": 18.33, "south": 18.27, "west": 42.70, "east": 42.77},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Bisha": {
                "name_ar": "بيشة",
                "aliases": [],
                "population": 100_000,
                "bounds": {"north": 20.02, "south": 19.97, "west": 42.58, "east": 42.64},
                "base_grid_step_km": 2.5,
                "radius": 2500,
            },
            "Namas": {
                "name_ar": "النماص",
                "aliases": ["al namas"],
                "population": 35_000,
                "bounds": {"north": 19.15, "south": 19.11, "west": 42.12, "east": 42.17},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            }
        }
    },

    "Tabuk_Region": {
        "name_en": "Tabuk Region",
        "name_ar": "منطقة تبوك",
        "aliases": ["tabuk", "تبوك", "tabook"],
        "cities": {
            "Tabuk": {
                "name_ar": "تبوك",
                "aliases": ["tabuk city"],
                "population": 600_000,
                "bounds": {"north": 28.42, "south": 28.35, "west": 36.52, "east": 36.62},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Umluj": {
                "name_ar": "أملج",
                "aliases": [],
                "population": 30_000,
                "bounds": {"north": 25.07, "south": 25.03, "west": 37.25, "east": 37.30},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            },
            "Duba": {
                "name_ar": "ضباء",
                "aliases": ["dhaba"],
                "population": 25_000,
                "bounds": {"north": 27.37, "south": 27.33, "west": 36.51, "east": 36.56},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            }
        }
    },

    "Hail_Region": {
        "name_en": "Hail Region",
        "name_ar": "منطقة حائل",
        "aliases": ["hail", "ha'il", "حائل", "حايل"],
        "cities": {
            "Hail": {
                "name_ar": "حائل",
                "aliases": ["hail city"],
                "population": 450_000,
                "bounds": {"north": 27.56, "south": 27.48, "west": 41.66, "east": 41.75},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Baqaa": {
                "name_ar": "بقعاء",
                "aliases": [],
                "population": 30_000,
                "bounds": {"north": 27.92, "south": 27.88, "west": 42.38, "east": 42.43},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            }
        }
    },

    "Northern_Borders_Region": {
        "name_en": "Northern Borders Region",
        "name_ar": "منطقة الحدود الشمالية",
        "aliases": ["northern borders", "الحدود الشمالية", "الشمالية"],
        "cities": {
            "Arar": {
                "name_ar": "عرعر",
                "aliases": [],
                "population": 150_000,
                "bounds": {"north": 31.02, "south": 30.93, "west": 40.14, "east": 40.26},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Rafha": {
                "name_ar": "رفحاء",
                "aliases": [],
                "population": 70_000,
                "bounds": {"north": 29.65, "south": 29.59, "west": 43.46, "east": 43.55},
                "base_grid_step_km": 2.5,
                "radius": 2500,
            },
            "Turaif": {
                "name_ar": "طريف",
                "aliases": [],
                "population": 40_000,
                "bounds": {"north": 31.70, "south": 31.65, "west": 38.63, "east": 38.70},
                "base_grid_step_km": 2.5,
                "radius": 2500,
            }
        }
    },

    "Jazan_Region": {
        "name_en": "Jazan Region",
        "name_ar": "منطقة جازان",
        "aliases": ["jazan", "jizan", "جازان", "جيزان"],
        "cities": {
            "Jazan": {
                "name_ar": "جازان",
                "aliases": ["jizan city"],
                "population": 200_000,
                "bounds": {"north": 16.92, "south": 16.86, "west": 42.53, "east": 42.60},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Sabya": {
                "name_ar": "صبيا",
                "aliases": [],
                "population": 80_000,
                "bounds": {"north": 17.17, "south": 17.13, "west": 42.62, "east": 42.67},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            },
            "Abu_Arish": {
                "name_ar": "أبو عريش",
                "aliases": [],
                "population": 60_000,
                "bounds": {"north": 16.98, "south": 16.94, "west": 42.78, "east": 42.83},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            }
        }
    },

    "Najran_Region": {
        "name_en": "Najran Region",
        "name_ar": "منطقة نجران",
        "aliases": ["najran", "نجران"],
        "cities": {
            "Najran": {
                "name_ar": "نجران",
                "aliases": ["najran city"],
                "population": 350_000,
                "bounds": {"north": 17.53, "south": 17.47, "west": 44.20, "east": 44.28},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Sharurah": {
                "name_ar": "شرورة",
                "aliases": [],
                "population": 80_000,
                "bounds": {"north": 17.50, "south": 17.46, "west": 47.10, "east": 47.15},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            }
        }
    },

    "AlBaha_Region": {
        "name_en": "Al Baha Region",
        "name_ar": "منطقة الباحة",
        "aliases": ["al baha", "baha", "الباحة"],
        "cities": {
            "Al_Baha": {
                "name_ar": "الباحة",
                "aliases": ["baha city"],
                "population": 100_000,
                "bounds": {"north": 20.02, "south": 19.98, "west": 41.45, "east": 41.50},
                "base_grid_step_km": 2.5,
                "radius": 2500,
            },
            "Baljurashi": {
                "name_ar": "بلجرشي",
                "aliases": [],
                "population": 60_000,
                "bounds": {"north": 19.87, "south": 19.83, "west": 41.60, "east": 41.65},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            }
        }
    },

    "AlJawf_Region": {
        "name_en": "Al Jawf Region",
        "name_ar": "منطقة الجوف",
        "aliases": ["al jawf", "jawf", "الجوف"],
        "cities": {
            "Sakakah": {
                "name_ar": "سكاكا",
                "aliases": [],
                "population": 200_000,
                "bounds": {"north": 29.99, "south": 29.93, "west": 40.17, "east": 40.24},
                "base_grid_step_km": 2.0,
                "radius": 2000,
            },
            "Dumat_Al_Jandal": {
                "name_ar": "دومة الجندل",
                "aliases": ["domat al jandal"],
                "population": 50_000,
                "bounds": {"north": 29.83, "south": 29.79, "west": 39.85, "east": 39.90},
                "base_grid_step_km": 3.0,
                "radius": 3000,
            },
            "Qurayyat": {
                "name_ar": "القريات",
                "aliases": ["gurayat", "al qurayyat"],
                "population": 120_000,
                "bounds": {"north": 31.35, "south": 31.30, "west": 37.33, "east": 37.38},
                "base_grid_step_km": 2.5,
                "radius": 2500,
            }
        }
    }
}
```

---

## 6. Search Query Tiers

```python
TIER_1_QUERIES = [
    # Food (most common, highest density)
    "restaurant", "مطعم",
    "coffee shop", "مقهى", "كافيه",
    "fast food", "shawarma",
    "bakery", "مخبز",
    # Grocery
    "supermarket", "سوبرماركت",
    "grocery", "بقالة", "تموينات",
    # Essentials
    "pharmacy", "صيدلية",
    "gas station", "محطة وقود",
    # Common retail
    "mobile phone shop", "جوالات",
    "clothing store", "ملابس",
]

TIER_2_QUERIES = [
    # More food
    "pizza", "burger", "بوفيه",
    "juice bar", "ice cream",
    "مطبخ", "حلويات",
    # More retail
    "electronics store", "furniture store", "أثاث",
    "jewelry store", "shoe store",
    "perfume shop", "عطور",
    "gift shop", "bookstore",
    "toy store", "sports store",
    "stationery store", "shopping mall",
    # Health & beauty
    "beauty salon", "صالون",
    "barber shop", "حلاق",
    "spa", "optical shop", "نظارات",
    # Services
    "car wash", "auto repair", "ورشة",
    "laundry", "مغسلة",
    "tailoring", "خياط",
]

TIER_3_QUERIES = [
    # Niche retail
    "pet shop", "flower shop", "زهور",
    "computer shop", "watch shop", "ساعات",
    "cosmetics store", "مستحضرات تجميل",
    "baby store", "مستلزمات أطفال",
    "camping store",
    # Niche food
    "seafood restaurant", "مأكولات بحرية",
    "indian restaurant", "chinese restaurant",
    "korean restaurant", "turkish restaurant",
    "مطعم يمني", "مطعم بخاري", "مطعم مندي",
    "chocolate shop", "محمصة",
    # Home & building
    "hardware store", "building materials", "مواد بناء",
    "paint store", "plumbing supply",
    "electrical supply", "garden center",
    "curtain shop", "ستائر", "carpet shop", "سجاد",
    # More services
    "tire shop", "car rental", "car dealership",
    "travel agency", "hotel", "فندق",
    "shipping company", "printing shop", "مطبعة",
    "key locksmith", "مفاتيح",
    # Health
    "clinic", "عيادة", "dental clinic",
    "veterinary", "gym", "نادي رياضي",
]
```

### Tier Assignment Logic

The script dynamically decides which tiers to use based on target vs estimated yield:

```python
def select_tiers(region_profile, target_count):
    """Start with Tier 1 only. Add tiers if estimated yield is insufficient."""
    
    total_grid_points = sum(
        len(generate_grid(c["bounds"], c["base_grid_step_km"]))
        for c in region_profile["cities"].values()
    )
    
    # Tier 1 estimate
    tier1_yield = total_grid_points * len(TIER_1_QUERIES) * 6  # ~6 unique per call after dedup
    if tier1_yield >= target_count * 1.2:
        return TIER_1_QUERIES
    
    # Tier 1+2 estimate
    tier2_yield = tier1_yield + total_grid_points * len(TIER_2_QUERIES) * 3
    if tier2_yield >= target_count * 1.2:
        return TIER_1_QUERIES + TIER_2_QUERIES
    
    # All tiers
    return TIER_1_QUERIES + TIER_2_QUERIES + TIER_3_QUERIES
```

---

## 7. API Request Structure

### Text Search (New) Endpoint

```
POST https://places.googleapis.com/v1/places:searchText
```

**Headers:**
```
Content-Type: application/json
X-Goog-Api-Key: YOUR_API_KEY
X-Goog-FieldMask: places.id,places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.internationalPhoneNumber,places.location,places.rating,places.userRatingCount,places.types,places.websiteUri,places.googleMapsUri,places.businessStatus,places.currentOpeningHours,places.primaryType,places.primaryTypeDisplayName
```

**Body:**
```json
{
  "textQuery": "restaurant",
  "locationBias": {
    "circle": {
      "center": { "latitude": 24.7136, "longitude": 46.6753 },
      "radius": 2000.0
    }
  },
  "languageCode": "ar",
  "maxResultCount": 20
}
```

### Rate Limiting & Retries

- **Delay**: 0.1–0.2s between requests
- **On 429 (rate limit)**: Exponential backoff 1s → 2s → 4s → ... → 60s, max 5 retries
- **On 5xx**: Retry 3 times with 2s delay
- **On network timeout**: Retry 3 times with 5s delay
- **On API key error (403)**: Print message and exit immediately
- **On quota exceeded**: Save checkpoint, print resume command, exit

---

## 8. Data Fields

| Column | Source | Notes |
|---|---|---|
| Place ID | `places.id` | Dedup key |
| Name (Arabic) | `places.displayName.text` | Primary |
| Name (English) | Second pass or auto-detected | Optional |
| Category | `places.primaryTypeDisplayName.text` | |
| All Types | `places.types` | Comma-separated |
| Address | `places.formattedAddress` | |
| Region | Config | e.g., "Riyadh Region" |
| City | Config | e.g., "Riyadh" |
| Latitude | `places.location.latitude` | 6 decimals |
| Longitude | `places.location.longitude` | 6 decimals |
| Phone (Local) | `places.nationalPhoneNumber` | Text format |
| Phone (Intl) | `places.internationalPhoneNumber` | Text format |
| Rating | `places.rating` | 1 decimal |
| Reviews | `places.userRatingCount` | |
| Website | `places.websiteUri` | Hyperlink |
| Google Maps | `places.googleMapsUri` | Hyperlink |
| Status | `places.businessStatus` | |
| Hours | `places.currentOpeningHours.weekdayDescriptions` | Joined text |
| Scraped Date | Timestamp | |

---

## 9. Excel Output

### Filename: `{region}_{target}_businesses.xlsx`

Example: `Riyadh_5000_businesses.xlsx`

**Sheet 1: "All Businesses"**
- All columns from Section 8
- Header: Bold, #1F4E79 background, white text, frozen
- Auto-filter, auto-width, alternate row shading (#F2F2F2)
- Phone as text, links as hyperlinks, Arial font

**Sheet 2: "By City"**
- Business count per city, broken down by category

**Sheet 3: "By Category"**
- Count per primary type, sorted descending

**Sheet 4: "Metadata"**
- Target count, actual count, API calls, cost, runtime, date, queries used

---

## 10. Checkpointing & Resume

### Checkpoint File: `data/checkpoints/{region}_checkpoint.json`

```json
{
    "region": "Riyadh_Region",
    "target": 5000,
    "started_at": "2026-03-24T10:00:00",
    "last_updated": "2026-03-24T10:15:00",
    "completed_tasks": [
        {"city": "Riyadh", "grid": [24.70, 46.65], "query": "restaurant"},
        {"city": "Riyadh", "grid": [24.70, 46.65], "query": "مطعم"}
    ],
    "raw_count": 3200,
    "unique_count": 2100,
    "api_calls_made": 230,
    "results_file": "data/raw/Riyadh_Region_raw.jsonl"
}
```

### Resume Logic

```bash
# Automatic resume — detects existing checkpoint
python daleel.py --region "Riyadh" --target 5000

# Explicit resume of last run
python daleel.py --resume
```

On startup, if a checkpoint exists for the same region+target:
1. Print: "Found existing checkpoint: 2,100/5,000 unique (230 API calls). Resume? [Y/n]"
2. If yes, load checkpoint and skip completed tasks
3. If no, start fresh (archive old checkpoint)

### Raw Results Storage

Use JSONL (one JSON object per line) for raw results — easy to append without loading entire file:

```
{"place_id": "ChIJ...", "name": "...", "address": "...", ...}
{"place_id": "ChIJ...", "name": "...", "address": "...", ...}
```

---

## 11. Script Architecture

```
daleel/
├── daleel.py            # CLI entry point (argparse)
├── config.py            # Global settings, API config
├── regions.py           # All 13 region profiles (Section 5)
├── queries.py           # Tiered query lists (Section 6)
├── resolver.py          # Region/city name resolver (fuzzy matching)
├── planner.py           # Dynamic strategy planner (Section 4)
├── estimator.py         # Cost estimator (Section 3)
├── grid.py              # Center-first grid generator
├── searcher.py          # API calls + rate limiting + retries
├── dedup.py             # Deduplication by place_id
├── checkpoint.py        # Save/load/resume logic
├── exporter.py          # Excel export with formatting
├── requirements.txt     # openpyxl, requests
├── README.md            # Usage instructions
└── data/
    ├── checkpoints/
    ├── raw/
    └── output/
```

### requirements.txt

```
requests>=2.31.0
openpyxl>=3.1.0
```

---

## 12. Full Execution Flow

```
1. Parse CLI arguments (--region, --target, --api-key, etc.)
2. Load or prompt for API key
3. Validate API key with a single test request to the Places API
4. Resolve region name → match to profile(s) in regions.py
5. Run planner: determine grid points, query tiers, estimated calls
6. Run estimator: calculate cost, time, display summary table
7. Ask user: "Proceed? [Y/n]"
8. Check for existing checkpoint → offer resume if found
9. Execute scrape loop:
   For each city (sorted by population, largest first):
     For each grid point (center-first order):
       For each query (Tier 1 first, then 2, then 3):
         - Skip if already in checkpoint
         - Make API call
         - Parse results, append to raw JSONL
         - Update checkpoint
         - Update dedup set (in-memory)
         - Print progress line
         - CHECK: if unique_count >= target → STOP
         - Sleep 0.15s
10. Final deduplication pass (verify)
11. Export Excel file to data/output/
12. Print final summary:
    ✅ daleel: Collected 5,127 unique businesses in Riyadh Region
    📊 API calls: 612 | Cost: ~$19.58 | Time: 2m 14s
    📁 Saved to: data/output/Riyadh_5000_businesses.xlsx
```

---

## 13. Error Messages (User-Friendly)

```
❌ Invalid API key. Please check your key at:
   https://console.cloud.google.com/apis/credentials

❌ Places API (New) is not enabled. Enable it at:
   https://console.cloud.google.com/apis/library/places.googleapis.com

❌ Billing not enabled on your Google Cloud project. 
   Enable at: https://console.cloud.google.com/billing

⚠️  Rate limit hit. Backing off for 4s... (retry 2/5)

⚠️  Daily quota exceeded. Progress saved!
   Resume with: python daleel.py --resume

⚠️  Could not resolve region "Riyahd". Did you mean "Riyadh"?
```
