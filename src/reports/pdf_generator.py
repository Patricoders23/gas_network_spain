"""
PDF Generator
Converts a Markdown string into a formatted PDF report using ReportLab.
Supports headings, paragraphs, tables (parsed from Markdown), and image embedding.
"""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    HRFlowable,
    PageBreak,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from loguru import logger

REPORTS_DIR = Path("data/processed/reports")

# ---------------------------------------------------------------------------
# Style definitions
# ---------------------------------------------------------------------------

def _build_styles():
    styles = getSampleStyleSheet()
    custom = {
        "Title": ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontSize=22,
            textColor=colors.HexColor("#0D47A1"),
            spaceAfter=12,
            alignment=TA_CENTER,
        ),
        "H1": ParagraphStyle(
            "H1",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=colors.HexColor("#1565C0"),
            spaceBefore=14,
            spaceAfter=6,
            borderPad=4,
        ),
        "H2": ParagraphStyle(
            "H2",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=colors.HexColor("#1976D2"),
            spaceBefore=10,
            spaceAfter=4,
        ),
        "H3": ParagraphStyle(
            "H3",
            parent=styles["Heading3"],
            fontSize=11,
            textColor=colors.HexColor("#37474F"),
            spaceBefore=8,
            spaceAfter=3,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "BulletItem": ParagraphStyle(
            "BulletItem",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            leftIndent=18,
            bulletIndent=6,
            spaceAfter=3,
        ),
    }
    return custom


# ---------------------------------------------------------------------------
# Markdown → ReportLab flowables
# ---------------------------------------------------------------------------

def _md_to_flowables(markdown: str, styles: dict) -> list:
    flowables = []
    lines = markdown.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Page break
        if line in ("---", "***", "___"):
            flowables.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#BDBDBD")))
            i += 1
            continue

        # Headings
        if line.startswith("#### "):
            flowables.append(Paragraph(_clean(line[5:]), styles["H3"]))
        elif line.startswith("### "):
            flowables.append(Paragraph(_clean(line[4:]), styles["H3"]))
        elif line.startswith("## "):
            flowables.append(Paragraph(_clean(line[3:]), styles["H2"]))
        elif line.startswith("# "):
            flowables.append(Paragraph(_clean(line[2:]), styles["Title"]))

        # Bullet items
        elif line.startswith("- ") or line.startswith("* "):
            flowables.append(Paragraph(f"• {_clean(line[2:])}", styles["BulletItem"]))

        # Numbered items
        elif re.match(r"^\d+\. ", line):
            text = re.sub(r"^\d+\. ", "", line)
            flowables.append(Paragraph(f"  {_clean(text)}", styles["BulletItem"]))

        # Markdown table
        elif "|" in line and i + 1 < len(lines) and re.match(r"^[\|\s\-:]+$", lines[i + 1]):
            table_lines = [line]
            i += 2  # skip separator row
            while i < len(lines) and "|" in lines[i]:
                table_lines.append(lines[i].strip())
                i += 1
            flowables.append(_md_table_to_reportlab(table_lines, styles))
            flowables.append(Spacer(1, 6))
            continue

        # Empty line
        elif line == "":
            flowables.append(Spacer(1, 4))

        # Regular paragraph
        else:
            flowables.append(Paragraph(_clean(line), styles["Body"]))

        i += 1

    return flowables


def _clean(text: str) -> str:
    """Convert Markdown inline formatting to ReportLab XML."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*",     r"<i>\1</i>", text)
    text = re.sub(r"`(.+?)`",       r"<font name='Courier'>\1</font>", text)
    return text


def _md_table_to_reportlab(rows: list[str], styles: dict) -> Table:
    data = []
    for row in rows:
        cells = [Paragraph(_clean(c.strip()), styles["Body"]) for c in row.strip("|").split("|")]
        data.append(cells)

    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#1565C0")),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#BDBDBD")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#E3F2FD")]),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",(0, 0), (-1, -1), 6),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))
    return t


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_pdf(
    markdown: str,
    output_name: str = "gas_network_report",
    image_paths: list[Path] | None = None,
    title: str = "Análisis de la Red de Gas Natural — España",
) -> Path:
    """
    Convert a Markdown string into a PDF report.

    Args:
        markdown: Full report content in Markdown format.
        output_name: Output filename without extension.
        image_paths: Optional list of PNG paths to append as figures.
        title: Document title (used in PDF metadata).

    Returns:
        Path to the generated PDF.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = REPORTS_DIR / f"{output_name}.pdf"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        title=title,
        author="Gas Network Spain — AI Analysis System",
    )

    styles = _build_styles()
    story = _md_to_flowables(markdown, styles)

    # Append figures
    if image_paths:
        story.append(PageBreak())
        story.append(Paragraph("Anexo: Figuras", styles["H1"]))
        for img_path in image_paths:
            if Path(img_path).exists():
                story.append(Spacer(1, 12))
                story.append(Paragraph(Path(img_path).stem.replace("_", " ").title(), styles["H3"]))
                story.append(Image(str(img_path), width=15 * cm, height=10 * cm, kind="proportional"))

    doc.build(story)
    logger.info(f"PDF generated: {pdf_path}")
    return pdf_path
