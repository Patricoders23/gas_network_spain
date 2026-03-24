"""
Eurostat Collector
Fetches European gas supply/demand statistics via the Eurostat REST API.
https://ec.europa.eu/eurostat/web/json-and-unicode-web-services
"""

import requests
import pandas as pd
from pathlib import Path
from loguru import logger

BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
RAW_DIR = Path("data/raw")

# Key Eurostat dataset codes for gas
DATASETS = {
    "gas_supply_demand": "nrg_cb_gasm",   # Monthly gas supply/demand
    "gas_storage":       "nrg_stk_gasm",  # Monthly gas storage statistics
    "gas_trade":         "nrg_ti_gasm",   # Monthly gas trade by partner country
}


def fetch_dataset(
    dataset_code: str,
    geo: list[str] | None = None,
    since_period: str = "2020-01",
    save: bool = True,
) -> pd.DataFrame:
    """
    Fetch a Eurostat dataset in JSON-stat format and return a tidy DataFrame.

    Args:
        dataset_code: Eurostat dataset code (e.g. 'nrg_cb_gasm').
        geo: List of country codes to filter (e.g. ['ES', 'EU27_2020']).
        since_period: ISO period string (YYYY-MM or YYYY) for the start filter.
        save: Whether to cache results locally.

    Returns:
        Tidy DataFrame with columns: geo, time, indicator, value.
    """
    geo = geo or ["ES", "EU27_2020"]
    params: dict = {
        "format": "JSON",
        "lang": "EN",
        "sinceTimePeriod": since_period,
        "geo": geo,
    }

    logger.info(f"Fetching Eurostat dataset {dataset_code} for geo={geo}")
    response = requests.get(f"{BASE_URL}/{dataset_code}", params=params, timeout=120)
    response.raise_for_status()
    raw = response.json()

    df = _parse_jsonstat(raw)

    if save and not df.empty:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        path = RAW_DIR / f"eurostat_{dataset_code}.parquet"
        df.to_parquet(path, index=False)
        logger.info(f"Saved {len(df)} rows to {path}")

    return df


def _parse_jsonstat(raw: dict) -> pd.DataFrame:
    """Convert a Eurostat JSON-stat response into a tidy DataFrame."""
    try:
        dimension = raw["dimension"]
        values = raw["value"]
        size = raw["size"]
        ids = raw["id"]

        labels = {dim: list(dimension[dim]["category"]["label"].values()) for dim in ids}
        index_keys = {dim: list(dimension[dim]["category"]["index"].keys()) for dim in ids}

        import itertools

        combos = list(itertools.product(*[index_keys[d] for d in ids]))
        rows = []
        for i, combo in enumerate(combos):
            row = dict(zip(ids, combo))
            row["value"] = values.get(str(i))
            rows.append(row)

        return pd.DataFrame(rows)
    except Exception as exc:
        logger.warning(f"Could not parse JSON-stat response: {exc}")
        return pd.DataFrame()


def fetch_gas_supply_demand_spain(since_period: str = "2020-01") -> pd.DataFrame:
    """Convenience wrapper: gas supply/demand for Spain."""
    return fetch_dataset(DATASETS["gas_supply_demand"], geo=["ES"], since_period=since_period)


def fetch_gas_storage_spain(since_period: str = "2020-01") -> pd.DataFrame:
    """Convenience wrapper: gas storage statistics for Spain."""
    return fetch_dataset(DATASETS["gas_storage"], geo=["ES"], since_period=since_period)


if __name__ == "__main__":
    df = fetch_gas_supply_demand_spain()
    print(df.head())
