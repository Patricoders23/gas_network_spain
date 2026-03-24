"""
CORES Collector
Collects gas storage and infrastructure data from CORES (Spain's strategic reserves corpus).
https://www.cores.es/es/estadisticas
"""

import requests
import pandas as pd
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

CORES_BASE_URL = "https://www.cores.es"
RAW_DIR = Path("data/raw")


def fetch_storage_levels(year: int | None = None) -> pd.DataFrame:
    """
    Fetch underground gas storage levels from CORES.

    Args:
        year: Year to retrieve. Defaults to the current year.

    Returns:
        DataFrame with columns: date, storage_name, capacity_gwh, working_gas_gwh, fill_pct.
    """
    import datetime

    year = year or datetime.date.today().year
    logger.info(f"Fetching CORES storage levels for {year}")

    # CORES publishes monthly Excel reports; this stub shows the expected interface.
    # Replace the URL with the actual endpoint or file path when available.
    url = f"{CORES_BASE_URL}/sites/default/files/estadisticas/gas/almacenamientos/{year}_almacenamientos.xlsx"

    try:
        df = pd.read_excel(url, engine="openpyxl")
        logger.info(f"Retrieved {len(df)} rows from CORES storage report")
    except Exception as exc:
        logger.warning(f"Could not fetch CORES Excel ({exc}). Returning empty DataFrame.")
        df = pd.DataFrame(
            columns=["date", "storage_name", "capacity_gwh", "working_gas_gwh", "fill_pct"]
        )

    if not df.empty:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        path = RAW_DIR / f"cores_storage_{year}.parquet"
        df.to_parquet(path, index=False)
        logger.info(f"Saved to {path}")

    return df


def fetch_regasification_terminals() -> pd.DataFrame:
    """
    Return static metadata for Spain's LNG regasification terminals.

    Returns:
        DataFrame with columns: name, operator, location, capacity_gwh_day, lat, lon.
    """
    terminals = [
        {"name": "Barcelona", "operator": "Enagas", "location": "Barcelona", "capacity_gwh_day": 400, "lat": 41.35, "lon": 2.17},
        {"name": "Cartagena", "operator": "Enagas", "location": "Cartagena", "capacity_gwh_day": 400, "lat": 37.60, "lon": -0.99},
        {"name": "Huelva", "operator": "Enagas", "location": "Huelva", "capacity_gwh_day": 400, "lat": 37.25, "lon": -6.95},
        {"name": "Sagunto", "operator": "Enagas", "location": "Valencia", "capacity_gwh_day": 400, "lat": 39.67, "lon": -0.23},
        {"name": "Bilbao", "operator": "Bahia de Bizkaia Gas", "location": "Bilbao", "capacity_gwh_day": 350, "lat": 43.36, "lon": -3.04},
        {"name": "Mugardos", "operator": "Reganosa", "location": "Ferrol", "capacity_gwh_day": 350, "lat": 43.47, "lon": -8.25},
    ]
    return pd.DataFrame(terminals)


if __name__ == "__main__":
    df_storage = fetch_storage_levels()
    df_terminals = fetch_regasification_terminals()
    print(df_terminals)
