"""
Flow Analyzer
Computes gas flow metrics over the NetworkX graph: max-flow, centrality,
bottleneck detection, and supply/demand balance.
"""

import networkx as nx
import pandas as pd
from loguru import logger


def compute_max_flow(
    G: nx.DiGraph,
    source: str,
    sink: str,
    capacity_attr: str = "capacity_gwh_day",
) -> tuple[float, dict]:
    """
    Compute maximum flow between source and sink nodes.

    Returns:
        (flow_value, flow_dict) — total flow and per-edge allocations.
    """
    logger.info(f"Computing max-flow from '{source}' to '{sink}'")
    flow_value, flow_dict = nx.maximum_flow(G, source, sink, capacity=capacity_attr)
    logger.info(f"Max flow {source} → {sink}: {flow_value:.1f} GWh/day")
    return flow_value, flow_dict


def detect_bottlenecks(
    G: nx.DiGraph,
    capacity_attr: str = "capacity_gwh_day",
    threshold_pct: float = 0.9,
) -> pd.DataFrame:
    """
    Identify edges whose capacity utilisation exceeds threshold_pct in any
    max-flow scenario (source = each LNG/interconnection node, sink = each
    distribution node).

    Returns:
        DataFrame with columns: source, target, capacity, flow, utilisation_pct.
    """
    source_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") in ("lng_terminal", "interconnection")]
    sink_nodes   = [n for n, d in G.nodes(data=True) if d.get("node_type") == "distribution"]

    edge_max_util: dict[tuple, float] = {}

    for src in source_nodes:
        for snk in sink_nodes:
            if src == snk or not nx.has_path(G, src, snk):
                continue
            _, flow_dict = compute_max_flow(G, src, snk, capacity_attr)
            for u in flow_dict:
                for v, flow in flow_dict[u].items():
                    cap = G[u][v].get(capacity_attr, 1)
                    util = flow / cap if cap > 0 else 0.0
                    key = (u, v)
                    edge_max_util[key] = max(edge_max_util.get(key, 0.0), util)

    rows = []
    for (u, v), util in edge_max_util.items():
        if util >= threshold_pct:
            rows.append({
                "source": u,
                "target": v,
                "capacity_gwh_day": G[u][v].get(capacity_attr, 0),
                "max_utilisation_pct": round(util * 100, 1),
            })

    df = pd.DataFrame(rows).sort_values("max_utilisation_pct", ascending=False)
    logger.info(f"Found {len(df)} bottleneck edges (≥{threshold_pct*100:.0f}% utilisation)")
    return df


def compute_centrality(G: nx.DiGraph) -> pd.DataFrame:
    """
    Compute betweenness centrality for all nodes (undirected projection).
    Higher centrality → node is more critical for network connectivity.

    Returns:
        DataFrame with columns: node, name, centrality.
    """
    G_und = G.to_undirected()
    centrality = nx.betweenness_centrality(G_und, normalized=True, weight="capacity_gwh_day")
    rows = [
        {
            "node": node,
            "name": G.nodes[node].get("name", node),
            "node_type": G.nodes[node].get("node_type", ""),
            "centrality": round(score, 4),
        }
        for node, score in centrality.items()
    ]
    df = pd.DataFrame(rows).sort_values("centrality", ascending=False).reset_index(drop=True)
    return df


def supply_demand_balance(
    G: nx.DiGraph,
    supply_nodes: list[str],
    demand_nodes: list[str],
) -> dict:
    """
    Simple balance: total supply capacity vs total demand requirement.

    Args:
        supply_nodes: List of node IDs acting as supply sources.
        demand_nodes: List of node IDs acting as demand sinks.

    Returns:
        dict with total_supply, total_demand, balance, surplus.
    """
    total_supply = sum(G.nodes[n].get("capacity_gwh_day", 0) for n in supply_nodes if n in G)
    total_demand = sum(G.nodes[n].get("capacity_gwh_day", 0) for n in demand_nodes if n in G)
    balance = total_supply - total_demand
    return {
        "total_supply_gwh_day": total_supply,
        "total_demand_gwh_day": total_demand,
        "balance_gwh_day": balance,
        "surplus": balance >= 0,
    }
