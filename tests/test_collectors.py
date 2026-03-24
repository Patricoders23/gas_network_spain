"""
Tests for src/collectors/*
External API calls are mocked to avoid network dependencies in CI.
"""

from unittest.mock import patch, MagicMock
import pandas as pd
import pytest

from src.collectors.cores_collector import fetch_regasification_terminals
from src.collectors.eurostat_collector import _parse_jsonstat


# ---------------------------------------------------------------------------
# CORES collector
# ---------------------------------------------------------------------------

def test_fetch_regasification_terminals_returns_dataframe():
    df = fetch_regasification_terminals()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "name" in df.columns
    assert "capacity_gwh_day" in df.columns


def test_terminals_have_coordinates():
    df = fetch_regasification_terminals()
    assert df["lat"].notna().all()
    assert df["lon"].notna().all()


def test_six_terminals_returned():
    df = fetch_regasification_terminals()
    assert len(df) == 6


# ---------------------------------------------------------------------------
# Eurostat collector
# ---------------------------------------------------------------------------

def test_parse_jsonstat_valid():
    raw = {
        "id": ["geo", "time"],
        "size": [2, 2],
        "dimension": {
            "geo":  {"category": {"index": {"ES": 0, "EU": 1}, "label": {"ES": "Spain", "EU": "EU27"}}},
            "time": {"category": {"index": {"2023-01": 0, "2023-02": 1}, "label": {"2023-01": "Jan 2023", "2023-02": "Feb 2023"}}},
        },
        "value": {"0": 100.0, "1": 110.0, "2": 90.0, "3": 95.0},
    }
    df = _parse_jsonstat(raw)
    assert not df.empty
    assert "geo" in df.columns
    assert "time" in df.columns
    assert "value" in df.columns


def test_parse_jsonstat_malformed_returns_empty():
    df = _parse_jsonstat({"broken": True})
    assert df.empty


# ---------------------------------------------------------------------------
# ENTSOG collector (mocked HTTP)
# ---------------------------------------------------------------------------

@patch("src.collectors.entsog_collector.requests.get")
def test_fetch_interconnections_mocked(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "connectionPoints": [
            {"id": "ITP-00552", "fromCountryKey": "ES", "toCountryKey": "FR", "name": "Irún"},
            {"id": "ITP-00553", "fromCountryKey": "DZ", "toCountryKey": "ES", "name": "Medgaz"},
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    from src.collectors.entsog_collector import fetch_interconnections
    df = fetch_interconnections()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
