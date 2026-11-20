import os
from typing import Optional
import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load .env from project root if running locally
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

_engine = None


def get_db_engine():
    global _engine
    if _engine is None:
        db_url = os.getenv("SUPABASE_DB_URL")
        if not db_url:
            raise ValueError("SUPABASE_DB_URL is not set in environment variables.")
        _engine = create_engine(db_url, pool_pre_ping=True)
    return _engine


def _query_to_dicts(sql: str, params: Optional[dict] = None) -> list[dict]:
    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        columns = list(result.keys())
        return [dict(zip(columns, row)) for row in result.fetchall()]


# ============================================================================
# 1. IPL OVERVIEW & SEASON ANALYTICS
# ============================================================================

def get_ipl_overview() -> dict:
    sql = """
        SELECT
            (SELECT COUNT(*) FROM public.dim_seasons) AS total_seasons,
            (SELECT COUNT(*) FROM public.fact_matches) AS total_matches,
            (SELECT COUNT(*) FROM public.dim_players) AS total_players,
            (SELECT COUNT(*) FROM public.dim_teams) AS total_teams,
            (SELECT COUNT(*) FROM public.dim_venues) AS total_venues,
            (SELECT ROUND(AVG(innings_1_runs)::numeric, 2) FROM public.fact_matches WHERE innings_1_runs IS NOT NULL) AS avg_first_innings_score,
            (SELECT MAX(innings_1_runs) FROM public.fact_matches) AS highest_team_score
    """
    rows = _query_to_dicts(sql)
    return {k: (float(v) if hasattr(v, "is_finite") else v) for k, v in rows[0].items()}


def get_season_trends() -> list[dict]:
    sql = """
        SELECT
            m.season,
            COUNT(*) AS total_matches,
            ROUND(AVG(m.innings_1_runs)::numeric, 2) AS avg_first_innings_score,
            ROUND(AVG(m.innings_2_runs)::numeric, 2) AS avg_second_innings_score,
            MAX(GREATEST(COALESCE(m.innings_1_runs, 0), COALESCE(m.innings_2_runs, 0))) AS highest_score,
            SUM(CASE WHEN m.win_type = 'wickets' THEN 1 ELSE 0 END) AS chase_wins,
            SUM(CASE WHEN m.win_type = 'runs' THEN 1 ELSE 0 END) AS bat_first_wins
        FROM public.fact_matches m
        GROUP BY m.season
        ORDER BY m.season ASC
    """
    return _query_to_dicts(sql)


# ============================================================================
# 2. PLAYER ANALYTICS
# ============================================================================

def get_top_batters(season: Optional[int] = None, limit: int = 10) -> list[dict]:
    where_clause = "WHERE season = :season" if season is not None else ""
    sql = f"""
        SELECT
            player_name,
            SUM(matches) AS matches,
            SUM(runs) AS total_runs,
            SUM(balls_faced) AS balls_faced,
            SUM(fours) AS fours,
            SUM(sixes) AS sixes,
            MAX(highest_score) AS highest_score,
            ROUND((SUM(runs)::numeric / NULLIF(SUM(dismissals), 0)), 2) AS batting_average,
            ROUND((SUM(runs)::numeric / NULLIF(SUM(balls_faced), 0)) * 100, 2) AS strike_rate
        FROM public.fact_player_batting_season
        {where_clause}
        GROUP BY player_name
        ORDER BY total_runs DESC
        LIMIT :limit
    """
    return _query_to_dicts(sql, {"season": season, "limit": limit})


def get_top_bowlers(season: Optional[int] = None, limit: int = 10) -> list[dict]:
    where_clause = "WHERE season = :season" if season is not None else ""
    sql = f"""
        SELECT
            player_name,
            SUM(matches) AS matches,
            SUM(wickets) AS total_wickets,
            SUM(runs_conceded) AS runs_conceded,
            ROUND((SUM(legal_balls)::numeric / 6.0), 1) AS overs,
            ROUND((SUM(runs_conceded)::numeric / NULLIF(SUM(legal_balls), 0)) * 6.0, 2) AS economy_rate,
            ROUND((SUM(runs_conceded)::numeric / NULLIF(SUM(wickets), 0)), 2) AS bowling_average,
            ROUND((SUM(legal_balls)::numeric / NULLIF(SUM(wickets), 0)), 2) AS bowling_strike_rate
        FROM public.fact_player_bowling_season
        {where_clause}
        GROUP BY player_name
        ORDER BY total_wickets DESC, economy_rate ASC
        LIMIT :limit
    """
    return _query_to_dicts(sql, {"season": season, "limit": limit})


