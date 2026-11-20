import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.types import Integer
from dotenv import load_dotenv

# Anchor paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
GOLD_DIR = os.path.join(BASE_DIR, "gold")
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Load .env from project root
load_dotenv(os.path.join(ROOT_DIR, ".env"))

# Configure logging
log_file = os.path.join(LOG_DIR, "load_to_supabase.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Strict load order: Dimensions first, then Facts (respects Foreign Keys)
GOLD_TABLES = [
    "dim_seasons",
    "dim_teams",
    "dim_venues",
    "dim_players",
    "fact_matches",
    "fact_player_batting_season",
    "fact_player_bowling_season",
    "fact_venue_stats",
]

# Columns that must be bound as PostgreSQL INTEGER
INT_COLUMNS = [
    "match_id",
    "season",
    "first_season",
    "last_season",
    "total_matches",
    "total_matches_played",
    "innings_1_runs",
    "innings_1_wickets",
    "innings_2_runs",
    "innings_2_wickets",
    "win_margin",
    "matches",
    "runs",
    "balls_faced",
    "fours",
    "sixes",
    "highest_score",
    "dismissals",
    "legal_balls",
    "runs_conceded",
    "wickets",
    "highest_first_innings_score",
    "lowest_first_innings_score",
    "bat_first_wins",
    "chase_wins",
]

SEASON_MAPPING = {
    "2007/08": "2008",
    "2009/10": "2010",
    "2020/21": "2020",
}


def prepare_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    # Normalize any slash-formatted seasons just in case
    for col_name in ["season", "first_season", "last_season"]:
        if col_name in df.columns:
            df[col_name] = df[col_name].astype(str).str.strip().replace(SEASON_MAPPING)

    # Convert integer columns to nullable Int64 and build explicit SQLAlchemy dtype map
    dtype_map = {}
    for col_name in INT_COLUMNS:
        if col_name in df.columns:
            df[col_name] = pd.to_numeric(df[col_name], errors="coerce").astype("Int64")
            dtype_map[col_name] = Integer()

    return df, dtype_map


def load_gold_to_supabase():
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        logger.error("SUPABASE_DB_URL is missing in .env. Please add your Session Pooler URI.")
        return

    logger.info("Connecting to Supabase PostgreSQL via Session Pooler...")
    engine = create_engine(db_url, pool_pre_ping=True)

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified.")
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        return

    # 1. Truncate all 8 analytical tables cleanly (preserves PKs, FKs, Indexes, RLS)
    logger.info("Clearing existing analytical rows for an idempotent reload...")
    truncate_sql = "TRUNCATE TABLE " + ", ".join(f"public.{t}" for t in GOLD_TABLES) + " CASCADE;"
    with engine.begin() as conn:
        conn.execute(text(truncate_sql))
    logger.info("Existing analytical rows cleared.")

    # 2. Load each Gold Parquet table in dependency order
    total_rows_loaded = 0
    for table_name in GOLD_TABLES:
        parquet_dir = os.path.join(GOLD_DIR, table_name)
        if not os.path.exists(parquet_dir):
            logger.error(f"Missing Gold Parquet directory: {parquet_dir}")
            return

        logger.info(f"Reading Parquet for '{table_name}'...")
        df = pd.read_parquet(parquet_dir)
        df, dtype_map = prepare_dataframe(df)

        row_count = len(df)
        logger.info(f"Uploading {row_count:,} rows into public.{table_name}...")

        df.to_sql(
            name=table_name,
            con=engine,
            schema="public",
            if_exists="append",
            index=False,
            dtype=dtype_map,
            method="multi",
            chunksize=500,
        )
        total_rows_loaded += row_count
        logger.info(f"Successfully loaded public.{table_name} ({row_count:,} rows).")

    # 3. Verify final row counts directly from PostgreSQL
    logger.info("--- VERIFYING ROW COUNTS IN SUPABASE ---")
    with engine.connect() as conn:
        for table_name in GOLD_TABLES:
            db_count = conn.execute(text(f"SELECT COUNT(*) FROM public.{table_name}")).scalar()
            logger.info(f"public.{table_name}: {db_count:,} rows")

    logger.info(f"Gold load complete! Total rows synced: {total_rows_loaded:,}")
    logger.info(f"Log saved to: {log_file}")


if __name__ == "__main__":
    load_gold_to_supabase()