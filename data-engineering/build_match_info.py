import os
import csv
import glob
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

load_dotenv(os.path.join(ROOT_DIR, ".env"))

log_file = os.path.join(LOG_DIR, "build_match_info.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

TEAM_NAME_MAPPING = {
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Delhi Daredevils": "Delhi Capitals",
    "Kings XI Punjab": "Punjab Kings",
    "Rising Pune Supergiants": "Rising Pune Supergiant",
}

VENUE_NAME_MAPPING = {
    "Eden Gardens": "Eden Gardens, Kolkata",
    "Wankhede Stadium": "Wankhede Stadium, Mumbai",
    "M Chinnaswamy Stadium": "M Chinnaswamy Stadium, Bengaluru",
    "M.Chinnaswamy Stadium": "M Chinnaswamy Stadium, Bengaluru",
    "M Chinnaswamy Stadium, Bangalore": "M Chinnaswamy Stadium, Bengaluru",
    "Feroz Shah Kotla": "Arun Jaitley Stadium, Delhi",
    "Feroz Shah Kotla, Delhi": "Arun Jaitley Stadium, Delhi",
    "Arun Jaitley Stadium": "Arun Jaitley Stadium, Delhi",
    "Rajiv Gandhi International Stadium, Uppal": "Rajiv Gandhi International Stadium, Uppal, Hyderabad",
    "Rajiv Gandhi International Stadium": "Rajiv Gandhi International Stadium, Uppal, Hyderabad",
    "MA Chidambaram Stadium, Chepauk": "MA Chidambaram Stadium, Chepauk, Chennai",
    "MA Chidambaram Stadium": "MA Chidambaram Stadium, Chepauk, Chennai",
    "Sawai Mansingh Stadium": "Sawai Mansingh Stadium, Jaipur",
    "Sardar Patel Stadium, Motera": "Narendra Modi Stadium, Ahmedabad",
    "Narendra Modi Stadium": "Narendra Modi Stadium, Ahmedabad",
    "Punjab Cricket Association Stadium, Mohali": "Punjab Cricket Association IS Bindra Stadium, Mohali",
    "Punjab Cricket Association IS Bindra Stadium, Mohali, Chandigarh": "Punjab Cricket Association IS Bindra Stadium, Mohali",
    "Punjab Cricket Association IS Bindra Stadium": "Punjab Cricket Association IS Bindra Stadium, Mohali",
    "Maharashtra Cricket Association Stadium": "Maharashtra Cricket Association Stadium, Pune",
    "Subrata Roy Sahara Stadium": "Maharashtra Cricket Association Stadium, Pune",
    "Dr DY Patil Sports Academy": "Dr DY Patil Sports Academy, Mumbai",
    "Brabourne Stadium": "Brabourne Stadium, Mumbai",
    "Sheikh Zayed Stadium": "Zayed Cricket Stadium, Abu Dhabi",
    "Himachal Pradesh Cricket Association Stadium": "Himachal Pradesh Cricket Association Stadium, Dharamsala",
    "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium": "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium, Visakhapatnam",
    "Barsapara Cricket Stadium": "Barsapara Cricket Stadium, Guwahati",
    "Holkar Cricket Stadium": "Holkar Cricket Stadium, Indore",
    "Maharaja Yadavindra Singh International Cricket Stadium, New Chandigarh": "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur",
}


def normalize_season(raw_season: str | None) -> int | None:
    if not raw_season:
        return None
    s = str(raw_season).strip()
    if s == "2007/08":
        return 2008
    if s == "2009/10":
        return 2010
    if s == "2020/21":
        return 2020
    return int(s) if s.isdigit() else None


def parse_info_file(filepath: str) -> dict:
    filename = os.path.basename(filepath)
    match_id = int(filename.replace("_info.csv", ""))

    teams: list[str] = []
    umpires: list[str] = []
    potm: list[str] = []
    meta: dict[str, str] = {}

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3 or row[0].strip() != "info":
                continue
            key = row[1].strip()
            val = row[2].strip()
            if not val:
                continue

            if key == "team":
                teams.append(TEAM_NAME_MAPPING.get(val, val))
            elif key == "umpire":
                umpires.append(val)
            elif key == "player_of_match":
                potm.append(val)
            else:
                meta[key] = val

    raw_venue = meta.get("venue")
    venue = VENUE_NAME_MAPPING.get(raw_venue, raw_venue) if raw_venue else None

    raw_toss_winner = meta.get("toss_winner")
    toss_winner = TEAM_NAME_MAPPING.get(raw_toss_winner, raw_toss_winner) if raw_toss_winner else None

    raw_winner = meta.get("winner")
    winner = TEAM_NAME_MAPPING.get(raw_winner, raw_winner) if raw_winner else None

    win_by_runs = int(meta["winner_runs"]) if meta.get("winner_runs", "").isdigit() else None
    win_by_wickets = int(meta["winner_wickets"]) if meta.get("winner_wickets", "").isdigit() else None

    return {
        "match_id": match_id,
        "season": normalize_season(meta.get("season")),
        "start_date": meta.get("date"),
        "city": meta.get("city"),
        "venue": venue,
        "stage": meta.get("stage") or meta.get("match_number"),
        "team_1": teams[0] if len(teams) > 0 else None,
        "team_2": teams[1] if len(teams) > 1 else None,
        "toss_winner": toss_winner,
        "toss_decision": meta.get("toss_decision"),
        "player_of_match": ", ".join(potm) if potm else None,
        "umpire_1": umpires[0] if len(umpires) > 0 else None,
        "umpire_2": umpires[1] if len(umpires) > 1 else None,
        "tv_umpire": meta.get("tv_umpire"),
        "reserve_umpire": meta.get("reserve_umpire"),
        "match_referee": meta.get("match_referee"),
        "winner": winner,
        "win_by_runs": win_by_runs,
        "win_by_wickets": win_by_wickets,
        "outcome": meta.get("outcome"),
        "method": meta.get("method"),
    }


def build_and_load_match_info():
    raw_dir = os.path.join(BASE_DIR, "bronze", "cricsheet_raw")
    info_files = sorted(glob.glob(os.path.join(raw_dir, "*_info.csv")))
    logger.info(f"Found {len(info_files)} match info files in {raw_dir}")

    if not info_files:
        logger.error("No *_info.csv files found.")
        return

    records = [parse_info_file(fp) for fp in info_files]
    df = pd.DataFrame(records).sort_values(["season", "start_date", "match_id"]).reset_index(drop=True)

    # Save to Gold Parquet
    gold_path = os.path.join(BASE_DIR, "gold", "dim_match_info.parquet")
    df.to_parquet(gold_path, index=False)
    logger.info(f"Saved {len(df):,} rows to {gold_path}")

    # Load into Supabase PostgreSQL
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        logger.error("SUPABASE_DB_URL is not set.")
        return

    engine = create_engine(db_url)
    logger.info("Uploading public.dim_match_info to Supabase...")
    df.to_sql("dim_match_info", engine, schema="public", if_exists="replace", index=False, method="multi", chunksize=500)

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE public.dim_match_info ADD PRIMARY KEY (match_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_match_info_season ON public.dim_match_info (season);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_match_info_potm ON public.dim_match_info (player_of_match);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_match_info_ump1 ON public.dim_match_info (umpire_1);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_match_info_ump2 ON public.dim_match_info (umpire_2);"))
        conn.execute(text("ALTER TABLE public.dim_match_info ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text('DROP POLICY IF EXISTS "Authenticated users can read dim_match_info" ON public.dim_match_info;'))
        conn.execute(text('CREATE POLICY "Authenticated users can read dim_match_info" ON public.dim_match_info FOR SELECT TO authenticated USING (true);'))
        conn.execute(text("GRANT SELECT ON TABLE public.dim_match_info TO service_role, authenticated;"))

    logger.info("public.dim_match_info loaded, indexed, and secured with RLS!")


if __name__ == "__main__":
    build_and_load_match_info()