import os
import glob
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, coalesce, lit, when
from pyspark.sql.types import IntegerType

# Anchor paths to the data-engineering directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging to write to both file and console
log_file = os.path.join(LOG_DIR, "etl_silver.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Canonical franchise name mapping for renamed IPL teams
TEAM_NAME_MAPPING = {
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Delhi Daredevils": "Delhi Capitals",
    "Kings XI Punjab": "Punjab Kings",
}


def build_silver_layer():
    logger.info("Initializing PySpark Session...")
    spark = (
        SparkSession.builder.appName("IPL_Silver_Layer_ETL")
        .master("local[*]")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    raw_dir = os.path.join(BASE_DIR, "bronze", "cricsheet_raw")
    silver_path = os.path.join(BASE_DIR, "silver", "deliveries")

    # Select ONLY individual numeric match CSVs (excludes *_info.csv and all_matches.csv)
    all_csvs = glob.glob(os.path.join(raw_dir, "*.csv"))
    match_files = [
        f for f in all_csvs
        if os.path.splitext(os.path.basename(f))[0].isdigit()
    ]

    logger.info(f"Found {len(all_csvs)} total CSVs -> Selected {len(match_files)} unique match CSVs.")

    if not match_files:
        logger.error("No valid numeric match CSV files found in bronze/cricsheet_raw.")
        spark.stop()
        return

    # 1. EXTRACT: Read only the individual match CSVs
    df_raw = spark.read.csv(match_files, header=True, inferSchema=True)
    row_count = df_raw.count()
    logger.info(f"Total unique ball-by-ball rows extracted: {row_count:,}")

    # 2. TRANSFORM: Clean data, normalize season, standardize team names, and enforce integer types
    logger.info("Applying transformations (normalizing seasons, standardizing team names, casting integers, filling nulls)...")

    df_clean = df_raw.withColumn("match_id", col("match_id").cast(IntegerType()))

    # Standardize renamed IPL franchise names
    df_clean = df_clean.replace(TEAM_NAME_MAPPING, subset=["batting_team", "bowling_team"])

    # Normalize Cricsheet's 3 slash-formatted seasons to calendar year integers
    df_clean = df_clean.withColumn(
        "season",
        when(col("season").cast("string") == "2007/08", lit(2008))
        .when(col("season").cast("string") == "2009/10", lit(2010))
        .when(col("season").cast("string") == "2020/21", lit(2020))
        .otherwise(col("season").cast(IntegerType())),
    )

    numeric_extra_cols = ["wides", "noballs", "byes", "legbyes", "penalty"]
    for c in numeric_extra_cols:
        df_clean = df_clean.withColumn(c, coalesce(col(c).cast(IntegerType()), lit(0)))

    df_clean = (
        df_clean.withColumn("runs_off_bat", col("runs_off_bat").cast(IntegerType()))
        .withColumn("extras", col("extras").cast(IntegerType()))
        .withColumn("total_runs", col("runs_off_bat") + col("extras"))
        .fillna({"wicket_type": "no_wicket", "player_dismissed": "none"})
    )

    schema_str = df_clean._jdf.schema().treeString()
    logger.info(f"Schema after transformations:\n{schema_str}")

    # 3. LOAD: Write to Parquet in the Silver layer
    logger.info(f"Writing cleaned data to Parquet at: {silver_path} (Partitioned by season)")
    os.makedirs(os.path.dirname(silver_path), exist_ok=True)

    df_clean.write.mode("overwrite").partitionBy("season").parquet(silver_path)

    logger.info("Silver layer ETL complete! Deduplicated and standardized Parquet files generated successfully.")
    logger.info(f"Log saved to: {log_file}")
    spark.stop()


if __name__ == "__main__":
    build_silver_layer()