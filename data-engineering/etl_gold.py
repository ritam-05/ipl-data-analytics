import os
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    when,
    sum as spark_sum,
    count,
    countDistinct,
    min as spark_min,
    max as spark_max,
    avg,
    round as spark_round,
    lit,
    first,
    coalesce,
)

# Anchor paths to the data-engineering directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, "etl_gold.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

BOWLER_WICKET_TYPES = [
    "bowled",
    "caught",
    "lbw",
    "stumped",
    "caught and bowled",
    "hit wicket",
]


def save_gold_table(df, gold_dir, table_name):
    output_path = os.path.join(gold_dir, table_name)
    df.write.mode("overwrite").parquet(output_path)
    row_count = df.count()
    logger.info(f"Saved Gold table '{table_name}' -> {row_count:,} rows | Path: {output_path}")
    return row_count


def build_gold_layer():
    logger.info("Initializing PySpark Session for Gold Layer ETL...")
    spark = (
        SparkSession.builder.appName("IPL_Gold_Layer_ETL")
        .master("local[*]")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    silver_path = os.path.join(BASE_DIR, "silver", "deliveries")
    gold_dir = os.path.join(BASE_DIR, "gold")
    os.makedirs(gold_dir, exist_ok=True)

    logger.info(f"Reading Silver Parquet data from: {silver_path}")
    df = spark.read.parquet(silver_path)

    # Filter to valid delivery rows (guards against any _info.csv rows if present)
    df = df.filter(
        col("match_id").isNotNull()
        & col("innings").isNotNull()
        & col("striker").isNotNull()
        & col("bowler").isNotNull()
    )

    # Cache in memory since we will reuse this DataFrame across 8 tables
    df.cache()
    total_deliveries = df.count()
    logger.info(f"Valid ball-by-ball deliveries loaded: {total_deliveries:,}")

    # ---------------------------------------------------------
    # 1. DIMENSION TABLES
    # ---------------------------------------------------------
    logger.info("Building Dimension Tables...")

    # dim_seasons (PK: season)
    dim_seasons = df.groupBy("season").agg(
        countDistinct("match_id").alias("total_matches"),
        spark_min("start_date").alias("season_start_date"),
        spark_max("start_date").alias("season_end_date"),
    ).orderBy("season")
    save_gold_table(dim_seasons, gold_dir, "dim_seasons")

    # dim_teams (PK: team_name)
    teams_bat = df.select(col("batting_team").alias("team_name"), "season", "match_id")
    teams_bowl = df.select(col("bowling_team").alias("team_name"), "season", "match_id")
    dim_teams = (
        teams_bat.union(teams_bowl)
        .filter(col("team_name").isNotNull())
        .groupBy("team_name")
        .agg(
            countDistinct("match_id").alias("total_matches_played"),
            spark_min("season").alias("first_season"),
            spark_max("season").alias("last_season"),
        )
        .orderBy("team_name")
    )
    save_gold_table(dim_teams, gold_dir, "dim_teams")

    # dim_venues (PK: venue_name)
    dim_venues = (
        df.filter(col("venue").isNotNull())
        .groupBy(col("venue").alias("venue_name"))
        .agg(
            countDistinct("match_id").alias("total_matches"),
            spark_min("season").alias("first_season"),
            spark_max("season").alias("last_season"),
        )
        .orderBy("venue_name")
    )
    save_gold_table(dim_venues, gold_dir, "dim_venues")

    # dim_players (PK: player_name)
    p1 = df.select(col("striker").alias("player_name"))
    p2 = df.select(col("non_striker").alias("player_name"))
    p3 = df.select(col("bowler").alias("player_name"))
    dim_players = (
        p1.union(p2)
        .union(p3)
        .filter(col("player_name").isNotNull())
        .distinct()
        .orderBy("player_name")
    )
    save_gold_table(dim_players, gold_dir, "dim_players")

    # ---------------------------------------------------------
    # 2. FACT TABLE: fact_matches (Grain: 1 row per match_id)
    # ---------------------------------------------------------
    logger.info("Building fact_matches...")

    # Restrict to standard innings (1 and 2) so Super Overs don't distort match totals
    df_reg = df.filter(col("innings").isin(1, 2))

    innings_totals = df_reg.groupBy("match_id", "season", "start_date", "venue", "innings").agg(
        first("batting_team").alias("batting_team"),
        first("bowling_team").alias("bowling_team"),
        spark_sum("total_runs").alias("runs"),
        spark_sum(when(col("player_dismissed") != "none", 1).otherwise(0)).alias("wickets"),
    )

    inn1 = innings_totals.filter(col("innings") == 1).select(
        "match_id",
        "season",
        "start_date",
        "venue",
        col("batting_team").alias("team_1"),
        col("bowling_team").alias("team_2"),
        col("runs").alias("innings_1_runs"),
        col("wickets").alias("innings_1_wickets"),
    )

    inn2 = innings_totals.filter(col("innings") == 2).select(
        "match_id",
        col("runs").alias("innings_2_runs"),
        col("wickets").alias("innings_2_wickets"),
    )

    fact_matches = (
        inn1.join(inn2, on="match_id", how="left")
        .withColumn(
            "winner",
            when(col("innings_2_runs").isNull(), lit("No Result"))
            .when(col("innings_1_runs") > col("innings_2_runs"), col("team_1"))
            .when(col("innings_2_runs") > col("innings_1_runs"), col("team_2"))
            .otherwise(lit("Tie")),
        )
        .withColumn(
            "win_type",
            when(col("innings_2_runs").isNull(), lit("no_result"))
            .when(col("innings_1_runs") > col("innings_2_runs"), lit("runs"))
            .when(col("innings_2_runs") > col("innings_1_runs"), lit("wickets"))
            .otherwise(lit("tie")),
        )
        .withColumn(
            "win_margin",
            when(col("win_type") == "runs", col("innings_1_runs") - col("innings_2_runs"))
            .when(col("win_type") == "wickets", lit(10) - col("innings_2_wickets"))
            .otherwise(lit(0)),
        )
        .orderBy("season", "start_date", "match_id")
    )
    save_gold_table(fact_matches, gold_dir, "fact_matches")

    # ---------------------------------------------------------
    # 3. FACT TABLE: fact_player_batting_season
    # Grain: 1 row per (player_name, season, team)
    # ---------------------------------------------------------
    logger.info("Building fact_player_batting_season...")

    # Per-match batting score to calculate highest_score accurately
    batter_match_runs = (
        df_reg.groupBy("match_id", "season", col("batting_team").alias("team"), col("striker").alias("player_name"))
        .agg(spark_sum("runs_off_bat").alias("match_runs"))
    )

    batter_high_score = batter_match_runs.groupBy("player_name", "season", "team").agg(
        spark_max("match_runs").alias("highest_score")
    )

    # Dismissals counted by player_dismissed (handles non-striker run outs accurately)
    batter_dismissals = (
        df_reg.filter(col("player_dismissed") != "none")
        .groupBy(col("player_dismissed").alias("player_name"), "season", col("batting_team").alias("team"))
        .agg(count("*").alias("dismissals"))
    )

    batting_base = df_reg.groupBy(
        col("striker").alias("player_name"), "season", col("batting_team").alias("team")
    ).agg(
        countDistinct("match_id").alias("matches"),
        spark_sum("runs_off_bat").alias("runs"),
        spark_sum(when(col("wides") == 0, 1).otherwise(0)).alias("balls_faced"),
        spark_sum(when(col("runs_off_bat") == 4, 1).otherwise(0)).alias("fours"),
        spark_sum(when(col("runs_off_bat") == 6, 1).otherwise(0)).alias("sixes"),
    )

    fact_player_batting_season = (
        batting_base.join(batter_high_score, on=["player_name", "season", "team"], how="left")
        .join(batter_dismissals, on=["player_name", "season", "team"], how="left")
        .withColumn("dismissals", coalesce(col("dismissals"), lit(0)))
        .withColumn(
            "batting_average",
            when(col("dismissals") > 0, spark_round(col("runs") / col("dismissals"), 2)).otherwise(lit(None)),
        )
        .withColumn(
            "strike_rate",
            when(col("balls_faced") > 0, spark_round((col("runs") / col("balls_faced")) * 100, 2)).otherwise(lit(0.0)),
        )
        .orderBy("season", col("runs").desc())
    )
    save_gold_table(fact_player_batting_season, gold_dir, "fact_player_batting_season")

    # ---------------------------------------------------------
    # 4. FACT TABLE: fact_player_bowling_season
    # Grain: 1 row per (player_name, season, team)
    # ---------------------------------------------------------
    logger.info("Building fact_player_bowling_season...")

    bowling_base = df_reg.groupBy(
        col("bowler").alias("player_name"), "season", col("bowling_team").alias("team")
    ).agg(
        countDistinct("match_id").alias("matches"),
        spark_sum(when((col("wides") == 0) & (col("noballs") == 0), 1).otherwise(0)).alias("legal_balls"),
        spark_sum(col("runs_off_bat") + col("wides") + col("noballs")).alias("runs_conceded"),
        spark_sum(when(col("wicket_type").isin(BOWLER_WICKET_TYPES), 1).otherwise(0)).alias("wickets"),
    )

    fact_player_bowling_season = (
        bowling_base.withColumn("overs", spark_round(col("legal_balls") / 6.0, 2))
        .withColumn(
            "economy_rate",
            when(col("legal_balls") > 0, spark_round((col("runs_conceded") / col("legal_balls")) * 6.0, 2)).otherwise(lit(0.0)),
        )
        .withColumn(
            "bowling_average",
            when(col("wickets") > 0, spark_round(col("runs_conceded") / col("wickets"), 2)).otherwise(lit(None)),
        )
        .withColumn(
            "bowling_strike_rate",
            when(col("wickets") > 0, spark_round(col("legal_balls") / col("wickets"), 2)).otherwise(lit(None)),
        )
        .orderBy("season", col("wickets").desc())
    )
    save_gold_table(fact_player_bowling_season, gold_dir, "fact_player_bowling_season")

    # ---------------------------------------------------------
    # 5. FACT TABLE: fact_venue_stats (Grain: 1 row per venue)
    # ---------------------------------------------------------
    logger.info("Building fact_venue_stats...")

    fact_venue_stats = (
        fact_matches.filter(col("venue").isNotNull())
        .groupBy("venue")
        .agg(
            count("match_id").alias("total_matches"),
            spark_round(avg("innings_1_runs"), 2).alias("avg_first_innings_score"),
            spark_max("innings_1_runs").alias("highest_first_innings_score"),
            spark_min("innings_1_runs").alias("lowest_first_innings_score"),
            spark_sum(when(col("win_type") == "runs", 1).otherwise(0)).alias("bat_first_wins"),
            spark_sum(when(col("win_type") == "wickets", 1).otherwise(0)).alias("chase_wins"),
        )
        .withColumn(
            "chase_win_pct",
            when(
                (col("bat_first_wins") + col("chase_wins")) > 0,
                spark_round((col("chase_wins") / (col("bat_first_wins") + col("chase_wins"))) * 100, 2),
            ).otherwise(lit(0.0)),
        )
        .orderBy(col("total_matches").desc())
    )
    save_gold_table(fact_venue_stats, gold_dir, "fact_venue_stats")

    df.unpersist()
    logger.info("Gold Layer ETL complete! All 8 analytical Parquet tables generated.")
    logger.info(f"Log saved to: {log_file}")
    spark.stop()


if __name__ == "__main__":
    build_gold_layer()