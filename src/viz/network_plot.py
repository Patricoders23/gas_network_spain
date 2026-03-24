"""
Network Plot
Static matplotlib / NetworkX visualisations of the gas network graph,
suitable for embedding in PDF reports.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for server/report use
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import numpy as np
from loguru import logger

OUTPUT_DIR = Path("data/processed/plots")

NODE_COLORS = {
    "lng_terminal":   "#1565C0",
    "interconnection": "#C62828",
    "compressor":     "#E65100",
    "storage":        "#2E7D32",
    "distribution":   "#6A1B9A",
}


def _geo_positions(G: nx.DiGraph) -> dict[str, tuple[float, float]]:
    """Use lon/lat as node positions when available."""
    pos = {}
    for node, data in G.nodes(data=True):
        lon = data.get("lon")
        lat = data.get("lat")
        if lon is not None and lat is not None:
            pos[node] = (lon, lat)
    return pos


def plot_network(
    G: nx.DiGraph,
    output_name: str = "network",
    figsize: tuple[int, int] = (14, 10),
    title: str = "Red de Transporte de Gas Natural — España",
) -> Path:
    """
    Draw the gas network graph using geographic coordinates as positions.

    Returns:
        Path to the saved PNG file.
    """
    pos = _geo_positions(G)
    if not pos:
        pos = nx.spring_layout(G, seed=42)

    node_colors = [NODE_COLORS.get(G.nodes[n].get("node_type", ""), "#90A4AE") for n in G.nodes()]
    node_sizes  = [max(200, G.nodes[n].get("capacity_gwh_day", 0) * 0.8) for n in G.nodes()]

    edge_widths = [max(1, G[u][v].get("capacity_gwh_day", 50) / 100) for u, v in G.edges()]

    fig, ax = plt.subplots(figsize=figsize, facecolor="#F5F5F5")
    ax.set_facecolor("#E3F2FD")

    nx.draw_networkx_edges(
        G, pos, ax=ax,
        width=edge_widths,
        edge_color="#546E7A",
        alpha=0.6,
        arrows=True,
        arrowsize=15,
        connectionstyle="arc3,rad=0.05",
    )
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors,
        node_size=node_sizes,
        alpha=0.9,
    )
    labels = {n: G.nodes[n].get("name", n)[:15] for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, ax=ax, font_size=7, font_color="#212121")

    # Legend
    patches = [mpatches.Patch(color=c, label=k.replace("_", " ").title()) for k, c in NODE_COLORS.items()]
    ax.legend(handles=patches, loc="lower left", fontsize=8, framealpha=0.8)

    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.axis("off")
    plt.tight_layout()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{output_name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Network plot saved to {path}")
    return path


def plot_centrality_bar(
    centrality_df,
    output_name: str = "centrality",
    top_n: int = 10,
) -> Path:
    """
    Bar chart of the top-N nodes by betweenness centrality.

    Args:
        centrality_df: DataFrame with columns: name, centrality.
        top_n: Number of top nodes to show.
    """
    df = centrality_df.head(top_n)
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(df["name"], df["centrality"], color="#1565C0", alpha=0.8)
    ax.set_xlabel("Centralidad de intermediación (normalizada)", fontsize=10)
    ax.set_title(f"Top {top_n} nodos más críticos de la red", fontsize=12, fontweight="bold")
    ax.invert_yaxis()
    ax.bar_label(bars, fmt="%.3f", padding=3, fontsize=8)
    plt.tight_layout()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{output_name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Centrality bar chart saved to {path}")
    return path


def plot_scenario_comparison(
    scenarios_df,
    output_name: str = "scenarios",
) -> Path:
    """
    Grouped bar chart comparing max-flow across scenarios.

    Args:
        scenarios_df: DataFrame from scenario_simulator.run_scenario_analysis().
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#1565C0" if row["scenario"] == "Baseline" else
              "#C62828" if row["delta_vs_baseline"] < 0 else "#2E7D32"
              for _, row in scenarios_df.iterrows()]
    bars = ax.bar(scenarios_df["scenario"], scenarios_df["flow_gwh_day"], color=colors, alpha=0.85)
    ax.set_ylabel("Flujo máximo (GWh/día)", fontsize=10)
    ax.set_title("Comparación de escenarios — Flujo máximo", fontsize=12, fontweight="bold")
    ax.bar_label(bars, fmt="%.0f", padding=3, fontsize=9)
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{output_name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Scenario comparison plot saved to {path}")
    return path
