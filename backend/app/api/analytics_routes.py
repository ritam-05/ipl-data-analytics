from typing import Optional
from fastapi import APIRouter, Depends, Query
from backend.app.core.auth import get_current_user
from backend.app.services.analytics import (
    get_ipl_overview,
    get_season_trends,
    get_win_type_breakdown,
    get_top_batters,
    get_top_bowlers,
    get_player_consistency,
    get_all_players_directory,
    get_team_performance,
    get_head_to_head,
    get_team_details,
    get_venue_analytics,
    get_extreme_matches,
    run_statistical_investigations,
)

router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/overview")
def overview(_user: dict = Depends(get_current_user)):
    return get_ipl_overview()


@router.get("/seasons")
def seasons(_user: dict = Depends(get_current_user)):
    return get_season_trends()


@router.get("/win-types")
def win_types(_user: dict = Depends(get_current_user)):
    return get_win_type_breakdown()


@router.get("/players/batters")
def top_batters(
    season: Optional[int] = Query(default=None, description="Filter by IPL season year"),
    limit: int = Query(default=15, ge=1, le=100),
    _user: dict = Depends(get_current_user),
):
    return get_top_batters(season=season, limit=limit)


@router.get("/players/bowlers")
def top_bowlers(
    season: Optional[int] = Query(default=None, description="Filter by IPL season year"),
    limit: int = Query(default=15, ge=1, le=100),
    _user: dict = Depends(get_current_user),
):
    return get_top_bowlers(season=season, limit=limit)


@router.get("/players/consistency")
def player_consistency(
    min_seasons: int = Query(default=6, ge=2, le=19),
    min_total_runs: int = Query(default=2000, ge=100),
    limit: int = Query(default=10, ge=1, le=50),
    _user: dict = Depends(get_current_user),
):
    return get_player_consistency(
        min_seasons=min_seasons,
        min_total_runs=min_total_runs,
        limit=limit,
    )


@router.get("/players/all")
def all_players_directory(
    season: Optional[int] = Query(default=None, description="Filter by IPL season year"),
    search: Optional[str] = Query(default=None, description="Filter by player name"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user: dict = Depends(get_current_user),
):
    return get_all_players_directory(
        season=season,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/teams")
def teams(
    season: Optional[int] = Query(default=None, description="Filter by IPL season year"),
    _user: dict = Depends(get_current_user),
):
    return get_team_performance(season=season)


@router.get("/teams/h2h")
def head_to_head(
    team_a: str = Query(..., description="First team name"),
    team_b: str = Query(..., description="Second team name"),
    _user: dict = Depends(get_current_user),
):
    return get_head_to_head(team_a=team_a, team_b=team_b)


@router.get("/teams/details")
def team_details(
    team: str = Query(..., description="Franchise name"),
    season: Optional[int] = Query(default=None, description="Optional IPL season year"),
    _user: dict = Depends(get_current_user),
):
    return get_team_details(team_name=team, season=season)


@router.get("/venues")
def venues(
    season: Optional[int] = Query(default=None, description="Filter by IPL season year"),
    limit: int = Query(default=40, ge=1, le=60),
    _user: dict = Depends(get_current_user),
):
    return get_venue_analytics(season=season, limit=limit)


@router.get("/matches/extremes")
def extreme_matches(
    limit: int = Query(default=5, ge=1, le=20),
    _user: dict = Depends(get_current_user),
):
    return get_extreme_matches(limit=limit)


@router.get("/stats")
def statistical_investigations(_user: dict = Depends(get_current_user)):
    return run_statistical_investigations()