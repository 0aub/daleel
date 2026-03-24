"""daleel (دليل) — Saudi Arabia Business Directory Scraper.

CLI entry point that orchestrates the full scraping pipeline:
resolve region → plan strategy → estimate cost → confirm → scrape → export.
"""

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime

from dotenv import load_dotenv

from checkpoint import CheckpointData, find_latest_checkpoint, load_checkpoint, save_checkpoint
from config import load_config
from dedup import Deduplicator
from estimator import display_estimate, estimate_cost
from exporter import export_excel
from master_db import MasterDB
from planner import create_plan
from regions import REGIONS
from resolver import resolve_input
from searcher import Place, search

logger = logging.getLogger("daleel")


def main() -> None:
    load_dotenv()
    args = parse_args()
    setup_logging(verbose=args.verbose)

    if args.list_regions:
        print_regions()
        return

    if args.resume:
        run_resume(args)
        return

    if not args.region or not args.target:
        print("ERROR: --region and --target are required. Use --help for usage.")
        sys.exit(1)

    run_scrape(args)


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


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def print_regions() -> None:
    """Print all available regions and cities."""
    print("\nAvailable regions and cities:")
    print("=" * 50)
    for _key, region in REGIONS.items():
        total_pop = sum(c["population"] for c in region["cities"].values())
        print(f"\n  {region['name_en']} ({region['name_ar']})")
        print(f"  Aliases: {', '.join(region['aliases'])}")
        print(f"  Total population: {total_pop:,}")
        print("  Cities:")
        for city_name, city in sorted(region["cities"].items(), key=lambda x: -x[1]["population"]):
            print(f"    - {city_name} ({city['name_ar']}) — pop. {city['population']:,}")
    print()


