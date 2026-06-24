import os
from urllib.parse import quote
from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import models
from app.config import APP_NAME, DEFAULT_VAT_RATE
from app.db import get_db
from app.pdf_generator import generate_invoice_pdf
from app.mail_sender import send_pdf_email
from app.config import PDF_EMAIL_TO
from app.utils import (
    calculate_totals,
    generate_invoice_number,
    generate_rectifying_invoice_number,
    money,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.filters["money"] = money


DEFAULT_PAYMENT_TERMS = """30% en el momento de la aceptación del presupuesto mediante transferencia a la cuenta ES51 0049 7616 1120 1002 5183 (Banco Santander)
Resto al finalizar el trabajo."""


@router.get("/invoices", response_class=HTMLResponse)
def invoices_page(request: Request, db: Session = Depends(get_db)):
    invoices = db.query(models.Invoice).order_by(models.Invoice.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="invoices.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "invoices": invoices,
        },
    )


@router.get("/new-invoice", response_class=HTMLResponse)
def new_invoice_page(request: Request, db: Session = Depends(get_db)):
    clients = db.query(models.Client).order_by(models.Client.name.asc()).all()
    next_number = generate_invoice_number(db)

    return templates.TemplateResponse(
        request=request,
        name="new_invoice.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "clients": clients,
            "next_number": next_number,
            "today": date.today(),
            "default_vat_rate": DEFAULT_VAT_RATE,
            "default_payment_terms": DEFAULT_PAYMENT_TERMS,
        },
    )


@router.post("/invoices")
def create_invoice(
    client_id: int = Form(...),
    invoice_date: str = Form(...),
    title: str = Form(""),
    work_address: str = Form(""),
    notes: str = Form(""),
    payment_terms: str = Form(DEFAULT_PAYMENT_TERMS),
    vat_rate: float = Form(DEFAULT_VAT_RATE),
    line_type: list[str] = Form([]),
    description: list[str] = Form([]),
    quantity: list[float] = Form([]),
    unit_price: list[float] = Form([]),
    db: Session = Depends(get_db),
):
    lines_data = _build_lines_data(line_type, description, quantity, unit_price)
    totals = calculate_totals(lines_data, vat_rate)

    invoice = models.Invoice(
        number=generate_invoice_number(db),
        date=date.fromisoformat(invoice_date),
        client_id=client_id,
        title=title,
        work_address=work_address,
        notes=notes,
        payment_terms=payment_terms,
        status="pendiente",
        is_rectifying=False,
        subtotal_labor=totals["subtotal_labor"],
        subtotal_materials=totals["subtotal_materials"],
        subtotal_others=totals["subtotal_others"],
        base_amount=totals["base_amount"],
        vat_rate=totals["vat_rate"],
        vat_amount=totals["vat_amount"],
        total_amount=totals["total_amount"],
    )

    db.add(invoice)
    db.flush()

    _save_invoice_lines(db, invoice.id, totals["lines"])
    db.commit()

    return RedirectResponse(url=f"/invoices/{invoice.id}", status_code=303)


@router.get("/invoices/{invoice_id}", response_class=HTMLResponse)
def view_invoice(
    invoice_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()

    if not invoice:
        return RedirectResponse(url="/invoices", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="view_invoice.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "invoice": invoice,
        },
    )


@router.get("/edit-invoice/{invoice_id}", response_class=HTMLResponse)
def edit_invoice_page(
    invoice_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()

    if not invoice:
        return RedirectResponse(url="/invoices", status_code=303)

    if invoice.status == "enviada":
        return RedirectResponse(url=f"/invoices/{invoice.id}", status_code=303)

    clients = db.query(models.Client).order_by(models.Client.name.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="edit_invoice.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "invoice": invoice,
            "clients": clients,
        },
    )


@router.post("/edit-invoice/{invoice_id}")
def update_invoice(
    invoice_id: int,
    client_id: int = Form(...),
    invoice_date: str = Form(...),
    title: str = Form(""),
    work_address: str = Form(""),
    notes: str = Form(""),
    payment_terms: str = Form(DEFAULT_PAYMENT_TERMS),
    vat_rate: float = Form(DEFAULT_VAT_RATE),
    line_type: list[str] = Form([]),
    description: list[str] = Form([]),
    quantity: list[float] = Form([]),
    unit_price: list[float] = Form([]),
    db: Session = Depends(get_db),
):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()

    if not invoice:
        return RedirectResponse(url="/invoices", status_code=303)

    if invoice.status == "enviada":
        return RedirectResponse(url=f"/invoices/{invoice.id}", status_code=303)

    lines_data = _build_lines_data(line_type, description, quantity, unit_price)
    totals = calculate_totals(lines_data, vat_rate)

    invoice.date = date.fromisoformat(invoice_date)
    invoice.client_id = client_id
    invoice.title = title
    invoice.work_address = work_address
    invoice.notes = notes
    invoice.payment_terms = payment_terms
    invoice.subtotal_labor = totals["subtotal_labor"]
    invoice.subtotal_materials = totals["subtotal_materials"]
    invoice.subtotal_others = totals["subtotal_others"]
    invoice.base_amount = totals["base_amount"]
    invoice.vat_rate = totals["vat_rate"]
    invoice.vat_amount = totals["vat_amount"]
    invoice.total_amount = totals["total_amount"]
    invoice.pdf_path = None

    db.query(models.InvoiceLine).filter(models.InvoiceLine.invoice_id == invoice.id).delete()
    db.flush()

    _save_invoice_lines(db, invoice.id, totals["lines"])
    db.commit()

    return RedirectResponse(url=f"/invoices/{invoice.id}", status_code=303)


