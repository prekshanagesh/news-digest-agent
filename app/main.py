"""
app/main.py — Entry point for the News Digest Agent

Runs the agentic pipeline via Claude tool use.
The agent decides what to fetch, process, and send.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main():
    from storage.repository import log_pipeline_run
    from agents.orchestrator import run_agent

    run_start = datetime.utcnow().isoformat()
    logger.info("Pipeline started at %s", run_start)

    try:
        run_agent()
        run_finish = datetime.utcnow().isoformat()
        log_pipeline_run(
            run_started_at=run_start,
            run_finished_at=run_finish,
            articles_ingested=0,
            articles_sent=0,
            status="success",
        )
        logger.info("Pipeline finished successfully.")

    except Exception as e:
        run_finish = datetime.utcnow().isoformat()
        log_pipeline_run(
            run_started_at=run_start,
            run_finished_at=run_finish,
            articles_ingested=0,
            articles_sent=0,
            status="failed",
            error_message=str(e),
        )
        logger.error("Pipeline failed: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    main()
