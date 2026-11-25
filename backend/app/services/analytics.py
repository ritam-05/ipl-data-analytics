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
        return [
            {col: (float(val) if hasattr(val, "is_finite") else val) for col, val in zip(columns, row)}
            for row in result.fetchall()
        ]


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
    return rows[0] if rows else {}


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


def get_all_players_directory(
    season: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    Returns combined batting and bowling statistics for every IPL player in history
    (or for a specific season), with optional name search and pagination.
    """
    bat_where = "WHERE season = :season" if season is not None else ""
    bowl_where = "WHERE season = :season" if season is not None else ""

    if season is None:
        base_players_cte = """
            all_player_names AS (
                SELECT player_name FROM public.dim_players
                UNION
                SELECT player_name FROM public.fact_player_batting_season
                UNION
                SELECT player_name FROM public.fact_player_bowling_season
            ),
        """
    else:
        base_players_cte = """
            all_player_names AS (
                SELECT player_name FROM public.fact_player_batting_season WHERE season = :season
                UNION
                SELECT player_name FROM public.fact_player_bowling_season WHERE season = :season
            ),
        """

    search_filter = "WHERE p.player_name ILIKE :search_pattern" if search and search.strip() else ""
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None

    sql = f"""
        WITH
        {base_players_cte}
        bat_agg AS (
            SELECT
                player_name,
                SUM(matches) AS bat_matches,
                SUM(runs) AS runs,
                SUM(balls_faced) AS balls_faced,
                SUM(fours) AS fours,
                SUM(sixes) AS sixes,
                MAX(highest_score) AS highest_score,
                ROUND((SUM(runs)::numeric / NULLIF(SUM(dismissals), 0)), 2) AS batting_average,
                ROUND((SUM(runs)::numeric / NULLIF(SUM(balls_faced), 0)) * 100, 2) AS batting_sr
            FROM public.fact_player_batting_season
            {bat_where}
            GROUP BY player_name
        ),
        bowl_agg AS (
            SELECT
                player_name,
                SUM(matches) AS bowl_matches,
                SUM(wickets) AS wickets,
                SUM(runs_conceded) AS runs_conceded,
                ROUND((SUM(legal_balls)::numeric / 6.0), 1) AS overs,
                ROUND((SUM(runs_conceded)::numeric / NULLIF(SUM(legal_balls), 0)) * 6.0, 2) AS economy_rate,
                ROUND((SUM(runs_conceded)::numeric / NULLIF(SUM(wickets), 0)), 2) AS bowling_average,
                ROUND((SUM(legal_balls)::numeric / NULLIF(SUM(wickets), 0)), 2) AS bowling_sr
            FROM public.fact_player_bowling_season
            {bowl_where}
            GROUP BY player_name
        ),
        combined AS (
            SELECT
                p.player_name,
                GREATEST(COALESCE(bt.bat_matches, 0), COALESCE(bw.bowl_matches, 0)) AS matches,
                COALESCE(bt.runs, 0) AS runs,
                COALESCE(bt.balls_faced, 0) AS balls_faced,
                COALESCE(bt.fours, 0) AS fours,
                COALESCE(bt.sixes, 0) AS sixes,
                COALESCE(bt.highest_score, 0) AS highest_score,
                bt.batting_average,
                bt.batting_sr,
                COALESCE(bw.wickets, 0) AS wickets,
                COALESCE(bw.runs_conceded, 0) AS runs_conceded,
                COALESCE(bw.overs, 0) AS overs,
                bw.economy_rate,
                bw.bowling_average,
                bw.bowling_sr
            FROM all_player_names p
            LEFT JOIN bat_agg bt ON p.player_name = bt.player_name
            LEFT JOIN bowl_agg bw ON p.player_name = bw.player_name
            {search_filter}
        )
        SELECT
            *,
            COUNT(*) OVER() AS total_count
        FROM combined
        ORDER BY runs DESC, wickets DESC, player_name ASC
        LIMIT :limit OFFSET :offset
    """
    rows = _query_to_dicts(
        sql,
        {
            "season": season,
            "search_pattern": search_pattern,
            "limit": limit,
            "offset": offset,
        },
    )

    total_count = int(rows[0]["total_count"]) if rows else 0
    clean_rows = [{k: v for k, v in r.items() if k != "total_count"} for r in rows]

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "players": clean_rows,
    }


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


def get_team_details(team_name: str, season: Optional[int] = None) -> dict:
    season_filter = "AND season = :season" if season is not None else ""
    b_season_filter = "AND b.season = :season" if season is not None else ""
    params = {"team": team_name, "season": season}

    summary_sql = f"""
        WITH team_games AS (
            SELECT season, winner, 'bat_first' AS role, innings_1_runs AS team_runs
            FROM public.fact_matches
            WHERE team_1 = :team {season_filter}
            UNION ALL
            SELECT season, winner, 'chase' AS role, innings_2_runs AS team_runs
            FROM public.fact_matches
            WHERE team_2 = :team {season_filter}
        )
        SELECT
            COUNT(*) AS matches_played,
            SUM(CASE WHEN winner = :team THEN 1 ELSE 0 END) AS wins,
            ROUND((SUM(CASE WHEN winner = :team THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0)) * 100, 2) AS win_pct,
            SUM(CASE WHEN role = 'bat_first' AND winner = :team THEN 1 ELSE 0 END) AS bat_first_wins,
            SUM(CASE WHEN role = 'chase' AND winner = :team THEN 1 ELSE 0 END) AS chase_wins,
            MAX(team_runs) AS highest_team_score,
            ROUND(AVG(team_runs)::numeric, 2) AS avg_team_score
        FROM team_games
    """
    summary_rows = _query_to_dicts(summary_sql, params)
    summary = summary_rows[0] if summary_rows else {}

    top_batters_sql = f"""
        SELECT
            player_name,
            SUM(matches) AS matches,
            SUM(runs) AS total_runs,
            SUM(balls_faced) AS balls_faced,
            MAX(highest_score) AS highest_score,
            ROUND((SUM(runs)::numeric / NULLIF(SUM(dismissals), 0)), 2) AS batting_average,
            ROUND((SUM(runs)::numeric / NULLIF(SUM(balls_faced), 0)) * 100, 2) AS strike_rate
        FROM public.fact_player_batting_season
        WHERE team = :team {season_filter}
        GROUP BY player_name
        ORDER BY total_runs DESC
        LIMIT 5
    """
    top_batters = _query_to_dicts(top_batters_sql, params)

    top_bowlers_sql = f"""
        SELECT
            player_name,
            SUM(matches) AS matches,
            SUM(wickets) AS total_wickets,
            SUM(runs_conceded) AS runs_conceded,
            ROUND((SUM(legal_balls)::numeric / 6.0), 1) AS overs,
            ROUND((SUM(runs_conceded)::numeric / NULLIF(SUM(legal_balls), 0)) * 6.0, 2) AS economy_rate,
            ROUND((SUM(legal_balls)::numeric / NULLIF(SUM(wickets), 0)), 2) AS bowling_strike_rate
        FROM public.fact_player_bowling_season
        WHERE team = :team {season_filter}
        GROUP BY player_name
        ORDER BY total_wickets DESC, economy_rate ASC
        LIMIT 5
    """
    top_bowlers = _query_to_dicts(top_bowlers_sql, params)

    min_balls = 30 if season is not None else 100
    best_bat_sr_sql = f"""
        SELECT
            player_name,
            SUM(runs) AS total_runs,
            SUM(balls_faced) AS balls_faced,
            ROUND((SUM(runs)::numeric / NULLIF(SUM(balls_faced), 0)) * 100, 2) AS strike_rate
        FROM public.fact_player_batting_season
        WHERE team = :team {season_filter}
        GROUP BY player_name
        HAVING SUM(balls_faced) >= :min_balls
        ORDER BY strike_rate DESC, total_runs DESC
        LIMIT 1
    """
    best_bat_sr_rows = _query_to_dicts(best_bat_sr_sql, {**params, "min_balls": min_balls})
    if not best_bat_sr_rows:
        best_bat_sr_rows = _query_to_dicts(best_bat_sr_sql, {**params, "min_balls": 10})

    min_wkts = 3 if season is not None else 10
    best_bowl_sr_sql = f"""
        SELECT
            player_name,
            SUM(wickets) AS total_wickets,
            ROUND((SUM(legal_balls)::numeric / NULLIF(SUM(wickets), 0)), 2) AS bowling_strike_rate
        FROM public.fact_player_bowling_season
        WHERE team = :team {season_filter}
        GROUP BY player_name
        HAVING SUM(wickets) >= :min_wkts
        ORDER BY bowling_strike_rate ASC, total_wickets DESC
        LIMIT 1
    """
    best_bowl_sr_rows = _query_to_dicts(best_bowl_sr_sql, {**params, "min_wkts": min_wkts})
    if not best_bowl_sr_rows:
        best_bowl_sr_rows = _query_to_dicts(best_bowl_sr_sql, {**params, "min_wkts": 1})

    min_legal_balls = 24 if season is not None else 120
    best_econ_sql = f"""
        SELECT
            player_name,
            SUM(wickets) AS total_wickets,
            ROUND((SUM(legal_balls)::numeric / 6.0), 1) AS overs,
            ROUND((SUM(runs_conceded)::numeric / NULLIF(SUM(legal_balls), 0)) * 6.0, 2) AS economy_rate
        FROM public.fact_player_bowling_season
        WHERE team = :team {season_filter}
        GROUP BY player_name
        HAVING SUM(legal_balls) >= :min_legal_balls
        ORDER BY economy_rate ASC
        LIMIT 1
    """
    best_econ_rows = _query_to_dicts(best_econ_sql, {**params, "min_legal_balls": min_legal_balls})
    if not best_econ_rows:
        best_econ_rows = _query_to_dicts(best_econ_sql, {**params, "min_legal_balls": 6})

    emerging_sql = f"""
        WITH debut_seasons AS (
            SELECT player_name, MIN(season) AS debut_season
            FROM public.fact_player_batting_season
            GROUP BY player_name
        )
        SELECT
            b.player_name,
            b.season AS debut_season,
            b.runs AS runs,
            b.strike_rate AS strike_rate
        FROM public.fact_player_batting_season b
        JOIN debut_seasons d
          ON b.player_name = d.player_name AND b.season = d.debut_season
        WHERE b.team = :team {b_season_filter}
        ORDER BY b.runs DESC
        LIMIT 1
    """
    emerging_rows = _query_to_dicts(emerging_sql, params)

    return {
        "team": team_name,
        "season": season,
        "summary": summary,
        "most_runs": top_batters[0] if top_batters else None,
        "most_wickets": top_bowlers[0] if top_bowlers else None,
        "best_batting_sr": best_bat_sr_rows[0] if best_bat_sr_rows else None,
        "best_bowling_sr": best_bowl_sr_rows[0] if best_bowl_sr_rows else None,
        "best_economy": best_econ_rows[0] if best_econ_rows else None,
        "emerging_player": emerging_rows[0] if emerging_rows else None,
        "top_batters": top_batters,
        "top_bowlers": top_bowlers,
    }


# ============================================================================
# 4. VENUE & MATCH ANALYTICS
# ============================================================================

def get_venue_analytics(season: Optional[int] = None, min_matches: int = 1, limit: int = 40) -> list[dict]:
    if season is None:
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

    sql = """
        SELECT
            venue,
            COUNT(*) AS total_matches,
            ROUND(AVG(innings_1_runs)::numeric, 2) AS avg_first_innings_score,
            MAX(innings_1_runs) AS highest_first_innings_score,
            MIN(innings_1_runs) AS lowest_first_innings_score,
            SUM(CASE WHEN win_type = 'runs' THEN 1 ELSE 0 END) AS bat_first_wins,
            SUM(CASE WHEN win_type = 'wickets' THEN 1 ELSE 0 END) AS chase_wins,
            ROUND(
                (SUM(CASE WHEN win_type = 'wickets' THEN 1 ELSE 0 END)::numeric /
                 NULLIF(SUM(CASE WHEN win_type IN ('runs', 'wickets') THEN 1 ELSE 0 END), 0)) * 100,
                2
            ) AS chase_win_pct
        FROM public.fact_matches
        WHERE season = :season
        GROUP BY venue
        ORDER BY total_matches DESC, avg_first_innings_score DESC
        LIMIT :limit
    """
    return _query_to_dicts(sql, {"season": season, "limit": limit})


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
    sql = """
        SELECT season, innings_1_runs, win_type
        FROM public.fact_matches
        WHERE win_type IN ('runs', 'wickets') AND innings_1_runs IS NOT NULL
    """
    df = pd.DataFrame(_query_to_dicts(sql))

    total_decided = len(df)
    chase_wins = int((df["win_type"] == "wickets").sum())
    bat_first_wins = int((df["win_type"] == "runs").sum())
    binom_res = stats.binomtest(chase_wins, n=total_decided, p=0.5, alternative="two-sided")

    defended_flag = (df["win_type"] == "runs").astype(int)
    corr_r, corr_p = stats.pointbiserialr(df["innings_1_runs"], defended_flag)

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