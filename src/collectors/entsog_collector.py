"""
ENTSOG Collector
Collects gas flow data from the ENTSOG Transparency Platform API.
https://transparency.entsog.eu/api/archiveFullView
"""

import requests
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://transparency.entsog.eu/api/v1"
RAW_DIR = Path("data/raw")


def fetch_operational_data(
    from_date: date,
    to_date: date,
    indicator: str = "Physical Flow",
    save: bool = True,
) -> pd.DataFrame:
    """
    Fetch operational point data from ENTSOG for a given date range.

    Args:
        from_date: Start date.
        to_date: End date.
        indicator: One of 'Physical Flow', 'Nomination', 'Allocation', etc.
        save: Whether to persist raw JSON to data/raw/.

    Returns:
        DataFrame with columns: pointKey, pointLabel, operatorKey, date, value, unit.
    """
    params = {
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "indicator": indicator,
        "periodType": "day",
        "timezone": "CET",
        "limit": 10000,
        "offset": 0,
    }

    records = []
    while True:
        logger.info(f"Fetching ENTSOG data offset={params['offset']}")
        response = requests.get(f"{BASE_URL}/operationaldata", params=params, timeout=60)
        response.raise_for_status()
        payload = response.json()

        batch = payload.get("operationalData", [])
        if not batch:
            break

        records.extend(batch)
        if len(batch) < params["limit"]:
            break
        params["offset"] += params["limit"]

    df = pd.DataFrame(records)

    if save and not df.empty:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        path = RAW_DIR / f"entsog_{from_date}_{to_date}.parquet"
        df.to_parquet(path, index=False)
        logger.info(f"Saved {len(df)} rows to {path}")

    return df


def fetch_interconnections() -> pd.DataFrame:
    """Return the list of ENTSOG interconnection points relevant to Spain."""
    logger.info("Fetching ENTSOG interconnection points")
    response = requests.get(f"{BASE_URL}/connectionpoints", timeout=60)
    response.raise_for_status()
    data = response.json().get("connectionPoints", [])
    df = pd.DataFrame(data)
    # Filter Spain-related points (country codes ES, PT-ES border, FR-ES border)
    if "fromCountryKey" in df.columns:
        mask = df["fromCountryKey"].isin(["ES", "PT", "FR", "MA"]) | df["toCountryKey"].isin(["ES"])
        df = df[mask].copy()
    return df


if __name__ == "__main__":
    today = date.today()
    df = fetch_operational_data(today - timedelta(days=7), today)
    print(df.head())
