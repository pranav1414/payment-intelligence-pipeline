import os
import logging
from datetime import datetime

from google.cloud import storage

# ── Logging setup ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────
BUCKET_NAME = "payment-intelligence-pipeline"


def upload_to_gcs(local_file_path: str, gcs_folder: str) -> str:
    """
    Upload a local file to Google Cloud Storage.

    Args:
        local_file_path: Path to the local file e.g. 'data/raw_transactions.csv'
        gcs_folder:      Folder name inside the bucket e.g. 'transactions'

    Returns:
        Full GCS path of the uploaded file
    """
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    # Build the destination path with date partitioning
    # e.g. transactions/year=2026/month=02/day=26/raw_transactions.csv
    today = datetime.utcnow()
    filename = os.path.basename(local_file_path)
    gcs_path = (
        f"{gcs_folder}/"
        f"year={today.year}/"
        f"month={today.month:02d}/"
        f"day={today.day:02d}/"
        f"{filename}"
    )

    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(local_file_path)

    full_gcs_path = f"gs://{BUCKET_NAME}/{gcs_path}"
    logger.info(f"✅ Uploaded {local_file_path} → {full_gcs_path}")

    return full_gcs_path


if __name__ == "__main__":
    # Upload transactions CSV
    upload_to_gcs(
        local_file_path="data/raw_transactions.csv",
        gcs_folder="transactions"
    )