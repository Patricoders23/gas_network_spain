"""
Map Generator
Produces interactive Folium maps of Spain's gas network,
overlaid on a geographic basemap with node/edge popups.
"""

from __future__ import annotations

from pathlib import Path

import folium
import networkx as nx
import pandas as pd
from loguru import logger

OUTPUT_DIR = Path("data/processed/maps")

NODE_COLORS = {
    "lng_terminal": "blue",
    "interconnection": "red",
    "compressor": "orange",
    "storage": "green",
    "distribution": "purple",
}

NODE_ICONS = {
    "lng_terminal": "ship",
    "interconnection": "exchange",
    "compressor": "cog",
    "storage": "database",
    "distribution": "home",
}


def generate_network_map(
    G: nx.DiGraph,
    output_name: str = "gas_network_spain",
    center: tuple[float, float] = (40.0, -3.5),
    zoom: int = 6,
) -> Path:
    """
    Create an interactive Folium map of the gas network.

    Args:
        G: NetworkX DiGraph with lat/lon node attributes.
        output_name: HTML output filename (without extension).
        center: Map center [lat, lon].
        zoom: Initial zoom level.

    Returns:
        Path to the generated HTML file.
    """
    m = folium.Map(location=list(center), zoom_start=zoom, tiles="CartoDB positron")

    # Draw edges first (below nodes)
    for u, v, data in G.edges(data=True):
        u_data = G.nodes[u]
        v_data = G.nodes[v]
        if u_data.get("lat") and v_data.get("lat"):
            coords = [
                [u_data["lat"], u_data["lon"]],
                [v_data["lat"], v_data["lon"]],
            ]
            cap = data.get("capacity_gwh_day", 0)
            weight = max(1, min(8, cap / 100))
            popup_html = (
                f"<b>{u} → {v}</b><br>"
                f"Capacidad: {cap} GWh/día<br>"
                f"Longitud: {data.get('length_km', '?')} km<br>"
                f"Operador: {data.get('operator', '?')}"
            )
            folium.PolyLine(
                coords,
                weight=weight,
                color="#555555",
                opacity=0.7,
                tooltip=f"{u} → {v} ({cap} GWh/d)",
                popup=folium.Popup(popup_html, max_width=250),
            ).add_to(m)

    # Draw nodes
    for node, data in G.nodes(data=True):
        lat, lon = data.get("lat"), data.get("lon")
        if lat is None or lon is None:
            continue

        node_type = data.get("node_type", "compressor")
        color = NODE_COLORS.get(node_type, "gray")
        icon = NODE_ICONS.get(node_type, "info-sign")

        popup_html = (
            f"<b>{data.get('name', node)}</b><br>"
            f"Tipo: {node_type}<br>"
            f"Capacidad: {data.get('capacity_gwh_day', 0)} GWh/día"
        )

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=data.get("name", node),
            icon=folium.Icon(color=color, icon=icon, prefix="fa"),
        ).add_to(m)

    # Legend
    legend_html = """
    <div style="position:fixed; bottom:30px; left:30px; z-index:1000;
                background:white; padding:10px; border-radius:6px;
                border:1px solid #ccc; font-size:12px;">
        <b>Red de Gas España</b><br>
        <span style="color:blue">&#9679;</span> Terminal GNL<br>
        <span style="color:red">&#9679;</span> Interconexión<br>
        <span style="color:orange">&#9679;</span> Compresor<br>
        <span style="color:green">&#9679;</span> Almacenamiento<br>
        <span style="color:purple">&#9679;</span> Distribución
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{output_name}.html"
    m.save(str(path))
    logger.info(f"Interactive map saved to {path}")
    return path


def generate_flow_heatmap(
    G: nx.DiGraph,
    flow_dict: dict,
    output_name: str = "flow_heatmap",
) -> Path:
    """
    Overlay a max-flow result on the map, colouring edges by flow intensity.

    Args:
        G: Base network graph.
        flow_dict: Flow dict from nx.maximum_flow (nested {u: {v: flow}}).
        output_name: Output HTML filename.
    """
    m = folium.Map(location=[40.0, -3.5], zoom_start=6, tiles="CartoDB positron")

    for u, targets in flow_dict.items():
        for v, flow in targets.items():
            if flow == 0 or not G.has_edge(u, v):
                continue
            u_data = G.nodes.get(u, {})
            v_data = G.nodes.get(v, {})
            if u_data.get("lat") and v_data.get("lat"):
                cap = G[u][v].get("capacity_gwh_day", 1)
                pct = flow / cap
                color = _flow_color(pct)
                folium.PolyLine(
                    [[u_data["lat"], u_data["lon"]], [v_data["lat"], v_data["lon"]]],
                    weight=4,
                    color=color,
                    opacity=0.85,
                    tooltip=f"{u}→{v}: {flow:.0f}/{cap} GWh/d ({pct*100:.0f}%)",
                ).add_to(m)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{output_name}.html"
    m.save(str(path))
    logger.info(f"Flow heatmap saved to {path}")
    return path


def _flow_color(pct: float) -> str:
    if pct >= 0.9:
        return "#d32f2f"  # red — near capacity
    if pct >= 0.6:
        return "#f57c00"  # orange
    if pct >= 0.3:
        return "#fbc02d"  # yellow
    return "#388e3c"      # green — low utilisation