def get_player_consistency(min_seasons: int = 6, min_total_runs: int = 2000, limit: int = 10) -> list[dict]:
    """
    Measures batter season-to-season consistency using Coefficient of Variation (CV = std / mean).
    Lower CV indicates more consistent run production across seasons.
    """
    sql = """
        SELECT player_name, season, SUM(runs) AS season_runs
        FROM public.fact_player_batting_season
        GROUP BY player_name, season
    """
    df = pd.DataFrame(_query_to_dicts(sql))
    if df.empty:
        return []

    grouped = df.groupby("player_name")["season_runs"].agg(
        seasons_played="count",
        total_runs="sum",
        mean_runs_per_season="mean",
        std_runs_per_season="std",
    ).reset_index()

    filtered = grouped[
        (grouped["seasons_played"] >= min_seasons) & (grouped["total_runs"] >= min_total_runs)
    ].copy()

    filtered["cv"] = (filtered["std_runs_per_season"] / filtered["mean_runs_per_season"]).round(3)
    filtered["mean_runs_per_season"] = filtered["mean_runs_per_season"].round(2)
    filtered["std_runs_per_season"] = filtered["std_runs_per_season"].round(2)

    result = filtered.sort_values(by="cv", ascending=True).head(limit)
    return result.to_dict(orient="records")


# ============================================================================
# 3. TEAM ANALYTICS
# ============================================================================

def get_team_performance(season: Optional[int] = None) -> list[dict]:
    where_clause = "WHERE season = :season" if season is not None else ""
    sql = f"""
        WITH team_matches AS (
            SELECT team_1 AS team, winner, win_type, 'bat_first' AS role FROM public.fact_matches {where_clause}
            UNION ALL
            SELECT team_2 AS team, winner, win_type, 'chase' AS role FROM public.fact_matches {where_clause}
        )
        SELECT
            team,
            COUNT(*) AS matches_played,
            SUM(CASE WHEN winner = team THEN 1 ELSE 0 END) AS wins,
            ROUND((SUM(CASE WHEN winner = team THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0)) * 100, 2) AS win_pct,
            SUM(CASE WHEN role = 'bat_first' AND winner = team THEN 1 ELSE 0 END) AS bat_first_wins,
            SUM(CASE WHEN role = 'chase' AND winner = team THEN 1 ELSE 0 END) AS chase_wins
        FROM team_matches
        GROUP BY team
        ORDER BY win_pct DESC, wins DESC
    """
    return _query_to_dicts(sql, {"season": season})


def get_head_to_head(team_a: str, team_b: str) -> dict:
    sql = """
        SELECT
            COUNT(*) AS total_matches,
            SUM(CASE WHEN winner = :team_a THEN 1 ELSE 0 END) AS team_a_wins,
            SUM(CASE WHEN winner = :team_b THEN 1 ELSE 0 END) AS team_b_wins,
            SUM(CASE WHEN winner NOT IN (:team_a, :team_b) THEN 1 ELSE 0 END) AS no_result_or_tie
        FROM public.fact_matches
        WHERE (team_1 = :team_a AND team_2 = :team_b)
           OR (team_1 = :team_b AND team_2 = :team_a)
    """
    rows = _query_to_dicts(sql, {"team_a": team_a, "team_b": team_b})
    return {"team_a": team_a, "team_b": team_b, **rows[0]}


# ============================================================================
# 4. VENUE & MATCH ANALYTICS
# ============================================================================

def get_venue_analytics(min_matches: int = 10, limit: int = 15) -> list[dict]:
    sql = """
        SELECT
            venue,
            total_matches,
            avg_first_innings_score,
            highest_first_innings_score,
            lowest_first_innings_score,
            bat_first_wins,
            chase_wins,
            chase_win_pct
        FROM public.fact_venue_stats
        WHERE total_matches >= :min_matches
        ORDER BY total_matches DESC
        LIMIT :limit
    """
    return _query_to_dicts(sql, {"min_matches": min_matches, "limit": limit})


