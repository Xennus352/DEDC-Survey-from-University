"""Portable PDF output with bundled Myanmar font and HarfBuzz shaping."""

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable


def pdf_document(rows, title):
    font = (
        Path(__file__).resolve().parents[2] / "static/fonts/NotoSansMyanmar-Regular.ttf"
    )
    if "DEDCMyanmar" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("DEDCMyanmar", str(font), shapable=True))
        pdfmetrics.registerFontFamily(
            "DEDCMyanmar",
            normal="DEDCMyanmar",
            bold="DEDCMyanmar",
            italic="DEDCMyanmar",
            boldItalic="DEDCMyanmar",
        )
    body = ParagraphStyle(
        "body",
        fontName="DEDCMyanmar",
        fontSize=9,
        leading=17,
        shaping=True,
        spaceAfter=9,
    )
    heading = ParagraphStyle(
        "heading",
        parent=body,
        fontSize=17,
        leading=26,
        spaceAfter=18,
        textColor=colors.HexColor("#232550"),
    )
    stream = BytesIO()
    document = SimpleDocTemplate(
        stream,
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=42,
        bottomMargin=42,
        title=title,
    )
    story = [Paragraph(escape(title), heading)]
    headers = None
    for row in rows[1:]:
        if not row:
            story.append(Spacer(1, 12))
            continue
        if headers is None and len(row) >= 5:
            headers = row
            continue
        if headers and len(row) == len(headers):
            text = "<br/>".join(
                f"<b>{escape(str(label))}</b>: {escape(str(value)).replace(chr(10), '<br/>')}"
                for label, value in zip(headers, row)
            )
            story.extend(
                [
                    Paragraph(text, body),
                    HRFlowable(
                        width="100%", thickness=0.3, color=colors.HexColor("#e5e8ee")
                    ),
                    Spacer(1, 12),
                ]
            )
        else:
            story.append(
                Paragraph(" — ".join(escape(str(value)) for value in row), body)
            )

    def page_number(canvas, document):
        canvas.saveState()
        canvas.setFont("DEDCMyanmar", 8)
        canvas.drawRightString(A4[0] - 42, 24, str(document.page))
        canvas.restoreState()

    document.build(story, onFirstPage=page_number, onLaterPages=page_number)
    return stream.getvalue()
