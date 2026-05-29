from __future__ import annotations

from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.config import FONT_CANDIDATES, OUTPUT_DIR, SUPPORTED_LANGUAGES
from app.services.language import language_label
from app.services.products import get_product


class SvgPlaceholder(Flowable):
    def __init__(self, label: str, width: float, height: float) -> None:
        super().__init__()
        self.label = label
        self.width = width
        self.height = height

    def draw(self) -> None:
        canvas = self.canv
        canvas.setFillColor(colors.HexColor("#f3efe8"))
        canvas.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        canvas.setStrokeColor(colors.HexColor("#b78a5a"))
        canvas.setLineWidth(1)
        canvas.rect(0, 0, self.width, self.height, fill=0, stroke=1)
        canvas.setFillColor(colors.HexColor("#5c4632"))
        canvas.setFont("ManualFont", 12)
        canvas.drawCentredString(self.width / 2, self.height / 2, self.label)


def register_font() -> str:
    for font_path in FONT_CANDIDATES:
        path = Path(font_path)
        if path.exists():
            pdfmetrics.registerFont(TTFont("ManualFont", str(path)))
            return "ManualFont"
    return "Helvetica"


def _styles(font_name: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontName=font_name,
            fontSize=26,
            leading=32,
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=12,
            leading=16,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#555555"),
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName=font_name,
            fontSize=18,
            leading=22,
            spaceBefore=8,
            spaceAfter=8,
            textColor=colors.HexColor("#222222"),
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName=font_name,
            fontSize=12,
            leading=15,
            spaceBefore=8,
            spaceAfter=5,
            textColor=colors.HexColor("#6f4525"),
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9.5,
            leading=13.5,
            alignment=TA_LEFT,
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#666666"),
        ),
    }


def _bullet_list(items: list[str], style: ParagraphStyle) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, style), leftIndent=10) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=14,
    )


def _spec_table(specs: dict[str, str], style: ParagraphStyle) -> Table:
    rows = [[Paragraph(key, style), Paragraph(value, style)] for key, value in specs.items()]
    table = Table(rows, colWidths=[4.2 * cm, 10.2 * cm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "ManualFont"),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3efe8")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d6cabc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("ManualFont", 8)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(1.6 * cm, 1.0 * cm, "Product Manual Agent Demo")
    canvas.drawRightString(19.4 * cm, 1.0 * cm, f"Page {doc.page}")
    canvas.restoreState()


def resolve_languages(product: dict, languages: Optional[list[str]] = None) -> list[str]:
    """Return the languages to render, ordered by SUPPORTED_LANGUAGES.

    Always intersects with the languages the product actually has, so
    uploaded manuals (which may only have ``en``) never raise KeyError.
    Falls back to all available languages when the request is empty.
    """
    available = [lang for lang in SUPPORTED_LANGUAGES if lang in product["languages"]]
    # Include any non-standard language codes the product might carry.
    available += [lang for lang in product["languages"] if lang not in available]
    if not languages:
        return available
    requested = [lang for lang in available if lang in set(languages)]
    return requested or available


def generate_manual_pdf(product_id: str, languages: Optional[list[str]] = None) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    product = get_product(product_id)
    selected_languages = resolve_languages(product, languages)
    font_name = register_font()
    styles = _styles(font_name)
    lang_tag = "-".join(selected_languages)
    path = OUTPUT_DIR / f"{product_id}-manual-{lang_tag}.pdf"
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title="Multilingual Product Manual",
    )

    cover = product["languages"].get("en") or product["languages"][selected_languages[0]]
    lang_codes = " ".join(lang.upper() for lang in selected_languages)
    story: list = [
        Spacer(1, 2.4 * cm),
        Paragraph(cover["name"], styles["cover_title"]),
        Paragraph(f"Multilingual Product Manual / {lang_codes}", styles["cover_subtitle"]),
        Spacer(1, 0.5 * cm),
        SvgPlaceholder("Solid wood table product image", 15.5 * cm, 8.0 * cm),
        Spacer(1, 0.8 * cm),
        Paragraph(cover["summary"], styles["cover_subtitle"]),
        Spacer(1, 0.3 * cm),
        Paragraph(
            "This PDF is generated by the Product Manual Agent demo for cross-border e-commerce buyers.",
            styles["small"],
        ),
        PageBreak(),
    ]

    for index, language in enumerate(selected_languages):
        data = product["languages"][language]
        story.extend(
            [
                Paragraph(f"{language.upper()} - {language_label(language)}", styles["h1"]),
                Paragraph(data["title"], styles["h2"]),
                Paragraph(data["summary"], styles["body"]),
                Spacer(1, 0.2 * cm),
                Paragraph("Product Features", styles["h2"]),
                _bullet_list(data["bullets"], styles["body"]),
                Paragraph("Specifications", styles["h2"]),
                _spec_table(data["specs"], styles["body"]),
                Paragraph("Installation", styles["h2"]),
                KeepTogether([SvgPlaceholder("Assembly diagram: tabletop, legs, brackets", 14.5 * cm, 4.7 * cm)]),
                _bullet_list(data["installation"], styles["body"]),
                Paragraph("Safety", styles["h2"]),
                _bullet_list(data["safety"], styles["body"]),
                Paragraph("Care", styles["h2"]),
                _bullet_list(data["care"], styles["body"]),
                Paragraph("FAQ", styles["h2"]),
            ]
        )
        for item in data["faq"]:
            story.append(Paragraph(f"Q: {item['q']}<br/>A: {item['a']}", styles["body"]))
            story.append(Spacer(1, 0.1 * cm))
        story.append(PageBreak() if index < len(selected_languages) - 1 else Spacer(1, 0.1 * cm))

    story.append(Paragraph("Reference Notes", styles["h1"]))
    story.append(Paragraph(product["source_notes"], styles["body"]))
    for source in product["reference_sources"]:
        story.append(Paragraph(f"- {source}", styles["small"]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return path