def get_extreme_matches(limit: int = 5) -> dict:
    highest_scoring_sql = """
        SELECT match_id, season, start_date, venue, team_1, team_2,
               innings_1_runs, innings_2_runs, (innings_1_runs + COALESCE(innings_2_runs, 0)) AS combined_runs, winner
        FROM public.fact_matches
        WHERE innings_1_runs IS NOT NULL AND innings_2_runs IS NOT NULL
        ORDER BY combined_runs DESC
        LIMIT :limit
    """
    closest_runs_sql = """
        SELECT match_id, season, start_date, team_1, team_2, innings_1_runs, innings_2_runs, winner, win_margin
        FROM public.fact_matches
        WHERE win_type = 'runs' AND win_margin > 0
        ORDER BY win_margin ASC, season DESC
        LIMIT :limit
    """
    return {
        "highest_scoring_matches": _query_to_dicts(highest_scoring_sql, {"limit": limit}),
        "closest_run_margin_matches": _query_to_dicts(closest_runs_sql, {"limit": limit}),
    }


# ============================================================================
# 5. ADVANCED STATISTICAL INVESTIGATIONS
# ============================================================================

def run_statistical_investigations() -> dict:
    """
    Performs formal statistical hypothesis testing on IPL historical data:
    1. Chasing vs Batting First Advantage (Two-sided Exact Binomial Test)
    2. First-Innings Score vs. Defending Win Probability (Point-Biserial Correlation)
    3. Modern Era (2018-2026) vs Early Era (2008-2017) Scoring Shift (Welch's t-test)
    """
    sql = """
        SELECT season, innings_1_runs, win_type
        FROM public.fact_matches
        WHERE win_type IN ('runs', 'wickets') AND innings_1_runs IS NOT NULL
    """
    df = pd.DataFrame(_query_to_dicts(sql))

    # 1. Binomial Test: Is chasing win probability significantly different from 50%?
    total_decided = len(df)
    chase_wins = int((df["win_type"] == "wickets").sum())
    bat_first_wins = int((df["win_type"] == "runs").sum())
    binom_res = stats.binomtest(chase_wins, n=total_decided, p=0.5, alternative="two-sided")

    # 2. Point-Biserial Correlation: Does higher 1st innings score correlate with defending wins?
    defended_flag = (df["win_type"] == "runs").astype(int)
    corr_r, corr_p = stats.pointbiserialr(df["innings_1_runs"], defended_flag)

    # 3. Welch's t-test: Did average 1st innings score shift significantly from 2018 onwards?
    early_era = df[df["season"] <= 2017]["innings_1_runs"]
    modern_era = df[df["season"] >= 2018]["innings_1_runs"]
    t_stat, t_p = stats.ttest_ind(modern_era, early_era, equal_var=False)

    return {
        "chasing_advantage_test": {
            "sample_size": total_decided,
            "chase_wins": chase_wins,
            "bat_first_wins": bat_first_wins,
            "chase_win_pct": round((chase_wins / total_decided) * 100, 2),
            "p_value": round(float(binom_res.pvalue), 5),
            "statistically_significant_at_0_05": bool(binom_res.pvalue < 0.05),
        },
        "first_innings_score_vs_win_correlation": {
            "point_biserial_r": round(float(corr_r), 4),
            "p_value": float(f"{corr_p:.2e}"),
            "interpretation": "Strong positive association between 1st innings total and defending win probability"
            if corr_r > 0.35
            else "Moderate positive association",
        },
        "scoring_era_shift_test": {
            "early_era_2008_2017_avg": round(float(early_era.mean()), 2),
            "modern_era_2018_2026_avg": round(float(modern_era.mean()), 2),
            "difference_runs": round(float(modern_era.mean() - early_era.mean()), 2),
            "welch_t_stat": round(float(t_stat), 3),
            "p_value": float(f"{t_p:.2e}"),
            "statistically_significant_at_0_05": bool(t_p < 0.05),
        },
    }