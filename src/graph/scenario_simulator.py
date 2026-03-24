"""
Scenario Simulator
Runs what-if scenarios on the gas network graph:
  - Supply disruption (remove a node or edge)
  - Demand surge (increase demand at specific nodes)
  - Infrastructure addition (add a new edge/node)
"""

import copy
from dataclasses import dataclass, field
from typing import Literal

import networkx as nx
import pandas as pd
from loguru import logger

from src.graph.flow_analyzer import compute_max_flow, detect_bottlenecks, compute_centrality


@dataclass
class Scenario:
    name: str
    description: str
    disruptions: list[dict] = field(default_factory=list)
    additions: list[dict] = field(default_factory=list)
    demand_changes: dict[str, float] = field(default_factory=dict)


def apply_scenario(G: nx.DiGraph, scenario: Scenario) -> nx.DiGraph:
    """
    Return a modified copy of G with the scenario applied.

    Disruption dict format:
        {"type": "remove_node", "id": "TUN_ICP"}
        {"type": "remove_edge", "source": "IRU_ICP", "target": "ZAR_CMP"}
        {"type": "reduce_capacity", "source": "X", "target": "Y", "factor": 0.5}

    Addition dict format:
        {"type": "add_edge", "source": "X", "target": "Y", "capacity_gwh_day": 200, "length_km": 150}
    """
    G2 = copy.deepcopy(G)

    for d in scenario.disruptions:
        if d["type"] == "remove_node" and d["id"] in G2:
            G2.remove_node(d["id"])
            logger.info(f"[{scenario.name}] Removed node {d['id']}")
        elif d["type"] == "remove_edge":
            if G2.has_edge(d["source"], d["target"]):
                G2.remove_edge(d["source"], d["target"])
                logger.info(f"[{scenario.name}] Removed edge {d['source']} → {d['target']}")
        elif d["type"] == "reduce_capacity":
            if G2.has_edge(d["source"], d["target"]):
                orig = G2[d["source"]][d["target"]]["capacity_gwh_day"]
                G2[d["source"]][d["target"]]["capacity_gwh_day"] = orig * d.get("factor", 0.5)
                logger.info(f"[{scenario.name}] Reduced capacity {d['source']} → {d['target']} by factor {d.get('factor', 0.5)}")

    for a in scenario.additions:
        if a["type"] == "add_edge":
            G2.add_edge(
                a["source"],
                a["target"],
                capacity_gwh_day=a.get("capacity_gwh_day", 100),
                length_km=a.get("length_km", 0),
                operator=a.get("operator", "New"),
            )
            logger.info(f"[{scenario.name}] Added edge {a['source']} → {a['target']}")

    for node, delta in scenario.demand_changes.items():
        if node in G2.nodes:
            G2.nodes[node]["capacity_gwh_day"] = G2.nodes[node].get("capacity_gwh_day", 0) + delta

    return G2


def run_scenario_analysis(
    G: nx.DiGraph,
    scenarios: list[Scenario],
    source: str,
    sink: str,
) -> pd.DataFrame:
    """
    Run multiple scenarios and compare max-flow from source to sink.

    Returns:
        DataFrame with columns: scenario, flow_gwh_day, delta_vs_baseline, bottlenecks_count.
    """
    results = []

    # Baseline
    baseline_flow, _ = compute_max_flow(G, source, sink)
    results.append({
        "scenario": "Baseline",
        "flow_gwh_day": baseline_flow,
        "delta_vs_baseline": 0.0,
        "bottlenecks_count": len(detect_bottlenecks(G)),
    })

    for scenario in scenarios:
        G_mod = apply_scenario(G, scenario)
        if not nx.has_path(G_mod, source, sink):
            flow = 0.0
        else:
            flow, _ = compute_max_flow(G_mod, source, sink)

        results.append({
            "scenario": scenario.name,
            "flow_gwh_day": flow,
            "delta_vs_baseline": flow - baseline_flow,
            "bottlenecks_count": len(detect_bottlenecks(G_mod)),
        })

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Predefined scenarios for Spain
# ---------------------------------------------------------------------------

MEDGAZ_DISRUPTION = Scenario(
    name="Medgaz Disruption",
    description="Cierre total del gasoducto Medgaz (Argelia-España)",
    disruptions=[{"type": "remove_node", "id": "TUN_ICP"}],
)

FRANCE_BORDER_REDUCTION = Scenario(
    name="French Border -50%",
    description="Reducción del 50% en la capacidad de interconexión Francia-España",
    disruptions=[
        {"type": "reduce_capacity", "source": "IRU_ICP", "target": "ZAR_CMP", "factor": 0.5},
        {"type": "reduce_capacity", "source": "LAR_ICP", "target": "ZAR_CMP", "factor": 0.5},
    ],
)

NEW_BISCAY_GULF_PIPE = Scenario(
    name="New Midcat Pipeline",
    description="Añade un nuevo gasoducto Pirineos con 800 GWh/día de capacidad",
    additions=[
        {"type": "add_edge", "source": "IRU_ICP", "target": "MAD_CMP",
         "capacity_gwh_day": 800, "length_km": 650, "operator": "Nuevo"}
    ],
)
