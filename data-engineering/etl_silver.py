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
    "Rising Pune Supergiants": "Rising Pune Supergiant",
}

# Canonical venue name mapping (merges renamed stadiums & city-suffix duplicates)
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

    # 2. TRANSFORM: Clean data, normalize season, standardize team & venue names, cast integers
    logger.info("Applying transformations (normalizing seasons, teams, venues, and integer types)...")

    df_clean = df_raw.withColumn("match_id", col("match_id").cast(IntegerType()))

    # Standardize renamed IPL franchise names and stadium names
    df_clean = df_clean.replace(TEAM_NAME_MAPPING, subset=["batting_team", "bowling_team"])
    df_clean = df_clean.replace(VENUE_NAME_MAPPING, subset=["venue"])

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