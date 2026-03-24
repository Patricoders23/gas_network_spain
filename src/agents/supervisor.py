"""
Supervisor Agent
Orchestrates the multi-agent pipeline using LangGraph.
Coordinates the Graph Agent and Report Agent to produce
complete gas-network analysis reports.
"""

from __future__ import annotations

from typing import TypedDict, Annotated, Literal
import operator

from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from loguru import logger

from src.agents.graph_agent import run_graph_analysis
from src.agents.report_agent import run_report_generation


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

class NetworkState(TypedDict):
    messages: Annotated[list, operator.add]
    analysis_result: dict
    report_path: str
    error: str
    next_step: str


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

def supervisor_node(state: NetworkState) -> NetworkState:
    """
    Decide which agent to call next based on current state.
    """
    logger.info("Supervisor: evaluating state")

    if state.get("error"):
        logger.error(f"Supervisor: error detected — {state['error']}")
        return {**state, "next_step": "end"}

    if not state.get("analysis_result"):
        return {**state, "next_step": "graph_agent"}

    if not state.get("report_path"):
        return {**state, "next_step": "report_agent"}

    return {**state, "next_step": "end"}


def graph_agent_node(state: NetworkState) -> NetworkState:
    """Run the graph analysis agent."""
    logger.info("Supervisor: dispatching to Graph Agent")
    try:
        result = run_graph_analysis()
        return {**state, "analysis_result": result, "messages": state["messages"] + ["Graph analysis complete."]}
    except Exception as exc:
        logger.exception("Graph Agent failed")
        return {**state, "error": str(exc)}


def report_agent_node(state: NetworkState) -> NetworkState:
    """Run the report generation agent."""
    logger.info("Supervisor: dispatching to Report Agent")
    try:
        path = run_report_generation(state["analysis_result"])
        return {**state, "report_path": path, "messages": state["messages"] + [f"Report saved to {path}."]}
    except Exception as exc:
        logger.exception("Report Agent failed")
        return {**state, "error": str(exc)}


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def route(state: NetworkState) -> Literal["graph_agent", "report_agent", "__end__"]:
    step = state.get("next_step", "graph_agent")
    if step == "graph_agent":
        return "graph_agent"
    if step == "report_agent":
        return "report_agent"
    return END


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_supervisor_graph() -> StateGraph:
    workflow = StateGraph(NetworkState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("graph_agent", graph_agent_node)
    workflow.add_node("report_agent", report_agent_node)

    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges("supervisor", route)
    workflow.add_edge("graph_agent", "supervisor")
    workflow.add_edge("report_agent", "supervisor")

    return workflow.compile()


def run_pipeline(initial_message: str = "Run full gas network analysis") -> NetworkState:
    """Entry point: run the complete multi-agent pipeline."""
    app = build_supervisor_graph()
    initial_state: NetworkState = {
        "messages": [initial_message],
        "analysis_result": {},
        "report_path": "",
        "error": "",
        "next_step": "",
    }
    logger.info("Starting supervisor pipeline")
    final_state = app.invoke(initial_state)
    logger.info(f"Pipeline complete. Report: {final_state.get('report_path')}")
    return final_state


if __name__ == "__main__":
    result = run_pipeline()
    print(result["messages"])
