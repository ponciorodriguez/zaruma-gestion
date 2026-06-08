import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.config import (
    ESTIMATES_PDF_DIR,
    INVOICES_PDF_DIR,
)


def _money(value):
    try:
        return f"{float(value):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00 €"


def _empty_if_zero(value, money=False):
    try:
        number = float(value or 0)
    except Exception:
        return ""

    if number == 0:
        return ""

    if money:
        return _money(number)

    return f"{number:g}"


def _safe_text(value):
    if value is None:
        return ""
    return str(value)


def _ensure_dirs():
    os.makedirs(ESTIMATES_PDF_DIR, exist_ok=True)
    os.makedirs(INVOICES_PDF_DIR, exist_ok=True)







def _draw_page_header_footer(canvas, doc):
    canvas.saveState()

    page_width, page_height = A4

    # Ruta absoluta: /app/static/pdf_header.png dentro de Docker,
    # o static/pdf_header.png en local.
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    header_path = os.path.join(base_dir, "static", "pdf_header.png")

    if os.path.exists(header_path):
        try:
            image = ImageReader(header_path)
            image_width, image_height = image.getSize()

            max_width = 186 * mm
            ratio = image_height / float(image_width)
            draw_width = max_width
            draw_height = max_width * ratio

            x = (page_width - draw_width) / 2
            y = page_height - 8 * mm - draw_height

            canvas.drawImage(
                header_path,
                x,
                y,
                width=draw_width,
                height=draw_height,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#607D8B"))
    canvas.drawRightString(
        page_width - 12 * mm,
        8 * mm,
        f"Página {canvas.getPageNumber()}",
    )

    canvas.restoreState()



def _header_elements(title, document, styles):
    elements = []

    title_table = Table(
        [[
            Paragraph(f"<b>{title}</b>", styles["DocTitle"]),
            Paragraph(
                f"<b>Nº:</b> {document.number}<br/>"
                f"<b>Fecha:</b> {document.date.strftime('%d/%m/%Y') if document.date else ''}",
                styles["RightSmall"],
            ),
        ]],
        colWidths=[110 * mm, 70 * mm],
    )

    title_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.75, colors.HexColor("#607D8B")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elements.append(title_table)
    elements.append(Spacer(1, 6 * mm))

    return elements


def _client_block(client, styles):
    if not client:
        return Paragraph("<b>Cliente:</b> -", styles["Small"])

    lines = [
        "<b>Cliente</b>",
        _safe_text(client.name),
    ]

    if client.tax_id:
        lines.append(f"NIF/CIF: {client.tax_id}")

    if client.address:
        lines.append(_safe_text(client.address).replace("\n", "<br/>"))

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

    if getattr(document, "is_rectifying", False):
        lines.append("<b>Factura rectificada</b>")
        lines.append(f"Número: {getattr(document, 'rectifies_invoice_number', '') or '-'}")
        rectified_date = getattr(document, 'rectifies_invoice_date', None)
        lines.append(f"Fecha: {rectified_date.strftime('%d/%m/%Y') if rectified_date else '-'}")
        reason = getattr(document, 'rectification_reason', '') or '-'
        lines.append(f"Motivo: {_safe_text(reason).replace(chr(10), '<br/>')}")

    if document.title:
        lines.append(f"Obra: {document.title}")

    if document.work_address:
        lines.append(f"Dirección obra: {_safe_text(document.work_address).replace(chr(10), '<br/>')}")

    return Paragraph("<br/>".join(lines), styles["Small"])


def _split_long_text(value, max_chars=320):
    text = _safe_text(value).strip()

    if not text:
        return [""]

    chunks = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        words = line.split()
        current = ""

        for word in words:
            if not current:
                current = word
            elif len(current) + 1 + len(word) <= max_chars:
                current += " " + word
            else:
                chunks.append(current)
                current = word

        if current:
            chunks.append(current)

    return chunks or [""]


def _lines_table(lines, styles):
    data = [
        ["Tipo", "Descripción", "Cantidad", "Precio unit.", "Total"]
    ]

    for line in lines:
        line_type = {
            "mano_obra": "Mano de obra",
            "material": "Material",
            "texto": "",
            "partida": "Partida",
            "otros": "Otros",
        }.get(line.line_type, line.line_type)

        chunks = _split_long_text(line.description)

        for idx, chunk in enumerate(chunks):
            if idx == 0:
                row_type = line_type
                row_quantity = _empty_if_zero(line.quantity)
                row_unit_price = _empty_if_zero(line.unit_price, money=True)
                row_total = _empty_if_zero(line.line_total, money=True)
            else:
                row_type = ""
                row_quantity = ""
                row_unit_price = ""
                row_total = ""

            data.append(
                [
                    row_type,
                    Paragraph(_safe_text(chunk).replace("\n", "<br/>"), styles["Small"]),
                    row_quantity,
                    row_unit_price,
                    row_total,
                ]
            )

    table = Table(
        data,
        colWidths=[25 * mm, 86 * mm, 22 * mm, 31 * mm, 26 * mm],
        repeatRows=1,
        splitByRow=1,
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ECEFF1")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#263238")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CFD8DC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
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
    wrapper.setStyle(TableStyle([("ALIGN", (0, 0), (0, 0), "RIGHT")]))

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

    styles.add(
        ParagraphStyle(
            name="DocTitle",
            parent=styles["Heading2"],
            fontSize=15,
            leading=18,
        )
    )

    pdf = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=58 * mm,
        bottomMargin=14 * mm,
    )

    story = []

    story.extend(_header_elements(title, document, styles))

    client = _client_block(document.client, styles)
    doc_data = _document_data_block(document, styles, title_label)

    info_table = Table(
        [[client, doc_data]],
        colWidths=[95 * mm, 85 * mm],
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
    story.append(_lines_table(document.lines, styles))
    story.append(Spacer(1, 7 * mm))

    story.append(_totals_table(document))

    if title == "FACTURA PROFORMA":
        story.append(Spacer(1, 5 * mm))
        story.append(
            Paragraph(
                "<b>Esta factura proforma no lleva el IVA incluido.</b>",
                styles["Small"],
            )
        )

    payment_terms = getattr(document, "payment_terms", None)
    if title in ("PRESUPUESTO", "FACTURA", "FACTURA RECTIFICATIVA") and payment_terms:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("<b>Forma de pago</b>", styles["Heading3"]))
        story.append(
            Paragraph(
                _safe_text(payment_terms).replace("\n", "<br/>"),
                styles["Small"],
            )
        )

    if document.notes:
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph("<b>Notas / condiciones</b>", styles["Heading3"]))
        story.append(Paragraph(_safe_text(document.notes).replace("\n", "<br/>"), styles["Small"]))


    if title == "PRESUPUESTO":
        story.extend(_photo_report_elements(document, styles))

    pdf.build(story, onFirstPage=_draw_page_header_footer, onLaterPages=_draw_page_header_footer)


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

    if getattr(invoice, "is_rectifying", False):
        title = "FACTURA RECTIFICATIVA"
        title_label = "Datos de la factura rectificativa"
    else:
        title = "FACTURA"
        title_label = "Datos de la factura"

    _build_document_pdf(
        document=invoice,
        output_path=output_path,
        title=title,
        title_label=title_label,
    )

    return output_path


