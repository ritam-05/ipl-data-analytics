import os
import sys
import json
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
sys.path.insert(0, ROOT_DIR)

from backend.app.agents.ipl_agent import run_ipl_agent

log_file = os.path.join(LOG_DIR, "agent_verification.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

TEST_QUERIES = [
    "How is bowling economy rate calculated in IPL cricket?",
    "Who are the top 5 all-time run scorers in IPL history?",
    "Show the average first innings score by season from 2018 to 2026 and explain the trend.",
]


def run_tests():
    logger.info("=== PHASE 6: LANGGRAPH AGENT VERIFICATION ===")
    for idx, q in enumerate(TEST_QUERIES, start=1):
        logger.info(f"\n--- TEST {idx}: {q} ---")
        res = run_ipl_agent(q, user_preferences={"favourite_team": "Royal Challengers Bengaluru"})
        logger.info(f"Intent: {res['intent']}")
        logger.info(f"SQL Query: {res['sql_query']}")
        logger.info(f"SQL Rows Returned: {res['sql_row_count']} | Error: {res['sql_error']}")
        logger.info(f"Chart Generated: {res['chart_spec'] is not None}")
        logger.info(f"Answer:\n{res['answer']}\n")

    logger.info(f"Phase 6 verification complete! Log saved to: {log_file}")


if __name__ == "__main__":
    run_tests()