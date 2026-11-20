import os
import sys
import zipfile
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

# Anchor paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Load .env from project root
load_dotenv(os.path.join(ROOT_DIR, ".env"))

# Configure logging
log_file = os.path.join(LOG_DIR, "upload_to_s3.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def s3_object_exists(s3_client, bucket: str, key: str) -> bool:
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


def clear_s3_prefix(s3_client, bucket: str, prefix: str):
    """Deletes stale objects under a prefix so Spark's new UUID Parquet files don't pile up."""
    paginator = s3_client.get_paginator("list_objects_v2")
    to_delete = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            to_delete.append({"Key": obj["Key"]})

    if not to_delete:
        return

    # S3 delete_objects accepts up to 1,000 keys per call
    for i in range(0, len(to_delete), 1000):
        s3_client.delete_objects(Bucket=bucket, Delete={"Objects": to_delete[i : i + 1000]})
    logger.info(f"Cleared {len(to_delete)} stale objects under s3://{bucket}/{prefix}")


def zip_bronze_layer(bronze_dir: str, zip_path: str):
    logger.info(f"Compressing Bronze CSVs into single archive: {zip_path}")
    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(bronze_dir):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, bronze_dir)
                zf.write(full_path, arcname)
                file_count += 1
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    logger.info(f"Compressed {file_count} Bronze files into {size_mb:.2f} MB archive.")


def upload_directory(s3_client, local_dir: str, bucket: str, s3_prefix: str) -> int:
    uploaded = 0
    for root, _, files in os.walk(local_dir):
        for file in files:
            if file.endswith(".crc") or file == "_SUCCESS":
                continue
            local_path = os.path.join(root, file)
            rel_path = os.path.relpath(local_path, local_dir).replace("\\", "/")
            s3_key = f"{s3_prefix}/{rel_path}"
            s3_client.upload_file(local_path, bucket, s3_key)
            uploaded += 1
    logger.info(f"Uploaded {uploaded} files to s3://{bucket}/{s3_prefix}/")
    return uploaded


def sync_lake_to_s3(force_bronze: bool = False):
    bucket = os.getenv("AWS_S3_BUCKET")
    region = os.getenv("AWS_REGION", "ap-south-1")

    if not bucket:
        logger.error("AWS_S3_BUCKET is not set in .env file.")
        return

    logger.info(f"Connecting to S3 bucket '{bucket}' in region '{region}'...")
    try:
        s3_client = boto3.client("s3", region_name=region)
        s3_client.head_bucket(Bucket=bucket)
    except NoCredentialsError:
        logger.error("AWS credentials not found. Run 'aws configure' in cmd first.")
        return
    except ClientError as e:
        logger.error(f"Cannot access bucket '{bucket}': {e}")
        return

    total_puts = 0

    # 1. Bronze Layer (skip if already in S3 unless --force-bronze is passed)
    bronze_key = "bronze/cricsheet_raw.zip"
    bronze_raw_dir = os.path.join(BASE_DIR, "bronze", "cricsheet_raw")
    bronze_zip_path = os.path.join(BASE_DIR, "bronze", "cricsheet_raw.zip")

    if force_bronze or not s3_object_exists(s3_client, bucket, bronze_key):
        if os.path.exists(bronze_raw_dir):
            zip_bronze_layer(bronze_raw_dir, bronze_zip_path)
            s3_client.upload_file(bronze_zip_path, bucket, bronze_key)
            logger.info(f"Uploaded Bronze archive to s3://{bucket}/{bronze_key}")
            total_puts += 1
    else:
        logger.info(f"Skipping Bronze: s3://{bucket}/{bronze_key} already exists (use --force-bronze to re-upload).")

    # 2. Silver Layer (clear stale files, then upload)
    silver_dir = os.path.join(BASE_DIR, "silver", "deliveries")
    if os.path.exists(silver_dir):
        clear_s3_prefix(s3_client, bucket, "silver/deliveries/")
        total_puts += upload_directory(s3_client, silver_dir, bucket, "silver/deliveries")

    # 3. Gold Layer (clear stale files, then upload)
    gold_dir = os.path.join(BASE_DIR, "gold")
    if os.path.exists(gold_dir):
        clear_s3_prefix(s3_client, bucket, "gold/")
        total_puts += upload_directory(s3_client, gold_dir, bucket, "gold")

    logger.info(f"S3 Data Lake sync complete! Total PUT requests used: {total_puts}")
    logger.info(f"Log saved to: {log_file}")


if __name__ == "__main__":
    force = "--force-bronze" in sys.argv
    sync_lake_to_s3(force_bronze=force)