def generate_proforma_pdf(proforma):
    output_dir = os.path.join("pdf", "proformas")
    os.makedirs(output_dir, exist_ok=True)

    safe_number = proforma.number.replace("/", "-").replace("\\", "-")
    filename = f"{safe_number}.pdf"
    output_path = os.path.join(output_dir, filename)

    _build_document_pdf(
        document=proforma,
        output_path=output_path,
        title="FACTURA PROFORMA",
        title_label="Datos de la proforma",
    )

    return output_path


def _photo_report_elements(document, styles):
    photos = [
        photo for photo in getattr(document, "photos", [])
        if getattr(photo, "include_in_report", False) and os.path.exists(getattr(photo, "file_path", ""))
    ]

    if not photos:
        return []

    elements = [
        PageBreak(),
        Paragraph("<b>ANEXO FOTOGRÁFICO</b>", styles["Heading2"]),
        Spacer(1, 6 * mm),
    ]

    rows = []
    current_row = []

    for photo in photos:
        img = Image(photo.file_path)

        max_width = 82 * mm
        max_height = 70 * mm

        ratio = min(
            max_width / float(img.imageWidth),
            max_height / float(img.imageHeight),
        )

        img.drawWidth = img.imageWidth * ratio
        img.drawHeight = img.imageHeight * ratio

        caption = getattr(photo, "caption", "") or ""
        cell_content = [
            img,
            Spacer(1, 3 * mm),
            Paragraph(_safe_text(caption).replace("\n", "<br/>"), styles["Small"]),
        ]

        current_row.append(cell_content)

        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []

    if current_row:
        current_row.append("")
        rows.append(current_row)

    table = Table(
        rows,
        colWidths=[90 * mm, 90 * mm],
        hAlign="CENTER",
    )

    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#CFD8DC")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CFD8DC")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    elements.append(table)

    return elements