@router.post("/invoices/{invoice_id}/generate-pdf")
def generate_invoice_pdf_route(
    invoice_id: int,
    db: Session = Depends(get_db),
):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()

    if not invoice:
        return RedirectResponse(url="/invoices", status_code=303)

    pdf_path = generate_invoice_pdf(invoice)
    invoice.pdf_path = pdf_path
    db.commit()

    return RedirectResponse(url=f"/invoices/{invoice.id}", status_code=303)


@router.post("/invoices/{invoice_id}/mark-sent")


@router.post("/invoices/{invoice_id}/send-email")
def send_invoice_email_route(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    redirect_url = f"/invoices/{invoice_id}"

    if not PDF_EMAIL_TO:
        error = quote("No está configurado PDF_EMAIL_TO en el .env.")
        return RedirectResponse(url=f"{redirect_url}?email_error={error}", status_code=303)

    if not invoice.pdf_path or not os.path.exists(invoice.pdf_path):
        pdf_path = generate_invoice_pdf(invoice)
        invoice.pdf_path = pdf_path
        db.commit()
        db.refresh(invoice)

    try:
        send_pdf_email(
            to_email=PDF_EMAIL_TO,
            subject=f"Factura rectificativa Zaruma {invoice.number}" if invoice.is_rectifying else f"Factura Zaruma {invoice.number}",
            body=f"""Hola,

Adjuntamos la {"factura rectificativa" if invoice.is_rectifying else "factura"} {invoice.number} en formato PDF.

Quedamos a su disposición para cualquier aclaración.

Un saludo,
Zaruma
""",
            pdf_path=invoice.pdf_path,
        )
    except Exception as exc:
        error = quote(str(exc))
        return RedirectResponse(url=f"{redirect_url}?email_error={error}", status_code=303)

    return RedirectResponse(url=f"{redirect_url}?email_sent=1", status_code=303)


def mark_invoice_sent_route(
    invoice_id: int,
    db: Session = Depends(get_db),
):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()

    if not invoice:
        return RedirectResponse(url="/invoices", status_code=303)

    invoice.status = "enviada"
    db.commit()

    return RedirectResponse(url=f"/invoices/{invoice.id}", status_code=303)


@router.post("/invoices/{invoice_id}/create-rectifying")
def create_rectifying_invoice_route(
    invoice_id: int,
    rectification_reason: str = Form("Anulación total de la factura original."),
    db: Session = Depends(get_db),
):
    original = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()

    if not original:
        return RedirectResponse(url="/invoices", status_code=303)

    rectifying = models.Invoice(
        number=generate_rectifying_invoice_number(db),
        date=date.today(),
        client_id=original.client_id,
        estimate_id=None,
        title=f"Factura rectificativa de {original.number}",
        work_address=original.work_address,
        notes=(
            f"Factura rectificativa de la factura nº {original.number}.\n\n"
            f"Motivo de rectificación: {rectification_reason}"
        ),
        status="pendiente",
        is_rectifying=True,
        rectifies_invoice_number=original.number,
        rectifies_invoice_date=original.date,
        rectification_reason=rectification_reason,
        subtotal_labor=-abs(original.subtotal_labor or 0),
        subtotal_materials=-abs(original.subtotal_materials or 0),
        subtotal_others=-abs(original.subtotal_others or 0),
        base_amount=-abs(original.base_amount or 0),
        vat_rate=original.vat_rate,
        vat_amount=-abs(original.vat_amount or 0),
        total_amount=-abs(original.total_amount or 0),
    )

    db.add(rectifying)
    db.flush()

    for position, line in enumerate(original.lines, start=1):
        db.add(
            models.InvoiceLine(
                invoice_id=rectifying.id,
                line_type=line.line_type,
                description=f"Rectificación factura {original.number}:\n{line.description}",
                quantity=abs(line.quantity or 0),
                unit_price=-abs(line.unit_price or 0),
                line_total=-abs(line.line_total or 0),
                position=position,
            )
        )

    db.commit()

    return RedirectResponse(url=f"/invoices/{rectifying.id}", status_code=303)


def _build_lines_data(line_type, description, quantity, unit_price):
    lines_data = []

    for idx, desc in enumerate(description):
        desc = (desc or "").strip()
        if not desc:
            continue

        lt = line_type[idx] if idx < len(line_type) else "otros"
        qty = quantity[idx] if idx < len(quantity) else 1
        price = unit_price[idx] if idx < len(unit_price) else 0

        lines_data.append(
            {
                "line_type": lt,
                "description": desc,
                "quantity": qty,
                "unit_price": price,
            }
        )

    return lines_data


def _save_invoice_lines(db, invoice_id, lines):
    for position, line in enumerate(lines, start=1):
        db.add(
            models.InvoiceLine(
                invoice_id=invoice_id,
                line_type=line["line_type"],
                description=line["description"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                line_total=line["line_total"],
                position=position,
            )
        )
