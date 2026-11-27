import os
import sys
import json
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import voyageai

# Anchor paths and allow importing from backend/app/services
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
sys.path.insert(0, ROOT_DIR)

load_dotenv(os.path.join(ROOT_DIR, ".env"))

from backend.app.services.analytics import (
    get_top_batters,
    get_top_bowlers,
    get_team_performance,
    get_season_trends,
    get_venue_analytics,
    run_statistical_investigations,
)

# Configure logging
log_file = os.path.join(LOG_DIR, "build_rag_kb.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "voyage-4-lite"
EMBEDDING_BATCH_SIZE = 64


def build_documents() -> list[dict]:
    docs = []

    # 1. Cricket Terminology & Statistical Definitions
    definitions = [
        (
            "def_batting_metrics",
            "Batting Average in IPL cricket is calculated as total runs scored divided by total dismissals (times out). "
            "Batting Strike Rate is calculated as (total runs / valid balls faced) * 100, where wides are excluded from balls faced but no-balls are included. "
            "Batter Consistency is measured using the Coefficient of Variation (CV = standard deviation of seasonal runs / mean seasonal runs); a lower CV indicates more consistent season-to-season run production.",
            {"topic": "batting_metrics"},
        ),
        (
            "def_bowling_metrics",
            "Bowling Economy Rate in IPL cricket is calculated as (runs conceded / legal balls bowled) * 6, where runs conceded includes runs off the bat, wides, and no-balls, but excludes byes, legbyes, and penalty runs. "
            "Bowling Average is runs conceded divided by wickets taken, and Bowling Strike Rate is legal balls bowled per wicket. "
            "Only bowler-credited dismissals (bowled, caught, lbw, stumped, caught and bowled, hit wicket) count toward a bowler's wicket tally; run outs are excluded.",
            {"topic": "bowling_metrics"},
        ),
        (
            "def_match_phases",
            "An IPL innings of 20 overs is divided into three tactical phases: Powerplay (overs 1 to 6, with fielding restrictions), "
            "Middle Overs (overs 7 to 15, where spin and strike rotation dominate), and Death Overs (overs 16 to 20, focused on boundary hitting and yorkers).",
            {"topic": "match_phases"},
        ),
    ]
    for key, content, meta in definitions:
        docs.append({"doc_key": key, "doc_type": "cricket_term", "content": content, "metadata": meta})

    # 2. Statistical Investigations Summary (Phase 4)
    stats_res = run_statistical_investigations()
    chase = stats_res["chasing_advantage_test"]
    corr = stats_res["first_innings_score_vs_win_correlation"]
    era = stats_res["scoring_era_shift_test"]
    stats_content = (
        f"IPL Historical Statistical Findings (2008-2026): "
        f"Across {chase['sample_size']} decided matches, chasing teams won {chase['chase_wins']} matches ({chase['chase_win_pct']}%) "
        f"compared to {chase['bat_first_wins']} wins batting first (two-sided binomial test p-value = {chase['p_value']}, "
        f"statistically significant = {chase['statistically_significant_at_0_05']}). "
        f"First-innings score has a point-biserial correlation of r = {corr['point_biserial_r']} (p = {corr['p_value']}) with defending win probability. "
        f"Comparing scoring eras, average first-innings scores rose from {era['early_era_2008_2017_avg']} runs (2008-2017) to "
        f"{era['modern_era_2018_2026_avg']} runs (2018-2026), a shift of +{era['difference_runs']} runs (Welch's t = {era['welch_t_stat']}, p = {era['p_value']})."
    )
    docs.append({
        "doc_key": "finding_statistical_summary",
        "doc_type": "analytical_finding",
        "content": stats_content,
        "metadata": {"topic": "statistical_investigations"},
    })

    # 3. Top 100 Batters Career Summaries
    for b in get_top_batters(limit=100):
        name = b["player_name"]
        content = (
            f"IPL Batting Career Summary for {name}: Played {b['matches']} matches, scored {b['total_runs']} runs "
            f"off {b['balls_faced']} balls with a batting average of {b['batting_average']} and strike rate of {b['strike_rate']}. "
            f"Hit {b['fours']} fours and {b['sixes']} sixes, with a highest seasonal match score of {b['highest_score']}."
        )
        docs.append({
            "doc_key": f"player_bat_{name.lower().replace(' ', '_')}",
            "doc_type": "player_summary",
            "content": content,
            "metadata": {"player": name, "role": "batter"},
        })

    # 4. Top 100 Bowlers Career Summaries
    for bw in get_top_bowlers(limit=100):
        name = bw["player_name"]
        content = (
            f"IPL Bowling Career Summary for {name}: Played {bw['matches']} matches, bowled {bw['overs']} overs, "
            f"conceded {bw['runs_conceded']} runs, and took {bw['total_wickets']} wickets. "
            f"Career economy rate is {bw['economy_rate']}, bowling average is {bw['bowling_average']}, "
            f"and bowling strike rate is {bw['bowling_strike_rate']}."
        )
        docs.append({
            "doc_key": f"player_bowl_{name.lower().replace(' ', '_')}",
            "doc_type": "player_summary",
            "content": content,
            "metadata": {"player": name, "role": "bowler"},
        })

    # 5. Team Histories
    for t in get_team_performance():
        team = t["team"]
        content = (
            f"IPL Team History for {team}: Played {t['matches_played']} matches with {t['wins']} wins "
            f"(overall win percentage: {t['win_pct']}%). Won {t['bat_first_wins']} matches batting first "
            f"and {t['chase_wins']} matches while chasing."
        )
        docs.append({
            "doc_key": f"team_{team.lower().replace(' ', '_')}",
            "doc_type": "team_history",
            "content": content,
            "metadata": {"team": team},
        })

    # 6. Season Summaries (2008-2026)
    for s in get_season_trends():
        season = int(s["season"])
        top_bat = get_top_batters(season=season, limit=1)
        top_bowl = get_top_bowlers(season=season, limit=1)
        bat_str = f"{top_bat[0]['player_name']} ({top_bat[0]['total_runs']} runs)" if top_bat else "N/A"
        bowl_str = f"{top_bowl[0]['player_name']} ({top_bowl[0]['total_wickets']} wickets)" if top_bowl else "N/A"
        content = (
            f"IPL {season} Season Summary: {s['total_matches']} matches played. "
            f"Average 1st innings score was {s['avg_first_innings_score']} and average 2nd innings score was {s['avg_second_innings_score']}. "
            f"Highest innings score was {s['highest_score']}. Chasing teams won {s['chase_wins']} matches vs {s['bat_first_wins']} batting first. "
            f"Top run scorer: {bat_str}. Top wicket taker: {bowl_str}."
        )
        docs.append({
            "doc_key": f"season_{season}",
            "doc_type": "season_summary",
            "content": content,
            "metadata": {"season": season},
        })

    # 7. Venue Profiles
    for v in get_venue_analytics(min_matches=5, limit=60):
        venue = v["venue"]
        content = (
            f"IPL Venue Profile for {venue}: Hosted {v['total_matches']} matches. "
            f"Average 1st innings score is {v['avg_first_innings_score']} (highest: {v['highest_first_innings_score']}, "
            f"lowest: {v['lowest_first_innings_score']}). "
            f"Teams batting first won {v['bat_first_wins']} times and chasing teams won {v['chase_wins']} times "
            f"(chase win percentage: {v['chase_win_pct']}%)."
        )
        docs.append({
            "doc_key": f"venue_{venue.lower().replace(' ', '_').replace(',', '')[:60]}",
            "doc_type": "venue_info",
            "content": content,
            "metadata": {"venue": venue},
        })

    return docs


def build_and_load_rag_kb():
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        logger.error("SUPABASE_DB_URL is missing in .env.")
        return

    voyage_api_key = os.getenv("VOYAGE_API_KEY")
    if not voyage_api_key:
        logger.error("VOYAGE_API_KEY is missing in .env.")
        return

    logger.info("Generating grounded IPL RAG documents from Supabase Gold tables...")
    docs = build_documents()
    logger.info(f"Generated {len(docs)} documents across all categories.")

    client = voyageai.Client(api_key=voyage_api_key)
    texts = [d["content"] for d in docs]
    logger.info("Generating 1024-dim Voyage document embeddings...")
    embeddings = []
    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[start : start + EMBEDDING_BATCH_SIZE]
        result = client.embed(
            batch,
            model=EMBEDDING_MODEL_NAME,
            input_type="document",
        )
        embeddings.extend(result.embeddings)

    engine = create_engine(db_url, pool_pre_ping=True)
    upsert_sql = text("""
        INSERT INTO public.rag_documents (doc_key, doc_type, content, metadata, embedding)
        VALUES (:doc_key, :doc_type, :content, CAST(:metadata AS jsonb), CAST(:embedding AS vector))
        ON CONFLICT (doc_key) DO UPDATE SET
            doc_type = EXCLUDED.doc_type,
            content = EXCLUDED.content,
            metadata = EXCLUDED.metadata,
            embedding = EXCLUDED.embedding,
            created_at = NOW();
    """)

    logger.info("Upserting documents and embeddings into Supabase public.rag_documents...")
    with engine.begin() as conn:
        for doc, emb in zip(docs, embeddings):
            emb_str = "[" + ",".join(f"{x:.6f}" for x in emb) + "]"
            conn.execute(
                upsert_sql,
                {
                    "doc_key": doc["doc_key"],
                    "doc_type": doc["doc_type"],
                    "content": doc["content"],
                    "metadata": json.dumps(doc["metadata"]),
                    "embedding": emb_str,
                },
            )

    with engine.connect() as conn:
        total_in_db = conn.execute(text("SELECT COUNT(*) FROM public.rag_documents")).scalar()
        logger.info(f"Verified public.rag_documents count in Supabase: {total_in_db}")

        # Retrieval Evaluation Test
        test_query = "Which stadium favors chasing and what is the chasing advantage in IPL?"
        q_emb = client.embed(
            [test_query],
            model=EMBEDDING_MODEL_NAME,
            input_type="query",
        ).embeddings[0]
        q_emb_str = "[" + ",".join(f"{x:.6f}" for x in q_emb) + "]"

        search_sql = text("""
            SELECT doc_key, doc_type, ROUND((1 - (embedding <=> CAST(:q_emb AS vector)))::numeric, 4) AS similarity,
                   LEFT(content, 140) AS snippet
            FROM public.rag_documents
            ORDER BY embedding <=> CAST(:q_emb AS vector)
            LIMIT 3;
        """)
        results = conn.execute(search_sql, {"q_emb": q_emb_str}).fetchall()
        logger.info(f"\n--- RETRIEVAL TEST QUERY: '{test_query}' ---")
        for row in results:
            logger.info(f"  [{row[1]}] {row[0]} (sim={row[2]}): {row[3]}...")

    logger.info(f"Phase 5 RAG Knowledge Base complete! Log saved to: {log_file}")


if __name__ == "__main__":
    build_and_load_rag_kb()
