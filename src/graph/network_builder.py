"""
Network Builder
Constructs a NetworkX graph of Spain's gas transmission network from
infrastructure metadata and ENTSOG interconnection point data.
"""

import json
from pathlib import Path

import networkx as nx
import pandas as pd
import geopandas as gpd
from loguru import logger

PROCESSED_DIR = Path("data/processed")


def build_network(
    nodes_df: pd.DataFrame | None = None,
    edges_df: pd.DataFrame | None = None,
) -> nx.DiGraph:
    """
    Build a directed graph of the Spanish gas network.

    Expected node columns : id, name, type, lat, lon, capacity_gwh_day
    Expected edge columns : source, target, capacity_gwh_day, length_km, operator

    If DataFrames are not provided, falls back to bundled static data.

    Returns:
        Directed NetworkX graph with node/edge attributes.
    """
    G = nx.DiGraph()

    nodes_df = nodes_df if nodes_df is not None else _default_nodes()
    edges_df = edges_df if edges_df is not None else _default_edges()

    for _, row in nodes_df.iterrows():
        G.add_node(
            row["id"],
            name=row.get("name", row["id"]),
            node_type=row.get("type", "compressor"),
            lat=row.get("lat"),
            lon=row.get("lon"),
            capacity_gwh_day=row.get("capacity_gwh_day", 0.0),
        )

    for _, row in edges_df.iterrows():
        G.add_edge(
            row["source"],
            row["target"],
            capacity_gwh_day=row.get("capacity_gwh_day", 0.0),
            length_km=row.get("length_km", 0.0),
            operator=row.get("operator", "Enagas"),
        )

    logger.info(f"Network built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def save_network(G: nx.DiGraph, name: str = "gas_network") -> Path:
    """Persist the graph as GraphML and node/edge CSVs."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = PROCESSED_DIR / f"{name}.graphml"
    nx.write_graphml(G, path)
    logger.info(f"Graph saved to {path}")
    return path


def load_network(name: str = "gas_network") -> nx.DiGraph:
    """Load a previously saved graph."""
    path = PROCESSED_DIR / f"{name}.graphml"
    G = nx.read_graphml(path)
    logger.info(f"Graph loaded from {path}: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


# ---------------------------------------------------------------------------
# Static seed data (placeholder until real data pipeline is connected)
# ---------------------------------------------------------------------------

def _default_nodes() -> pd.DataFrame:
    data = [
        {"id": "BAR_LNG", "name": "Terminal GNL Barcelona", "type": "lng_terminal", "lat": 41.35, "lon": 2.17, "capacity_gwh_day": 400},
        {"id": "CAR_LNG", "name": "Terminal GNL Cartagena", "type": "lng_terminal", "lat": 37.60, "lon": -0.99, "capacity_gwh_day": 400},
        {"id": "HUE_LNG", "name": "Terminal GNL Huelva",    "type": "lng_terminal", "lat": 37.25, "lon": -6.95, "capacity_gwh_day": 400},
        {"id": "SAG_LNG", "name": "Terminal GNL Sagunto",   "type": "lng_terminal", "lat": 39.67, "lon": -0.23, "capacity_gwh_day": 400},
        {"id": "BIL_LNG", "name": "Terminal GNL Bilbao",    "type": "lng_terminal", "lat": 43.36, "lon": -3.04, "capacity_gwh_day": 350},
        {"id": "MUG_LNG", "name": "Terminal GNL Mugardos",  "type": "lng_terminal", "lat": 43.47, "lon": -8.25, "capacity_gwh_day": 350},
        {"id": "IRU_ICP", "name": "Interconexión Irún (FR-ES)", "type": "interconnection", "lat": 43.35, "lon": -1.79, "capacity_gwh_day": 530},
        {"id": "LAR_ICP", "name": "Interconexión Larrau (FR-ES)", "type": "interconnection", "lat": 42.98, "lon": -0.73, "capacity_gwh_day": 180},
        {"id": "BAD_ICP", "name": "Interconexión Badajoz (PT-ES)", "type": "interconnection", "lat": 38.88, "lon": -7.01, "capacity_gwh_day": 110},
        {"id": "TUN_ICP", "name": "Medgaz (DZ-ES Almería)", "type": "interconnection", "lat": 36.83, "lon": -2.47, "capacity_gwh_day": 800},
        {"id": "MAD_CMP", "name": "Compresor Madrid",  "type": "compressor", "lat": 40.42, "lon": -3.70, "capacity_gwh_day": 0},
        {"id": "ZAR_CMP", "name": "Compresor Zaragoza","type": "compressor", "lat": 41.65, "lon": -0.89, "capacity_gwh_day": 0},
        {"id": "ALM_STG", "name": "Almacenamiento Yela", "type": "storage", "lat": 40.97, "lon": -2.72, "capacity_gwh_day": 200},
        {"id": "SEV_DST", "name": "Zona distribución Sevilla", "type": "distribution", "lat": 37.38, "lon": -5.97, "capacity_gwh_day": 0},
    ]
    return pd.DataFrame(data)


def _default_edges() -> pd.DataFrame:
    data = [
        {"source": "IRU_ICP", "target": "ZAR_CMP", "capacity_gwh_day": 530, "length_km": 340, "operator": "Enagas"},
        {"source": "LAR_ICP", "target": "ZAR_CMP", "capacity_gwh_day": 180, "length_km": 120, "operator": "Enagas"},
        {"source": "ZAR_CMP", "target": "MAD_CMP", "capacity_gwh_day": 700, "length_km": 300, "operator": "Enagas"},
        {"source": "ZAR_CMP", "target": "BAR_LNG", "capacity_gwh_day": 400, "length_km": 280, "operator": "Enagas"},
        {"source": "MAD_CMP", "target": "ALM_STG", "capacity_gwh_day": 300, "length_km": 130, "operator": "Enagas"},
        {"source": "MAD_CMP", "target": "SEV_DST", "capacity_gwh_day": 500, "length_km": 540, "operator": "Enagas"},
        {"source": "HUE_LNG", "target": "SEV_DST", "capacity_gwh_day": 400, "length_km": 80, "operator": "Enagas"},
        {"source": "TUN_ICP", "target": "MAD_CMP", "capacity_gwh_day": 800, "length_km": 620, "operator": "Enagas"},
        {"source": "BAD_ICP", "target": "MAD_CMP", "capacity_gwh_day": 110, "length_km": 400, "operator": "Enagas"},
        {"source": "CAR_LNG", "target": "MAD_CMP", "capacity_gwh_day": 400, "length_km": 450, "operator": "Enagas"},
        {"source": "SAG_LNG", "target": "ZAR_CMP", "capacity_gwh_day": 400, "length_km": 300, "operator": "Enagas"},
        {"source": "BIL_LNG", "target": "IRU_ICP", "capacity_gwh_day": 350, "length_km": 90, "operator": "Enagas"},
        {"source": "MUG_LNG", "target": "IRU_ICP", "capacity_gwh_day": 350, "length_km": 580, "operator": "Enagas"},
    ]
    return pd.DataFrame(data)
