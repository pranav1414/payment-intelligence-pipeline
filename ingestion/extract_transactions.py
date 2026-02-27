import uuid
import random
import logging
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

# ── Logging setup ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ── Faker init ─────────────────────────────────────────────────────────────
fake = Faker()
Faker.seed(42)
random.seed(42)

# ── Constants ──────────────────────────────────────────────────────────────
MERCHANT_CATEGORIES = [
    "groceries", "restaurants", "travel", "entertainment",
    "healthcare", "retail", "utilities", "subscriptions",
    "fuel", "education"
]

PAYMENT_METHODS = ["credit_card", "debit_card", "bank_transfer", "digital_wallet"]

CURRENCIES = ["USD", "EUR", "GBP", "INR", "CAD", "AUD", "SGD", "JPY"]

STATUSES = ["completed", "completed", "completed", "failed", "pending"]
# completed weighted higher — reflects real-world distribution

AMOUNT_RANGES = {
    "groceries":     (10, 200),
    "restaurants":   (5, 150),
    "travel":        (50, 2000),
    "entertainment": (10, 300),
    "healthcare":    (20, 500),
    "retail":        (15, 800),
    "utilities":     (30, 400),
    "subscriptions": (5, 50),
    "fuel":          (20, 150),
    "education":     (50, 1000),
}


def generate_transaction(transaction_date: datetime) -> dict:
    """Generate a single realistic payment transaction."""
    category = random.choice(MERCHANT_CATEGORIES)
    min_amt, max_amt = AMOUNT_RANGES[category]

    return {
        "transaction_id":   str(uuid.uuid4()),
        "transaction_date": transaction_date.strftime("%Y-%m-%d"),
        "transaction_time": transaction_date.strftime("%H:%M:%S"),
        "customer_id":      str(uuid.uuid4()),
        "merchant_name":    fake.company(),
        "merchant_category": category,
        "amount":           round(random.uniform(min_amt, max_amt), 2),
        "currency":         random.choice(CURRENCIES),
        "payment_method":   random.choice(PAYMENT_METHODS),
        "status":           random.choice(STATUSES),
        "country":          fake.country_code(),
        "city":             fake.city(),
        "is_flagged":       random.random() < 0.02,  # 2% flagged as suspicious
    }


def generate_transactions(
    num_records: int = 1000,
    start_date: str = "2024-01-01",
    end_date: str = "2024-12-31"
) -> pd.DataFrame:
    """
    Generate a batch of synthetic payment transactions.

    Args:
        num_records: Number of transactions to generate
        start_date:  Start of date range (YYYY-MM-DD)
        end_date:    End of date range (YYYY-MM-DD)

    Returns:
        pd.DataFrame with all generated transactions
    """
    logger.info(f"Generating {num_records} transactions from {start_date} to {end_date}...")

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end   = datetime.strptime(end_date,   "%Y-%m-%d")
    delta = (end - start).days

    transactions = []
    for _ in range(num_records):
        # Random timestamp within the date range
        random_days    = random.randint(0, delta)
        random_seconds = random.randint(0, 86400)
        txn_datetime   = start + timedelta(days=random_days, seconds=random_seconds)
        transactions.append(generate_transaction(txn_datetime))

    df = pd.DataFrame(transactions)

    logger.info(f"✅ Generated {len(df)} transactions")
    logger.info(f"   Date range : {df['transaction_date'].min()} → {df['transaction_date'].max()}")
    logger.info(f"   Categories : {df['merchant_category'].nunique()} unique")
    logger.info(f"   Currencies : {df['currency'].nunique()} unique")
    logger.info(f"   Flagged    : {df['is_flagged'].sum()} suspicious transactions")

    return df


def save_to_csv(df: pd.DataFrame, output_path: str) -> None:
    """Save transactions DataFrame to CSV."""
    df.to_csv(output_path, index=False)
    logger.info(f"💾 Saved to {output_path}")


if __name__ == "__main__":
    # Generate 10,000 transactions for full year 2024
    df = generate_transactions(
        num_records=10_000,
        start_date="2024-01-01",
        end_date="2024-12-31"
    )

    # Preview
    print("\n── Sample Transactions ──────────────────────────")
    print(df.head(3).to_string())
    print(f"\n── Shape: {df.shape}")
    print(f"── Columns: {list(df.columns)}")

    # Save locally first (before GCS upload in next step)
    save_to_csv(df, "data/raw_transactions.csv")