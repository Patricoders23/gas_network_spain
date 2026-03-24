"""
Graph Agent
Uses Claude (via LangChain) + tool calls to analyse the gas network graph.
Produces a structured analysis result dict consumed by the Supervisor.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from loguru import logger

from src.graph.network_builder import build_network, _default_nodes, _default_edges
from src.graph.flow_analyzer import (
    compute_max_flow,
    detect_bottlenecks,
    compute_centrality,
    supply_demand_balance,
)
from src.graph.scenario_simulator import (
    run_scenario_analysis,
    MEDGAZ_DISRUPTION,
    FRANCE_BORDER_REDUCTION,
    NEW_BISCAY_GULF_PIPE,
)


# ---------------------------------------------------------------------------
# Tool definitions (exposed to Claude)
# ---------------------------------------------------------------------------

@tool
def get_network_summary() -> str:
    """Return a JSON summary of the current gas network (nodes, edges, capacities)."""
    G = build_network()
    nodes = [{"id": n, **d} for n, d in G.nodes(data=True)]
    edges = [{"source": u, "target": v, **d} for u, v, d in G.edges(data=True)]
    return json.dumps({"nodes": nodes, "edges": edges}, default=str)


@tool
def get_bottlenecks(threshold_pct: float = 0.8) -> str:
    """Identify pipeline bottlenecks above the given utilisation threshold (0-1)."""
    G = build_network()
    df = detect_bottlenecks(G, threshold_pct=threshold_pct)
    return df.to_json(orient="records")


@tool
def get_centrality() -> str:
    """Return betweenness centrality for all network nodes (higher = more critical)."""
    G = build_network()
    df = compute_centrality(G)
    return df.to_json(orient="records")


@tool
def run_scenarios(source: str = "TUN_ICP", sink: str = "SEV_DST") -> str:
    """
    Run predefined disruption/expansion scenarios and compare max-flow results.

    Args:
        source: Source node ID (default: Medgaz Algeria entry).
        sink: Sink node ID (default: Seville distribution zone).
    """
    G = build_network()
    df = run_scenario_analysis(
        G,
        [MEDGAZ_DISRUPTION, FRANCE_BORDER_REDUCTION, NEW_BISCAY_GULF_PIPE],
        source=source,
        sink=sink,
    )
    return df.to_json(orient="records")


TOOLS = [get_network_summary, get_bottlenecks, get_centrality, run_scenarios]


# ---------------------------------------------------------------------------
# Agent logic
# ---------------------------------------------------------------------------

def run_graph_analysis(model: str = "claude-opus-4-6") -> dict[str, Any]:
    """
    Invoke Claude with gas-network tools to produce a structured analysis.

    Returns:
        dict with keys: summary, bottlenecks, centrality, scenarios, insights.
    """
    llm = ChatAnthropic(model=model, temperature=0).bind_tools(TOOLS)

    system = (
        "Eres un experto en infraestructuras de gas natural. "
        "Tienes acceso a herramientas para analizar la red de transporte de gas de España. "
        "Usa las herramientas disponibles para: "
        "1) Obtener un resumen de la red, "
        "2) Identificar cuellos de botella, "
        "3) Calcular la centralidad de los nodos, "
        "4) Ejecutar escenarios de disrupción y expansión. "
        "Devuelve un análisis estructurado en JSON con claves: "
        "summary, bottlenecks, centrality, scenarios, insights."
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "Realiza un análisis completo de la red de gas de España."},
    ]

    # Agentic loop (max 6 turns)
    tool_map = {t.name: t for t in TOOLS}
    for turn in range(6):
        response = llm.invoke(messages)
        messages.append({"role": "assistant", "content": response.content})

        tool_calls = getattr(response, "tool_calls", [])
        if not tool_calls:
            break

        for tc in tool_calls:
            tool_fn = tool_map.get(tc["name"])
            if tool_fn:
                result = tool_fn.invoke(tc["args"])
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": str(result)})

    # Extract final JSON from last assistant message
    last_content = response.content if isinstance(response.content, str) else str(response.content)
    try:
        start = last_content.find("{")
        end = last_content.rfind("}") + 1
        analysis = json.loads(last_content[start:end]) if start != -1 else {}
    except Exception:
        analysis = {"raw_response": last_content}

    logger.info("Graph Agent analysis complete")
    return analysis
