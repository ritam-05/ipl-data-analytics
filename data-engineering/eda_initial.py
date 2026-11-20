import os
import glob
import logging
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, "eda_initial.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_initial_eda():
    raw_data_dir = os.path.join(BASE_DIR, "bronze", "cricsheet_raw")

    if not os.path.exists(raw_data_dir):
        logger.error(f"Directory '{raw_data_dir}' not found. Please extract the Cricsheet zip here.")
        return

    csv_files = glob.glob(os.path.join(raw_data_dir, "*.csv"))
    logger.info("--- DATASET OVERVIEW ---")
    logger.info(f"Total CSV files found: {len(csv_files)}")

    if len(csv_files) == 0:
        logger.warning("No CSV files found. Please make sure you extracted the files correctly.")
        return

    sample_file = csv_files[0]
    logger.info(f"--- INSPECTING SAMPLE FILE: {os.path.basename(sample_file)} ---")

    try:
        df = pd.read_csv(sample_file)
        logger.info(f"\n1. Data Types and Schema:\n{df.dtypes}")
        logger.info(f"\n2. First 5 Rows of Ball-by-Ball Data:\n{df.head()}")
        logger.info(f"\n3. Missing Values Summary:\n{df.isnull().sum()[df.isnull().sum() > 0]}")

        if "wicket_type" in df.columns:
            logger.info(f"\n4. Unique Wicket Types:\n{df['wicket_type'].dropna().unique()}")

        logger.info(f"EDA log saved to: {log_file}")
    except Exception as e:
        logger.error(f"Error reading {sample_file}: {e}")


if __name__ == "__main__":
    run_initial_eda()