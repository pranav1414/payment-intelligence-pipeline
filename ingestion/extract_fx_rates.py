import os
import logging
from datetime import datetime, timedelta

import requests
import pandas as pd
from dotenv import load_dotenv

# ── Load environment variables from .env ──────────────────────────────────
load_dotenv()

# ── Logging setup ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────
APP_ID    = os.getenv("OPEN_EXCHANGE_RATES_APP_ID")
BASE_URL  = "https://openexchangerates.org/api"
CURRENCIES = ["EUR", "GBP", "INR", "CAD", "AUD", "SGD", "JPY"]


def fetch_fx_rates(date: str) -> dict:
    """
    Fetch FX rates for a specific date from Open Exchange Rates API.

    Args:
        date: Date string in YYYY-MM-DD format

    Returns:
        Dictionary of currency -> rate against USD
    """
    url = f"{BASE_URL}/historical/{date}.json"
    params = {
        "app_id": APP_ID,
        "symbols": ",".join(CURRENCIES),
        "base": "USD"
    }

    logger.info(f"Fetching FX rates for {date}...")
    response = requests.get(url, params=params)

    if response.status_code != 200:
        raise Exception(f"API error {response.status_code}: {response.text}")

    data = response.json()
    rates = data.get("rates", {})
    rates["USD"] = 1.0  # USD is always 1.0 against itself

    logger.info(f"✅ Got rates for {date}: {rates}")
    return rates


def generate_fx_dataframe(
    start_date: str = "2024-01-01",
    end_date: str = "2024-12-31",
    sample_days: int = 30
) -> pd.DataFrame:
    """
    Generate FX rates for a sample of days in the date range.
    Free plan limits historical calls so we sample instead of fetching every day.

    Args:
        start_date:  Start date (YYYY-MM-DD)
        end_date:    End date (YYYY-MM-DD)
        sample_days: Number of days to sample

    Returns:
        pd.DataFrame with columns: date, currency, rate_to_usd
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end   = datetime.strptime(end_date,   "%Y-%m-%d")
    delta = (end - start).days

    # Sample evenly spaced dates across the year
    step = max(1, delta // sample_days)
    dates = [
        (start + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(0, delta, step)
    ][:sample_days]

    records = []
    for date in dates:
        try:
            rates = fetch_fx_rates(date)
            for currency, rate in rates.items():
                records.append({
                    "date":        date,
                    "currency":    currency,
                    "rate_to_usd": round(rate, 6)
                })
        except Exception as e:
            logger.error(f"Failed to fetch rates for {date}: {e}")
            continue

    df = pd.DataFrame(records)
    logger.info(f"✅ Generated FX rates: {len(df)} records across {len(dates)} dates")
    return df


def save_to_csv(df: pd.DataFrame, output_path: str) -> None:
    """Save FX rates DataFrame to CSV."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"💾 Saved to {output_path}")


if __name__ == "__main__":
    # Fetch FX rates for 30 sample days across 2024
    df = generate_fx_dataframe(
        start_date="2024-01-01",
        end_date="2024-12-31",
        sample_days=30
    )

    print("\n── Sample FX Rates ──────────────────────────────")
    print(df.head(10).to_string())
    print(f"\n── Shape: {df.shape}")

    # Save locally
    save_to_csv(df, "data/raw_fx_rates.csv")