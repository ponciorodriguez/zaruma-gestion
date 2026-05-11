import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.config import (
    COMPANY_ADDRESS,
    COMPANY_EMAIL,
    COMPANY_NAME,
    COMPANY_NIF,
    COMPANY_PHONE,
    ESTIMATES_PDF_DIR,
    INVOICES_PDF_DIR,
)


def _money(value):
    try:
        return f"{float(value):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00 €"


def _safe_text(value):
    if value is None:
        return ""
    return str(value)


def _ensure_dirs():
    os.makedirs(ESTIMATES_PDF_DIR, exist_ok=True)
    os.makedirs(INVOICES_PDF_DIR, exist_ok=True)


def _logo_element():
    logo_path = "static/logo.png"

    if not os.path.exists(logo_path):
        return Paragraph("", getSampleStyleSheet()["Normal"])

    try:
        img = Image(logo_path)
        img.drawHeight = 22 * mm
        img.drawWidth = 45 * mm
        return img
    except Exception:
        return Paragraph("", getSampleStyleSheet()["Normal"])


def _company_block(styles):
    company_lines = [
        f"<b>{COMPANY_NAME or 'Zaruma'}</b>",
    ]

    if COMPANY_NIF:
        company_lines.append(f"NIF/CIF: {COMPANY_NIF}")

    if COMPANY_ADDRESS:
        company_lines.append(COMPANY_ADDRESS)

    if COMPANY_PHONE:
        company_lines.append(f"Tel: {COMPANY_PHONE}")

    if COMPANY_EMAIL:
        company_lines.append(COMPANY_EMAIL)

    return Paragraph("<br/>".join(company_lines), styles["Small"])


def _header(title, number, styles):
    logo = _logo_element()

    doc_info = Paragraph(
        f"<b>{title}</b><br/>"
        f"Nº: {number}<br/>"
        f"Fecha generación: {datetime.now().strftime('%d/%m/%Y')}",
        styles["RightSmall"],
    )

    table = Table(
        [[logo, doc_info]],
        colWidths=[95 * mm, 80 * mm],
    )

    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )

    return table


def _client_block(client, styles):
    if not client:
        return Paragraph("<b>Cliente:</b> -", styles["Normal"])

    lines = [
        "<b>Cliente</b>",
        _safe_text(client.name),
    ]

    if client.tax_id:
        lines.append(f"NIF/CIF: {client.tax_id}")

    if client.address:
        lines.append(client.address)

    if client.phone:
        lines.append(f"Tel: {client.phone}")

    if client.email:
        lines.append(client.email)

    return Paragraph("<br/>".join(lines), styles["Small"])


def _document_data_block(document, styles, title_label):
    lines = [
        f"<b>{title_label}</b>",
        f"Número: {document.number}",
        f"Fecha: {document.date.strftime('%d/%m/%Y') if document.date else ''}",
        f"Estado: {document.status}",
    ]

    if document.title:
        lines.append(f"Obra: {document.title}")

    if document.work_address:
        lines.append(f"Dirección obra: {document.work_address}")

    return Paragraph("<br/>".join(lines), styles["Small"])


def _lines_table(lines):
    data = [
        [
            "Tipo",
            "Descripción",
            "Cantidad",
            "Precio unit.",
            "Total",
        ]
    ]

    for line in lines:
        line_type = {
            "mano_obra": "Mano de obra",
            "material": "Material",
            "otros": "Otros",
        }.get(line.line_type, line.line_type)

        data.append(
            [
                line_type,
                Paragraph(_safe_text(line.description), getSampleStyleSheet()["Small"]),
                f"{line.quantity:g}",
                _money(line.unit_price),
                _money(line.line_total),
            ]
        )

    table = Table(
        data,
        colWidths=[28 * mm, 78 * mm, 23 * mm, 30 * mm, 30 * mm],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#263238")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B0BEC5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FAFAFA")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    return table


def _totals_table(document):
    data = [
        ["Subtotal mano de obra", _money(document.subtotal_labor)],
        ["Subtotal materiales", _money(document.subtotal_materials)],
        ["Otros conceptos", _money(document.subtotal_others)],
        ["Base imponible", _money(document.base_amount)],
        [f"IVA {document.vat_rate:g}%", _money(document.vat_amount)],
        ["TOTAL", _money(document.total_amount)],
    ]

    table = Table(data, colWidths=[55 * mm, 35 * mm])

    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.HexColor("#263238")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ECEFF1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    wrapper = Table([[table]], colWidths=[190 * mm])
    wrapper.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (0, 0), "RIGHT"),
            ]
        )
    )

    return wrapper


def _build_document_pdf(document, output_path, title, title_label):
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["Normal"],
            fontSize=8,
            leading=11,
        )
    )

    styles.add(
        ParagraphStyle(
            name="RightSmall",
            parent=styles["Small"],
            alignment=TA_RIGHT,
        )
    )

    pdf = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=14 * mm,
    )

    story = []

    story.append(_header(title, document.number, styles))
    story.append(Spacer(1, 5 * mm))

    company = _company_block(styles)
    client = _client_block(document.client, styles)
    doc_data = _document_data_block(document, styles, title_label)

    info_table = Table(
        [
            [company, client, doc_data],
        ],
        colWidths=[60 * mm, 65 * mm, 65 * mm],
    )

    info_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#CFD8DC")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CFD8DC")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.append(info_table)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("<b>Partidas</b>", styles["Heading3"]))
    story.append(_lines_table(document.lines))
    story.append(Spacer(1, 7 * mm))

    story.append(_totals_table(document))

    if document.notes:
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph("<b>Notas / condiciones</b>", styles["Heading3"]))
        story.append(Paragraph(_safe_text(document.notes).replace("\n", "<br/>"), styles["Small"]))

    story.append(Spacer(1, 10 * mm))

    footer_text = "Documento generado con Zaruma Gestión"
    story.append(Paragraph(footer_text, styles["Small"]))

    pdf.build(story)


def generate_estimate_pdf(estimate):
    _ensure_dirs()

    safe_number = estimate.number.replace("/", "-").replace("\\", "-")
    filename = f"{safe_number}.pdf"
    output_path = os.path.join(ESTIMATES_PDF_DIR, filename)

    _build_document_pdf(
        document=estimate,
        output_path=output_path,
        title="PRESUPUESTO",
        title_label="Datos del presupuesto",
    )

    return output_path


def generate_invoice_pdf(invoice):
    _ensure_dirs()

    safe_number = invoice.number.replace("/", "-").replace("\\", "-")
    filename = f"{safe_number}.pdf"
    output_path = os.path.join(INVOICES_PDF_DIR, filename)

    _build_document_pdf(
        document=invoice,
        output_path=output_path,
        title="FACTURA",
        title_label="Datos de la factura",
    )

    return output_path
