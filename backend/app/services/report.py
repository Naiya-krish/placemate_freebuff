"""Aggregate-only PDF report for placement cells (ReportLab)."""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.officer import OfficerOverview

VIOLET = colors.HexColor("#6D4AFF")
INK = colors.HexColor("#16161D")
MUTED = colors.HexColor("#6B7280")
LIGHT = colors.HexColor("#F4F2FF")


def build_overview_pdf(overview: OfficerOverview, college_name: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="PlaceMate cohort readiness report",
        author="PlaceMate",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("Title2", parent=styles["Title"], textColor=INK, fontSize=22, leading=26)
    subtitle = ParagraphStyle("Sub", parent=styles["Normal"], textColor=MUTED, fontSize=9.5)
    h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"], textColor=VIOLET, fontSize=12, spaceBefore=14
    )
    cell = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=8.5, leading=10.5)

    story: list[object] = [
        Paragraph("PlaceMate · Cohort readiness", title),
        Paragraph(
            f"{college_name} · generated {overview.generated_at[:16].replace('T', ' ')} UTC · "
            "aggregate data only (no individual data unless the student opted in)",
            subtitle,
        ),
        Spacer(1, 8 * mm),
        Paragraph("Key indicators", h2),
    ]
    k = overview.kpis
    kpi_data = [
        ["Students", "Active 30d", "Resumes", "Interviews", "Avg readiness", "Days to drive"],
        [
            str(k.total_students),
            str(k.active_30d),
            str(k.resume_uploads),
            str(k.interviews_completed),
            f"{k.avg_readiness}/100",
            str(k.days_to_placement if k.days_to_placement is not None else "—"),
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[28 * mm] * 6, hAlign="LEFT")
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
                ("TEXTCOLOR", (0, 0), (-1, 0), VIOLET),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 1), (-1, 1), INK),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(kpi_table)

    story.append(Paragraph("Readiness funnel", h2))
    funnel_rows = [["Stage", "Students", "Share"]] + [
        [Paragraph(stage.stage, cell), str(stage.count), f"{stage.percent}%"]
        for stage in overview.funnel
    ]
    funnel_table = Table(funnel_rows, colWidths=[80 * mm, 30 * mm, 30 * mm], hAlign="LEFT")
    funnel_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(funnel_table)

    story.append(Paragraph("Department heatmap (average rubric score /100)", h2))
    header = ["Branch"] + overview.criteria
    heat_rows = [header]
    for branch in overview.branches:
        row = [Paragraph(branch, cell)]
        for criterion in overview.criteria:
            value = next(
                (
                    h.value
                    for h in overview.heatmap
                    if h.branch == branch and h.criterion == criterion
                ),
                0,
            )
            row.append(str(value) if value else "—")
        heat_rows.append(row)
    heat_table = Table(
        heat_rows, colWidths=[38 * mm] + [26 * mm] * len(overview.criteria), hAlign="LEFT"
    )
    heat_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
                ("TEXTCOLOR", (0, 0), (-1, 0), VIOLET),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(heat_table)

    story.append(Paragraph("Weakest skills", h2))
    weak_rows = [["Skill", "Gap (pts)", "Students affected"]] + [
        [item.skill, str(item.gap), str(item.students_affected)] for item in overview.weakest_skills
    ]
    weak_table = Table(weak_rows, colWidths=[90 * mm, 30 * mm, 40 * mm], hAlign="LEFT")
    weak_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(weak_table)
    story.append(Spacer(1, 6 * mm))
    story.append(
        Paragraph(
            "Method: readiness = 70% latest interview score + 30% latest resume score. "
            "Interview scores are the median of three low-temperature rubric samples. "
            "Named student data is excluded unless that student opted in. "
            "This report contains aggregate statistics only and is safe to share for accreditation.",
            subtitle,
        )
    )
    doc.build(story)
    return buffer.getvalue()