def run_scrape(
    args: argparse.Namespace,
    resume_checkpoint: CheckpointData | None = None,
) -> None:
    """Main scraping pipeline.

    Args:
        args: CLI arguments.
        resume_checkpoint: If resuming, the loaded checkpoint data.
    """
    # Resolve targets
    targets = resolve_input(args.region)
    print(f"\nResolved {len(targets)} target(s):")
    for t in targets:
        cities = ", ".join(t.city_names) if t.city_names else "all cities"
        print(f"  - {t.region_name}: {cities}")

    # Load config
    config = load_config(api_key=args.api_key, language=args.lang)

    # Load master database of all previously scraped place IDs
    master = MasterDB()
    if master.total_count > 0:
        print(f"\nMaster DB: {master.total_count:,} businesses from previous runs (will be skipped)")

    # Restore state from checkpoint if resuming
    all_places: list[Place] = []
    dedup = Deduplicator()
    dedup.load_ids(master.ids)  # Pre-load master IDs so they're treated as duplicates
    total_api_calls = 0

    if resume_checkpoint:
        dedup.load_ids(set(resume_checkpoint.seen_place_ids))
        total_api_calls = resume_checkpoint.api_calls_made
        print(f"\nResuming: {dedup.count} unique businesses already collected, "
              f"{total_api_calls} API calls made")

    for target in targets:
        region = REGIONS[target.region_key]
        city_filter = target.city_names or None
        cities = city_filter or list(region["cities"].keys())

        # Estimate cost
        total_pop = sum(
            region["cities"][c]["population"] for c in cities if c in region["cities"]
        )
        remaining = max(0, args.target - dedup.count)
        estimate = estimate_cost(total_pop, remaining if resume_checkpoint else args.target)
        display_estimate(estimate, target.region_name, cities)

        if args.dry_run:
            continue

        # Confirm (skip if resuming — already confirmed)
        if not resume_checkpoint:
            response = input("Proceed? [Y/n]: ").strip().lower()
            if response and response != "y":
                print("Aborted.")
                return

        # Create plan
        plan = create_plan(region, args.target, city_filter=city_filter)
        print(f"\nPlan: {plan.total_api_calls} API calls across {len(plan.cities)} cities")

        # Initialize or restore checkpoint
        if resume_checkpoint and resume_checkpoint.region_key == target.region_key:
            cp = resume_checkpoint
        else:
            cp = CheckpointData(
                region_key=target.region_key,
                target=args.target,
                started_at=datetime.now(UTC).isoformat(),
                last_updated="",
                results_file=os.path.join(config.raw_dir, f"{target.region_key}_raw.jsonl"),
            )
        os.makedirs(config.raw_dir, exist_ok=True)

        # Execute plan
        for task in plan.tasks:
            for grid_point in task.grid_points:
                if dedup.count >= args.target:
                    print(f"\nTarget reached! {dedup.count} unique businesses collected.")
                    break

                for query in task.queries:
                    if dedup.count >= args.target:
                        break

                    task_key = {"city": task.city_name, "grid": list(grid_point), "query": query}
                    if task_key in cp.completed_tasks:
                        continue

                    result = search(
                        config, query,
                        latitude=grid_point[0],
                        longitude=grid_point[1],
                        radius=float(region["cities"][task.city_name]["radius"]),
                        region_name=target.region_name,
                        city_name=task.city_name,
                    )

                    new_places = dedup.add_batch(result.places)
                    all_places.extend(new_places)
                    total_api_calls += result.api_calls

                    # Append raw results
                    with open(cp.results_file, "a", encoding="utf-8") as f:
                        for place in new_places:
                            f.write(json.dumps({
                                "place_id": place.place_id,
                                "name": place.name,
                                "address": place.address,
                                "latitude": place.latitude,
                                "longitude": place.longitude,
                            }, ensure_ascii=False) + "\n")

                    # Update checkpoint
                    cp.completed_tasks.append(task_key)
                    cp.raw_count += len(result.places)
                    cp.unique_count = dedup.count
                    cp.api_calls_made = total_api_calls
                    cp.seen_place_ids = list(dedup.seen_ids)
                    save_checkpoint(cp, config.checkpoint_dir)

                    logger.info(
                        "[%s] %s @ (%.4f, %.4f) — %d new, %d total unique",
                        task.city_name, query, grid_point[0], grid_point[1],
                        len(new_places), dedup.count,
                    )

            if dedup.count >= args.target:
                break
        if dedup.count >= args.target:
            break

    if args.dry_run:
        return

    # Save new IDs to master database
    for place in all_places:
        master.add(place.place_id)
    master.save()

    # Export
    if all_places:
        output_path = args.output or os.path.join(
            config.output_dir, f"{targets[0].region_key}_{args.target}_businesses.xlsx"
        )
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        export_excel(all_places, output_path, metadata={
            "Target": args.target,
            "New Businesses": len(all_places),
            "Total in Master DB": master.total_count,
            "Skipped (duplicates)": master.total_count - len(all_places),
            "API Calls": total_api_calls,
            "Estimated Cost": f"${total_api_calls * 0.032:.2f}",
            "Regions": ", ".join(t.region_name for t in targets),
        })
        print(f"\nExported {len(all_places)} new businesses to {output_path}")
        print(f"Master DB: {master.total_count:,} total unique businesses across all runs")
    else:
        print("\nNo new businesses collected.")


def run_resume(args: argparse.Namespace) -> None:
    """Resume from the latest checkpoint."""
    cp_path = find_latest_checkpoint()
    if not cp_path:
        print("No checkpoint found. Start a new scrape with --region and --target.")
        sys.exit(1)

    cp = load_checkpoint(cp_path)
    print(f"\nFound checkpoint: {cp.unique_count}/{cp.target} unique ({cp.api_calls_made} API calls)")
    response = input("Resume? [Y/n]: ").strip().lower()
    if response and response != "y":
        print("Aborted.")
        return

    # Resume with checkpoint state restored
    args.region = cp.region_key
    args.target = cp.target
    args.dry_run = False
    run_scrape(args, resume_checkpoint=cp)


if __name__ == "__main__":
    main()
