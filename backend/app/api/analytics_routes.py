from typing import Optional
from fastapi import APIRouter, Query
from backend.app.services.analytics import (
    get_ipl_overview,
    get_season_trends,
    get_top_batters,
    get_top_bowlers,
    get_player_consistency,
    get_team_performance,
    get_head_to_head,
    get_venue_analytics,
    get_extreme_matches,
    run_statistical_investigations,
)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/overview")
def overview():
    return get_ipl_overview()


@router.get("/seasons")
def seasons():
    return get_season_trends()


@router.get("/players/batters")
def top_batters(
    season: Optional[int] = Query(default=None, description="Filter by IPL season year"),
    limit: int = Query(default=15, ge=1, le=100),
):
    return get_top_batters(season=season, limit=limit)


@router.get("/players/bowlers")
def top_bowlers(
    season: Optional[int] = Query(default=None, description="Filter by IPL season year"),
    limit: int = Query(default=15, ge=1, le=100),
):
    return get_top_bowlers(season=season, limit=limit)


@router.get("/players/consistency")
def player_consistency(
    min_seasons: int = Query(default=6, ge=2, le=19),
    min_total_runs: int = Query(default=2000, ge=100),
    limit: int = Query(default=10, ge=1, le=50),
):
    return get_player_consistency(
        min_seasons=min_seasons,
        min_total_runs=min_total_runs,
        limit=limit,
    )


@router.get("/teams")
def teams(
    season: Optional[int] = Query(default=None, description="Filter by IPL season year"),
):
    return get_team_performance(season=season)


@router.get("/teams/h2h")
def head_to_head(
    team_a: str = Query(..., description="First team name"),
    team_b: str = Query(..., description="Second team name"),
):
    return get_head_to_head(team_a=team_a, team_b=team_b)


@router.get("/venues")
def venues(
    min_matches: int = Query(default=10, ge=1),
    limit: int = Query(default=20, ge=1, le=60),
):
    return get_venue_analytics(min_matches=min_matches, limit=limit)


@router.get("/matches/extremes")
def extreme_matches(limit: int = Query(default=5, ge=1, le=20)):
    return get_extreme_matches(limit=limit)


@router.get("/stats")
def statistical_investigations():
    return run_statistical_investigations()