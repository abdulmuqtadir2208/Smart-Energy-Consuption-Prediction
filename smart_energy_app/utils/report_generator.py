"""
utils/report_generator.py
--------------------------
Generates a PDF energy report using ReportLab.
"""

import os
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def generate_pdf_report(
    user_name: str,
    records: list[dict],
    total_kwh: float,
    predicted_kwh: float
) -> str:
    """
    Build a styled PDF report and return the file path.

    Parameters
    ----------
    user_name     : str   — Logged-in user's display name.
    records       : list  — List of usage dicts (usage_date, device, hours_used, energy_kwh).
    total_kwh     : float — Cumulative energy consumed.
    predicted_kwh : float — ML-predicted tomorrow usage.

    Returns
    -------
    str — Absolute path to the generated PDF file.
    """
    # Write to a temp file so Flask can serve it
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.close()

    doc = SimpleDocTemplate(
        tmp.name,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    # ── Styles ──
    styles  = getSampleStyleSheet()
    primary = colors.HexColor("#2E8B57")
    accent  = colors.HexColor("#3B82F6")
    light   = colors.HexColor("#F4F6F8")
    dark    = colors.HexColor("#1F2933")

    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        textColor=primary, fontSize=22, spaceAfter=4, alignment=TA_CENTER,
        fontName="Helvetica-Bold"
    )
    sub_style = ParagraphStyle(
        "Sub", parent=styles["Normal"],
        textColor=dark, fontSize=10, alignment=TA_CENTER, spaceAfter=2
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading2"],
        textColor=primary, fontSize=13, spaceBefore=14, spaceAfter=6,
        fontName="Helvetica-Bold"
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, textColor=dark
    )

    story = []

    # ── Header ──
    story.append(Paragraph("⚡ Smart Energy Report", title_style))
    story.append(Paragraph(f"Generated for: <b>{user_name}</b>", sub_style))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%d %B %Y, %H:%M')}", sub_style))
    story.append(HRFlowable(width="100%", thickness=1, color=primary, spaceAfter=12))

    # ── Summary Cards ──
    story.append(Paragraph("Energy Summary", section_style))
    summary_data = [
        ["Metric", "Value"],
        ["Total Energy Consumed (All Time)", f"{round(total_kwh, 3)} kWh"],
        ["Predicted Tomorrow", f"{round(predicted_kwh, 3)} kWh"],
        ["Total Records Logged", str(len(records))],
    ]
    summary_table = Table(summary_data, colWidths=[10*cm, 6*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), primary),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 10),
        ("ALIGN",      (0,0), (-1,-1), "CENTER"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [light, colors.white]),
        ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 14))

    # ── Usage Table ──
    story.append(Paragraph("Device Usage Log", section_style))
    if records:
        table_data = [["Date", "Device", "Hours Used", "Energy (kWh)"]]
        for r in records[:50]:  # Limit to 50 rows for PDF readability
            table_data.append([
                r["usage_date"],
                r["device"],
                str(round(r["hours_used"], 1)),
                str(round(r["energy_kwh"], 3)),
            ])
        usage_table = Table(table_data, colWidths=[3.5*cm, 5*cm, 3.5*cm, 4.5*cm])
        usage_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), accent),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 9),
            ("ALIGN",      (0,0), (-1,-1), "CENTER"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [light, colors.white]),
            ("GRID",       (0,0), (-1,-1), 0.4, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(usage_table)
    else:
        story.append(Paragraph("No usage records found.", body_style))

    # ── Footer ──
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1")))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Smart Energy Consumption Tracking System  •  Report auto-generated",
        ParagraphStyle("Footer", parent=styles["Normal"],
                       fontSize=8, textColor=colors.HexColor("#9CA3AF"), alignment=TA_CENTER)
    ))

    doc.build(story)
    return tmp.name
