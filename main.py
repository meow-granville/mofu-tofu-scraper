"""Main scheduler for Mofu Tofu scraper."""

import os
import sys
import time
import schedule
from datetime import datetime, timezone

from db import init as db_init
from scraper import run_scraper
from accounts import run_account_discovery
from backfill import run_engagement_backfill
from digest import run_digest


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}")


def run_all() -> None:
    """Run all tasks once (useful for dry-run / manual trigger)."""
    log("=== Starting full scrape cycle ===")
    handle = os.environ.get("BSKY_HANDLE", "")
    password = os.environ.get("BSKY_PASSWORD", "")
    run_scraper(handle or None, password or None)
    run_account_discovery()
    run_engagement_backfill()
    log("=== Full scrape cycle complete ===")


def main() -> None:
    # Ensure DB is initialized before scheduling
    db_init()
    log("Mofu Tofu scheduler started — DB initialized")

    # Register scheduled jobs
    schedule.every(15).minutes.do(
        lambda: run_scraper(
            os.environ.get("BSKY_HANDLE", "") or None,
            os.environ.get("BSKY_PASSWORD", "") or None,
        )
    )
    log("Scheduled: every 15 minutes → run_scraper")

    schedule.every(1).hours.do(run_account_discovery)
    log("Scheduled: every 1 hour → run_account_discovery")

    schedule.every(6).hours.do(run_engagement_backfill)
    log("Scheduled: every 6 hours → run_engagement_backfill")

    # Run digest immediately on startup
    run_digest()

    # Run everything once at start
    run_all()

    log("Scheduler entering main loop...")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Scheduler stopped by user")
        sys.exit(0)