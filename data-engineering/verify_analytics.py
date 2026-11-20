import os
import sys
import json
import logging

# Allow importing from backend/app/services
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, ROOT_DIR)

from backend.app.services.analytics import (
    get_ipl_overview,
    get_top_batters,
    get_top_bowlers,
    get_player_consistency,
    get_team_performance,
    get_head_to_head,
    get_venue_analytics,
    get_extreme_matches,
    run_statistical_investigations,
)

LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "analytics_report.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def run_verification():
    logger.info("=== IPL INTELLIGENCE: PHASE 4 ANALYTICS VERIFICATION ===")

    overview = get_ipl_overview()
    logger.info(f"\n1. IPL OVERVIEW:\n{json.dumps(overview, indent=2, default=str)}")

    top_batters = get_top_batters(limit=5)
    logger.info(f"\n2. TOP 5 ALL-TIME BATTERS:\n{json.dumps(top_batters, indent=2, default=str)}")

    top_bowlers = get_top_bowlers(limit=5)
    logger.info(f"\n3. TOP 5 ALL-TIME BOWLERS:\n{json.dumps(top_bowlers, indent=2, default=str)}")

    consistency = get_player_consistency(min_seasons=6, min_total_runs=2000, limit=5)
    logger.info(f"\n4. MOST CONSISTENT BATTERS (Lowest CV):\n{json.dumps(consistency, indent=2, default=str)}")

    teams = get_team_performance()[:5]
    logger.info(f"\n5. TOP 5 TEAMS BY WIN %:\n{json.dumps(teams, indent=2, default=str)}")

    h2h = get_head_to_head("Mumbai Indians", "Chennai Super Kings")
    logger.info(f"\n6. HEAD-TO-HEAD (MI vs CSK):\n{json.dumps(h2h, indent=2, default=str)}")

    venues = get_venue_analytics(min_matches=15, limit=5)
    logger.info(f"\n7. TOP 5 VENUES:\n{json.dumps(venues, indent=2, default=str)}")

    extremes = get_extreme_matches(limit=3)
    logger.info(f"\n8. EXTREME MATCHES (Top 3 Highest Scoring):\n{json.dumps(extremes['highest_scoring_matches'], indent=2, default=str)}")

    stats_report = run_statistical_investigations()
    logger.info(f"\n9. STATISTICAL INVESTIGATIONS:\n{json.dumps(stats_report, indent=2, default=str)}")

    logger.info(f"\nPhase 4 verification complete! Report saved to: {log_file}")


if __name__ == "__main__":
    run_verification()