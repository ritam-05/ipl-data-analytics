import os
import logging
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

load_dotenv(os.path.join(ROOT_DIR, ".env"))

log_file = os.path.join(LOG_DIR, "build_over_and_matchup_tables.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def _format_ball_event(row) -> str:
    runs = int(row["total_runs"])
    w_type = str(row["wicket_type"])
    dismissed = str(row["player_dismissed"])
    wides = int(row["wides"])
    noballs = int(row["noballs"])

    tags = []
    if wides > 0:
        tags.append(f"{runs}wd")
    elif noballs > 0:
        tags.append(f"{runs}nb")
    else:
        tags.append(str(runs))

    if w_type != "no_wicket" and dismissed != "none":
        tags.append(f"W({dismissed} - {w_type})")

    return " ".join(tags)


def build_and_load():
    silver_dir = os.path.join(BASE_DIR, "silver", "deliveries")
    if not os.path.exists(silver_dir):
        logger.error(f"Silver directory not found at {silver_dir}")
        return

    logger.info("Reading Silver Parquet deliveries...")
    cols = [
        "match_id",
        "season",
        "innings",
        "ball",
        "batting_team",
        "bowling_team",
        "striker",
        "bowler",
        "runs_off_bat",
        "extras",
        "total_runs",
        "wides",
        "noballs",
        "wicket_type",
        "player_dismissed",
    ]
    df = pd.read_parquet(silver_dir, columns=cols)
    logger.info(f"Loaded {len(df):,} deliveries across {df['match_id'].nunique():,} matches.")

    # Cricsheet `ball` is 0.1..0.6 for over 1, 19.1..19.6 for over 20
    df["over_num"] = np.floor(df["ball"].astype(float)).astype(int) + 1
    df["phase"] = np.select(
        [df["over_num"] <= 6, df["over_num"] <= 15],
        ["Powerplay", "Middle"],
        default="Death",
    )
    df["is_legal"] = ((df["wides"] == 0) & (df["noballs"] == 0)).astype(int)
    df["is_four"] = (df["runs_off_bat"] == 4).astype(int)
    df["is_six"] = (df["runs_off_bat"] == 6).astype(int)
    df["is_wicket"] = (df["wicket_type"] != "no_wicket").astype(int)
    df["is_bowler_wicket"] = (
        (df["wicket_type"] != "no_wicket")
        & (~df["wicket_type"].isin(["run out", "retired hurt", "retired out", "obstructing the field"]))
    ).astype(int)

    df = df.sort_values(["match_id", "innings", "ball"]).reset_index(drop=True)
    df["ball_event"] = [
        _format_ball_event(r)
        for r in df[["total_runs", "wicket_type", "player_dismissed", "wides", "noballs"]].to_dict("records")
    ]

    # ------------------------------------------------------------------------
    # 1. Build fact_match_overs
    # ------------------------------------------------------------------------
    logger.info("Aggregating fact_match_overs...")
    overs_df = (
        df.groupby(
            ["match_id", "season", "innings", "over_num", "phase", "batting_team", "bowling_team"],
            as_index=False,
        )
        .agg(
            bowler=("bowler", lambda s: ", ".join(dict.fromkeys(s))),
            batters=("striker", lambda s: ", ".join(dict.fromkeys(s))),
            legal_balls=("is_legal", "sum"),
            runs=("total_runs", "sum"),
            fours=("is_four", "sum"),
            sixes=("is_six", "sum"),
            wickets=("is_wicket", "sum"),
            dismissals=(
                "player_dismissed",
                lambda s: ", ".join(x for x in dict.fromkeys(s) if x != "none") or None,
            ),
            ball_by_ball=("ball_event", lambda s: " | ".join(s)),
        )
        .sort_values(["match_id", "innings", "over_num"])
        .reset_index(drop=True)
    )

    gold_overs_path = os.path.join(BASE_DIR, "gold", "fact_match_overs.parquet")
    overs_df.to_parquet(gold_overs_path, index=False)
    logger.info(f"Saved {len(overs_df):,} over rows to {gold_overs_path}")

    # ------------------------------------------------------------------------
    # 2. Build fact_player_matchups (batter vs bowler, min 6 legal balls)
    # ------------------------------------------------------------------------
    logger.info("Aggregating fact_player_matchups...")
    df["batter_ball"] = (df["wides"] == 0).astype(int)
    matchups_df = (
        df.groupby(["striker", "bowler"], as_index=False)
        .agg(
            matches=("match_id", "nunique"),
            balls_faced=("batter_ball", "sum"),
            runs=("runs_off_bat", "sum"),
            fours=("is_four", "sum"),
            sixes=("is_six", "sum"),
            dismissals=("is_bowler_wicket", "sum"),
        )
    )
    matchups_df = matchups_df[matchups_df["balls_faced"] >= 6].copy()
    matchups_df["strike_rate"] = (
        (matchups_df["runs"] / matchups_df["balls_faced"].replace(0, np.nan)) * 100
    ).round(2)
    matchups_df["batting_average"] = (
        matchups_df["runs"] / matchups_df["dismissals"].replace(0, np.nan)
    ).round(2)
    matchups_df = matchups_df.rename(columns={"striker": "batter"}).sort_values(
        ["runs", "balls_faced"], ascending=False
    ).reset_index(drop=True)

    gold_matchups_path = os.path.join(BASE_DIR, "gold", "fact_player_matchups.parquet")
    matchups_df.to_parquet(gold_matchups_path, index=False)
    logger.info(f"Saved {len(matchups_df):,} matchup rows to {gold_matchups_path}")

    # ------------------------------------------------------------------------
    # 3. Upload both tables to Supabase & enable RLS
    # ------------------------------------------------------------------------
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        logger.error("SUPABASE_DB_URL is not set.")
        return

    engine = create_engine(db_url)
    logger.info("Uploading public.fact_match_overs to Supabase...")
    overs_df.to_sql(
        "fact_match_overs",
        engine,
        schema="public",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000,
    )

    logger.info("Uploading public.fact_player_matchups to Supabase...")
    matchups_df.to_sql(
        "fact_player_matchups",
        engine,
        schema="public",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000,
    )

    with engine.begin() as conn:
        # Indexes & RLS for fact_match_overs
        conn.execute(text("ALTER TABLE public.fact_match_overs ADD PRIMARY KEY (match_id, innings, over_num);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_match_overs_season ON public.fact_match_overs (season);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_match_overs_phase ON public.fact_match_overs (phase);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_match_overs_bat_team ON public.fact_match_overs (batting_team);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_match_overs_bowl_team ON public.fact_match_overs (bowling_team);"))
        conn.execute(text("ALTER TABLE public.fact_match_overs ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text('DROP POLICY IF EXISTS "Authenticated users can read fact_match_overs" ON public.fact_match_overs;'))
        conn.execute(text('CREATE POLICY "Authenticated users can read fact_match_overs" ON public.fact_match_overs FOR SELECT TO authenticated USING (true);'))
        conn.execute(text("GRANT SELECT ON TABLE public.fact_match_overs TO service_role, authenticated;"))

        # Indexes & RLS for fact_player_matchups
        conn.execute(text("ALTER TABLE public.fact_player_matchups ADD PRIMARY KEY (batter, bowler);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_matchups_batter ON public.fact_player_matchups (batter);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_matchups_bowler ON public.fact_player_matchups (bowler);"))
        conn.execute(text("ALTER TABLE public.fact_player_matchups ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text('DROP POLICY IF EXISTS "Authenticated users can read fact_player_matchups" ON public.fact_player_matchups;'))
        conn.execute(text('CREATE POLICY "Authenticated users can read fact_player_matchups" ON public.fact_player_matchups FOR SELECT TO authenticated USING (true);'))
        conn.execute(text("GRANT SELECT ON TABLE public.fact_player_matchups TO service_role, authenticated;"))

    logger.info("Successfully loaded fact_match_overs and fact_player_matchups into Supabase!")


if __name__ == "__main__":
    build_and_load()