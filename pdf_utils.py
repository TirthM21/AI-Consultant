import io
from datetime import datetime

import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


def _build_insights_chart(consultation):
    """
    Build a simple bar chart from consultation.analysis['insights'].
    Returns an in‑memory PNG buffer or None if no insights.
    """
    analysis = consultation.analysis or {}
    insights = analysis.get("insights", [])
    if not insights:
        return None

    categories = [i.get("category", "Unknown") for i in insights]
    values = [1] * len(categories)

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar(categories, values, color="#667eea")
    ax.set_title("Market Insights by Category")
    ax.set_ylabel("Count")
    ax.set_xticklabels(categories, rotation=30, ha="right")

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_consultation_pdf(consultation):
    """
    Generate a PDF report for a Consultation.
    Returns an in‑memory BytesIO ready to send with Flask's send_file.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=22,
        textColor=colors.HexColor("#667eea"),
        spaceAfter=18,
    )
    section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#764ba2"),
        spaceBefore=12,
        spaceAfter=6,
    )

    elements = []

    # Header
    elements.append(Paragraph("Business Consultation Report", title_style))
    elements.append(
        Paragraph(
            f"Client: {consultation.user.name} &nbsp;&nbsp; | &nbsp;&nbsp; "
            f"Date: {consultation.created_at.strftime('%Y-%m-%d')}",
            styles["Normal"],
        )
    )
    elements.append(
        Paragraph(f"Consultation ID: {consultation.id[:8]}...", styles["Normal"])
    )
    elements.append(Spacer(1, 0.3 * inch))

    # Query
    elements.append(Paragraph("Business Question", section_title))
    elements.append(Paragraph(f'"{consultation.query}"', styles["BodyText"]))
    elements.append(Spacer(1, 0.2 * inch))

    # Executive summary
    response_text = consultation.response or ""
    summary = (response_text[:400] + "...") if len(response_text) > 400 else response_text
    elements.append(Paragraph("Executive Summary", section_title))
    elements.append(Paragraph(summary.replace("\n", "<br/>"), styles["BodyText"]))
    elements.append(Spacer(1, 0.2 * inch))

    # Full AI response
    elements.append(PageBreak())
    elements.append(Paragraph("AI Consultation Response", section_title))
    elements.append(
        Paragraph(response_text.replace("\n", "<br/>"), styles["BodyText"])
    )

    # Market insights
    analysis = consultation.analysis or {}
    insights = analysis.get("insights", [])
    if insights:
        elements.append(PageBreak())
        elements.append(Paragraph("Market Analysis", section_title))
        for ins in insights:
            cat = ins.get("category", "Category")
            finding = ins.get("finding", "")
            elements.append(
                Paragraph(f"<b>{cat}:</b> {finding}", styles["BodyText"])
            )
            elements.append(Spacer(1, 0.05 * inch))

    # Strategic recommendations
    recs = consultation.recommendations or []
    if recs:
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph("Strategic Recommendations", section_title))
        for rec in recs:
            elements.append(
                Paragraph(
                    f"<b>{rec.get('category', 'Area')}:</b> "
                    f"{rec.get('recommendation', '')}",
                    styles["BodyText"],
                )
            )
            meta = (
                f"Priority: {rec.get('priority', 'N/A')} | "
                f"Timeline: {rec.get('timeline', 'N/A')}"
            )
            elements.append(Paragraph(meta, styles["Italic"]))
            elements.append(Spacer(1, 0.1 * inch))

    # Chart page
    chart_buf = _build_insights_chart(consultation)
    if chart_buf is not None:
        elements.append(PageBreak())
        elements.append(Paragraph("Visual Insights", section_title))
        elements.append(Spacer(1, 0.1 * inch))
        chart_img = Image(chart_buf, width=6 * inch, height=3 * inch)
        elements.append(chart_img)

    # Sources
    sources = (consultation.search_results or {}).get("sources", [])
    if sources:
        elements.append(PageBreak())
        elements.append(Paragraph("Key Sources", section_title))
        for url in sources[:10]:
            elements.append(Paragraph(url, styles["BodyText"]))
            elements.append(Spacer(1, 0.05 * inch))

    doc.build(elements)
    buffer.seek(0)
    return buffer

