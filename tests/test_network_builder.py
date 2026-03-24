"""Tests for src/graph/network_builder.py"""

import networkx as nx
import pytest

from src.graph.network_builder import build_network, _default_nodes, _default_edges


def test_build_network_returns_digraph():
    G = build_network()
    assert isinstance(G, nx.DiGraph)


def test_build_network_has_nodes_and_edges():
    G = build_network()
    assert G.number_of_nodes() > 0
    assert G.number_of_edges() > 0


def test_node_attributes_present():
    G = build_network()
    for node, data in G.nodes(data=True):
        assert "node_type" in data, f"Node {node} missing 'node_type'"
        assert "lat" in data, f"Node {node} missing 'lat'"
        assert "lon" in data, f"Node {node} missing 'lon'"


def test_edge_attributes_present():
    G = build_network()
    for u, v, data in G.edges(data=True):
        assert "capacity_gwh_day" in data, f"Edge {u}→{v} missing 'capacity_gwh_day'"


def test_default_nodes_dataframe():
    df = _default_nodes()
    assert not df.empty
    required_cols = {"id", "name", "type", "lat", "lon", "capacity_gwh_day"}
    assert required_cols.issubset(df.columns)


def test_default_edges_dataframe():
    df = _default_edges()
    assert not df.empty
    required_cols = {"source", "target", "capacity_gwh_day"}
    assert required_cols.issubset(df.columns)


def test_build_network_with_custom_data():
    import pandas as pd
    nodes = pd.DataFrame([
        {"id": "A", "name": "Node A", "type": "compressor", "lat": 40.0, "lon": -3.0, "capacity_gwh_day": 100},
        {"id": "B", "name": "Node B", "type": "distribution", "lat": 41.0, "lon": -2.0, "capacity_gwh_day": 50},
    ])
    edges = pd.DataFrame([
        {"source": "A", "target": "B", "capacity_gwh_day": 80, "length_km": 100, "operator": "Test"},
    ])
    G = build_network(nodes_df=nodes, edges_df=edges)
    assert G.number_of_nodes() == 2
    assert G.number_of_edges() == 1
    assert G["A"]["B"]["capacity_gwh_day"] == 80
