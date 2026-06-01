from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import models
from app.config import APP_NAME, DEFAULT_VAT_RATE
from app.db import get_db
from app.pdf_generator import generate_proforma_pdf
from app.utils import calculate_totals, generate_invoice_number, generate_proforma_number, money

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.filters["money"] = money


@router.get("/proformas", response_class=HTMLResponse)
def proformas_page(request: Request, db: Session = Depends(get_db)):
    proformas = db.query(models.Proforma).order_by(models.Proforma.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="proformas.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "proformas": proformas,
        },
    )


@router.get("/new-proforma", response_class=HTMLResponse)
def new_proforma_page(request: Request, db: Session = Depends(get_db)):
    clients = db.query(models.Client).order_by(models.Client.name.asc()).all()
    next_number = generate_proforma_number(db)

    return templates.TemplateResponse(
        request=request,
        name="new_proforma.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "clients": clients,
            "next_number": next_number,
            "today": date.today(),
            "default_vat_rate": DEFAULT_VAT_RATE,
        },
    )


@router.post("/proformas")
def create_proforma(
    client_id: int = Form(...),
    proforma_date: str = Form(...),
    title: str = Form(""),
    work_address: str = Form(""),
    notes: str = Form(""),
    vat_rate: float = Form(DEFAULT_VAT_RATE),
    line_type: list[str] = Form([]),
    description: list[str] = Form([]),
    quantity: list[float] = Form([]),
    unit_price: list[float] = Form([]),
    db: Session = Depends(get_db),
):
    lines_data = _build_lines_data(line_type, description, quantity, unit_price)
    totals = calculate_totals(lines_data, 0)

    proforma = models.Proforma(
        number=generate_proforma_number(db),
        date=date.fromisoformat(proforma_date),
        client_id=client_id,
        title=title,
        work_address=work_address,
        notes=notes,
        status="borrador",
        subtotal_labor=totals["subtotal_labor"],
        subtotal_materials=totals["subtotal_materials"],
        subtotal_others=totals["subtotal_others"],
        base_amount=totals["base_amount"],
        vat_rate=0,
        vat_amount=totals["vat_amount"],
        total_amount=totals["total_amount"],
    )

    db.add(proforma)
    db.flush()

    _save_proforma_lines(db, proforma.id, totals["lines"])
    db.commit()

    return RedirectResponse(url=f"/proformas/{proforma.id}", status_code=303)


@router.get("/proformas/{proforma_id}", response_class=HTMLResponse)
def view_proforma(
    proforma_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    proforma = db.query(models.Proforma).filter(models.Proforma.id == proforma_id).first()

    if not proforma:
        return RedirectResponse(url="/proformas", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="view_proforma.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "proforma": proforma,
        },
    )


@router.get("/edit-proforma/{proforma_id}", response_class=HTMLResponse)
def edit_proforma_page(
    proforma_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    proforma = db.query(models.Proforma).filter(models.Proforma.id == proforma_id).first()

    if not proforma:
        return RedirectResponse(url="/proformas", status_code=303)

    clients = db.query(models.Client).order_by(models.Client.name.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="edit_proforma.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "proforma": proforma,
            "clients": clients,
        },
    )


@router.post("/edit-proforma/{proforma_id}")
def update_proforma(
    proforma_id: int,
    client_id: int = Form(...),
    proforma_date: str = Form(...),
    title: str = Form(""),
    work_address: str = Form(""),
    notes: str = Form(""),
    vat_rate: float = Form(DEFAULT_VAT_RATE),
    line_type: list[str] = Form([]),
    description: list[str] = Form([]),
    quantity: list[float] = Form([]),
    unit_price: list[float] = Form([]),
    db: Session = Depends(get_db),
):
    proforma = db.query(models.Proforma).filter(models.Proforma.id == proforma_id).first()

    if not proforma:
        return RedirectResponse(url="/proformas", status_code=303)

    lines_data = _build_lines_data(line_type, description, quantity, unit_price)
    totals = calculate_totals(lines_data, 0)

    proforma.date = date.fromisoformat(proforma_date)
    proforma.client_id = client_id
    proforma.title = title
    proforma.work_address = work_address
    proforma.notes = notes
    proforma.subtotal_labor = totals["subtotal_labor"]
    proforma.subtotal_materials = totals["subtotal_materials"]
    proforma.subtotal_others = totals["subtotal_others"]
    proforma.base_amount = totals["base_amount"]
    proforma.vat_rate = 0
    proforma.vat_rate = totals["vat_rate"]
    proforma.vat_amount = totals["vat_amount"]
    proforma.total_amount = totals["total_amount"]
    proforma.pdf_path = None

    db.query(models.ProformaLine).filter(models.ProformaLine.proforma_id == proforma.id).delete()
    db.flush()

    _save_proforma_lines(db, proforma.id, totals["lines"])
    db.commit()

    return RedirectResponse(url=f"/proformas/{proforma.id}", status_code=303)


@router.post("/proformas/{proforma_id}/generate-pdf")
def generate_proforma_pdf_route(
    proforma_id: int,
    db: Session = Depends(get_db),
):
    proforma = db.query(models.Proforma).filter(models.Proforma.id == proforma_id).first()

    if not proforma:
        return RedirectResponse(url="/proformas", status_code=303)

    pdf_path = generate_proforma_pdf(proforma)
    proforma.pdf_path = pdf_path
    db.commit()

    return RedirectResponse(url=f"/proformas/{proforma.id}", status_code=303)


@router.post("/proformas/{proforma_id}/convert-to-invoice")
def convert_proforma_to_invoice_route(
    proforma_id: int,
    db: Session = Depends(get_db),
):
    proforma = db.query(models.Proforma).filter(models.Proforma.id == proforma_id).first()

    if not proforma:
        return RedirectResponse(url="/proformas", status_code=303)

    invoice = models.Invoice(
        number=generate_invoice_number(db),
        date=date.today(),
        client_id=proforma.client_id,
        estimate_id=None,
        title=proforma.title,
        work_address=proforma.work_address,
        notes=proforma.notes,
        status="pendiente",
        subtotal_labor=proforma.subtotal_labor,
        subtotal_materials=proforma.subtotal_materials,
        subtotal_others=proforma.subtotal_others,
        base_amount=proforma.base_amount,
        vat_rate=proforma.vat_rate,
        vat_amount=proforma.vat_amount,
        total_amount=proforma.total_amount,
    )

    db.add(invoice)
    db.flush()

    for position, line in enumerate(proforma.lines, start=1):
        db.add(
            models.InvoiceLine(
                invoice_id=invoice.id,
                line_type=line.line_type,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                line_total=line.line_total,
                position=position,
            )
        )

    proforma.status = "convertida a factura"

    db.commit()

    return RedirectResponse(url=f"/invoices/{invoice.id}", status_code=303)


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


def _save_proforma_lines(db, proforma_id, lines):
    for position, line in enumerate(lines, start=1):
        db.add(
            models.ProformaLine(
                proforma_id=proforma_id,
                line_type=line["line_type"],
                description=line["description"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                line_total=line["line_total"],
                position=position,
            )
        )
