"""
Report Agent
Uses Claude to generate a structured natural-language report from the
analysis dict produced by the Graph Agent, then triggers PDF generation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_anthropic import ChatAnthropic
from loguru import logger

from src.reports.pdf_generator import generate_pdf


REPORTS_DIR = Path("data/processed/reports")


def run_report_generation(
    analysis: dict[str, Any],
    model: str = "claude-opus-4-6",
    output_name: str = "gas_network_report",
) -> str:
    """
    Generate a markdown + PDF report from the analysis dict.

    Args:
        analysis: Output from graph_agent.run_graph_analysis().
        model: Claude model to use for narrative generation.
        output_name: Base filename (without extension).

    Returns:
        Absolute path to the generated PDF.
    """
    llm = ChatAnthropic(model=model, temperature=0.3)

    system = (
        "Eres un analista senior de infraestructuras energéticas. "
        "Redacta un informe ejecutivo completo en español sobre la red de gas de España "
        "basándote en los datos de análisis proporcionados. "
        "El informe debe incluir: "
        "1. Resumen ejecutivo, "
        "2. Estado actual de la red, "
        "3. Cuellos de botella identificados, "
        "4. Nodos críticos por centralidad, "
        "5. Análisis de escenarios de riesgo, "
        "6. Recomendaciones estratégicas. "
        "Usa formato Markdown con secciones claras y tablas donde sea útil."
    )

    user_content = (
        f"Datos de análisis de la red:\n```json\n{json.dumps(analysis, indent=2, ensure_ascii=False)}\n```\n\n"
        "Genera el informe completo."
    )

    logger.info("Report Agent: generating narrative report with Claude")
    response = llm.invoke([
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ])

    markdown_report = response.content if isinstance(response.content, str) else str(response.content)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    md_path = REPORTS_DIR / f"{output_name}.md"
    md_path.write_text(markdown_report, encoding="utf-8")
    logger.info(f"Markdown report saved: {md_path}")

    pdf_path = generate_pdf(markdown_report, output_name=output_name)
    logger.info(f"PDF report saved: {pdf_path}")

    return str(pdf_path)
