"""Tests for src/graph/flow_analyzer.py"""

import networkx as nx
import pytest

from src.graph.flow_analyzer import (
    compute_max_flow,
    compute_centrality,
    supply_demand_balance,
)


@pytest.fixture
def simple_graph():
    G = nx.DiGraph()
    G.add_node("S", node_type="interconnection", lat=43.0, lon=-1.0, capacity_gwh_day=500)
    G.add_node("M", node_type="compressor",      lat=40.0, lon=-3.0, capacity_gwh_day=0)
    G.add_node("T", node_type="distribution",    lat=37.0, lon=-6.0, capacity_gwh_day=0)
    G.add_edge("S", "M", capacity_gwh_day=400, length_km=300, operator="Test")
    G.add_edge("M", "T", capacity_gwh_day=300, length_km=500, operator="Test")
    return G


def test_max_flow_basic(simple_graph):
    flow_val, flow_dict = compute_max_flow(simple_graph, "S", "T")
    assert flow_val == pytest.approx(300)
    assert "S" in flow_dict


def test_max_flow_no_path():
    G = nx.DiGraph()
    G.add_node("A", capacity_gwh_day=100)
    G.add_node("B", capacity_gwh_day=100)
    # No edge between A and B
    assert not nx.has_path(G, "A", "B")


def test_compute_centrality(simple_graph):
    df = compute_centrality(simple_graph)
    assert not df.empty
    assert "node" in df.columns
    assert "centrality" in df.columns
    # Middle node should have highest centrality in a linear graph
    assert df.iloc[0]["node"] == "M"


def test_supply_demand_balance(simple_graph):
    result = supply_demand_balance(simple_graph, supply_nodes=["S"], demand_nodes=["T"])
    assert result["total_supply_gwh_day"] == 500
    assert result["surplus"] is True


def test_supply_demand_deficit(simple_graph):
    simple_graph.nodes["S"]["capacity_gwh_day"] = 100
    simple_graph.nodes["T"]["capacity_gwh_day"] = 500
    result = supply_demand_balance(simple_graph, supply_nodes=["S"], demand_nodes=["T"])
    assert result["balance_gwh_day"] == -400
    assert result["surplus"] is False
