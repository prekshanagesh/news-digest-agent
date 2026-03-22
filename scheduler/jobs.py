"""
News Digest Scheduler
Runs the pipeline every morning at 7:00 AM automatically.

Usage:
    cd news_digest_agent
    python3 -m scheduler.jobs
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ROOT / "scheduler.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def run_pipeline():
    """Wrapper around main() with error handling and logging."""
    logger.info("=" * 50)
    logger.info("Starting scheduled pipeline run at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 50)

    try:
        from app.main import main
        main()
        logger.info("Pipeline completed successfully.")

    except Exception as e:
        logger.error("Pipeline failed with error: %s", e, exc_info=True)


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")

    # Schedule: every day at 7:00 AM
    scheduler.add_job(
        run_pipeline,
        trigger=CronTrigger(hour=7, minute=0),
        id="daily_news_digest",
        name="Daily News Digest",
        misfire_grace_time=3600,  # if job is missed, run it within 1 hour
        coalesce=True,            # if missed multiple times, only run once
    )

    logger.info("Scheduler started. Pipeline will run every day at 7:00 AM IST.")
    logger.info("Press Ctrl+C to stop.")

    # Compatible way to show next run time
    try:
        jobs = scheduler.get_jobs()
        for job in jobs:
            try:
                # APScheduler 3.x
                next_run = job.next_run_time
            except AttributeError:
                # APScheduler 4.x
                next_run = getattr(job, "next_fire_time", "unknown")
            logger.info("Job '%s' — next run: %s", job.name, next_run)
    except Exception:
        logger.info("Scheduler configured. Next run: tomorrow at 7:00 AM IST.")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user.")
        scheduler.shutdown()