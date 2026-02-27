import logging
from datetime import datetime

from google.cloud import bigquery

# ── Logging setup ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────
PROJECT_ID   = "payment-intelligence-488700"
DATASET_ID   = "payments_raw"
TABLE_ID     = "raw_transactions"
BUCKET_NAME  = "payment-intelligence-pipeline"


def create_dataset_if_not_exists(client: bigquery.Client) -> None:
    """Create BigQuery dataset if it doesn't already exist."""
    dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"
    try:
        client.get_dataset(dataset_ref)
        logger.info(f"Dataset {DATASET_ID} already exists")
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        client.create_dataset(dataset)
        logger.info(f"✅ Created dataset: {DATASET_ID}")


def load_gcs_to_bigquery() -> None:
    """
    Load the latest CSV from GCS into BigQuery using WRITE_TRUNCATE.
    This means each run replaces the table — idempotent and safe to re-run.
    """
    client = bigquery.Client(project=PROJECT_ID)

    # ── Step 1: Ensure dataset exists ─────────────────────────────────────
    create_dataset_if_not_exists(client)

    # ── Step 2: Build GCS source path (today's partition) ─────────────────
    today = datetime.utcnow()
    gcs_uri = (
        f"gs://{BUCKET_NAME}/transactions/"
        f"year={today.year}/"
        f"month={today.month:02d}/"
        f"day={today.day:02d}/"
        f"raw_transactions.csv"
    )
    logger.info(f"Loading from: {gcs_uri}")

    # ── Step 3: Define table schema ────────────────────────────────────────
    schema = [
        bigquery.SchemaField("transaction_id",    "STRING",    mode="REQUIRED"),
        bigquery.SchemaField("transaction_date",  "DATE",      mode="NULLABLE"),
        bigquery.SchemaField("transaction_time",  "STRING",    mode="NULLABLE"),
        bigquery.SchemaField("customer_id",       "STRING",    mode="NULLABLE"),
        bigquery.SchemaField("merchant_name",     "STRING",    mode="NULLABLE"),
        bigquery.SchemaField("merchant_category", "STRING",    mode="NULLABLE"),
        bigquery.SchemaField("amount",            "FLOAT64",   mode="NULLABLE"),
        bigquery.SchemaField("currency",          "STRING",    mode="NULLABLE"),
        bigquery.SchemaField("payment_method",    "STRING",    mode="NULLABLE"),
        bigquery.SchemaField("status",            "STRING",    mode="NULLABLE"),
        bigquery.SchemaField("country",           "STRING",    mode="NULLABLE"),
        bigquery.SchemaField("city",              "STRING",    mode="NULLABLE"),
        bigquery.SchemaField("is_flagged",        "BOOLEAN",   mode="NULLABLE"),
    ]

    # ── Step 4: Configure the load job ────────────────────────────────────
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,          # skip the header row
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        # WRITE_TRUNCATE = replace table on each run (idempotent)
        # Alternative: WRITE_APPEND = add rows on each run
    )

    # ── Step 5: Run the load job ───────────────────────────────────────────
    logger.info(f"Loading into BigQuery table: {table_ref}")
    load_job = client.load_table_from_uri(gcs_uri, table_ref, job_config=job_config)
    load_job.result()  # wait for the job to complete

    # ── Step 6: Verify ────────────────────────────────────────────────────
    table = client.get_table(table_ref)
    logger.info(f"✅ Load complete!")
    logger.info(f"   Table : {table_ref}")
    logger.info(f"   Rows  : {table.num_rows:,}")
    logger.info(f"   Size  : {table.num_bytes / 1024:.1f} KB")


if __name__ == "__main__":
    load_gcs_to_bigquery()