from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import models
from app.config import APP_NAME, DEFAULT_VAT_RATE
from app.db import get_db
from app.pdf_generator import generate_estimate_pdf
from app.utils import calculate_totals, generate_estimate_number, money

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.filters["money"] = money


@router.get("/estimates", response_class=HTMLResponse)
def estimates_page(request: Request, db: Session = Depends(get_db)):
    estimates = db.query(models.Estimate).order_by(models.Estimate.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="estimates.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "estimates": estimates,
        },
    )


@router.get("/new-estimate", response_class=HTMLResponse)
def new_estimate_page(request: Request, db: Session = Depends(get_db)):
    clients = db.query(models.Client).order_by(models.Client.name.asc()).all()
    next_number = generate_estimate_number(db)

    return templates.TemplateResponse(
        request=request,
        name="new_estimate.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "clients": clients,
            "next_number": next_number,
            "today": date.today(),
            "default_vat_rate": DEFAULT_VAT_RATE,
        },
    )


@router.post("/estimates")
def create_estimate(
    client_id: int = Form(...),
    estimate_date: str = Form(...),
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
    totals = calculate_totals(lines_data, vat_rate)

    estimate = models.Estimate(
        number=generate_estimate_number(db),
        date=date.fromisoformat(estimate_date),
        client_id=client_id,
        title=title,
        work_address=work_address,
        notes=notes,
        status="borrador",
        subtotal_labor=totals["subtotal_labor"],
        subtotal_materials=totals["subtotal_materials"],
        subtotal_others=totals["subtotal_others"],
        base_amount=totals["base_amount"],
        vat_rate=totals["vat_rate"],
        vat_amount=totals["vat_amount"],
        total_amount=totals["total_amount"],
    )

    db.add(estimate)
    db.flush()

    _save_estimate_lines(db, estimate.id, totals["lines"])
    db.commit()

    return RedirectResponse(url=f"/estimates/{estimate.id}", status_code=303)


@router.get("/estimates/{estimate_id}", response_class=HTMLResponse)
def view_estimate(
    estimate_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    estimate = db.query(models.Estimate).filter(models.Estimate.id == estimate_id).first()

    if not estimate:
        return RedirectResponse(url="/estimates", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="view_estimate.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "estimate": estimate,
        },
    )


@router.get("/edit-estimate/{estimate_id}", response_class=HTMLResponse)
def edit_estimate_page(
    estimate_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    estimate = db.query(models.Estimate).filter(models.Estimate.id == estimate_id).first()

    if not estimate:
        return RedirectResponse(url="/estimates", status_code=303)

    clients = db.query(models.Client).order_by(models.Client.name.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="edit_estimate.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "estimate": estimate,
            "clients": clients,
        },
    )


@router.post("/edit-estimate/{estimate_id}")
def update_estimate(
    estimate_id: int,
    client_id: int = Form(...),
    estimate_date: str = Form(...),
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
    estimate = db.query(models.Estimate).filter(models.Estimate.id == estimate_id).first()

    if not estimate:
        return RedirectResponse(url="/estimates", status_code=303)

    lines_data = _build_lines_data(line_type, description, quantity, unit_price)
    totals = calculate_totals(lines_data, vat_rate)

    estimate.date = date.fromisoformat(estimate_date)
    estimate.client_id = client_id
    estimate.title = title
    estimate.work_address = work_address
    estimate.notes = notes
    estimate.subtotal_labor = totals["subtotal_labor"]
    estimate.subtotal_materials = totals["subtotal_materials"]
    estimate.subtotal_others = totals["subtotal_others"]
    estimate.base_amount = totals["base_amount"]
    estimate.vat_rate = totals["vat_rate"]
    estimate.vat_amount = totals["vat_amount"]
    estimate.total_amount = totals["total_amount"]
    estimate.pdf_path = None

    db.query(models.EstimateLine).filter(models.EstimateLine.estimate_id == estimate.id).delete()
    db.flush()

    _save_estimate_lines(db, estimate.id, totals["lines"])
    db.commit()

    return RedirectResponse(url=f"/estimates/{estimate.id}", status_code=303)


@router.post("/estimates/{estimate_id}/generate-pdf")
def generate_estimate_pdf_route(
    estimate_id: int,
    db: Session = Depends(get_db),
):
    estimate = db.query(models.Estimate).filter(models.Estimate.id == estimate_id).first()

    if not estimate:
        return RedirectResponse(url="/estimates", status_code=303)

    pdf_path = generate_estimate_pdf(estimate)
    estimate.pdf_path = pdf_path
    db.commit()

    return RedirectResponse(url=f"/estimates/{estimate.id}", status_code=303)


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


def _save_estimate_lines(db, estimate_id, lines):
    for position, line in enumerate(lines, start=1):
        db.add(
            models.EstimateLine(
                estimate_id=estimate_id,
                line_type=line["line_type"],
                description=line["description"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                line_total=line["line_total"],
                position=position,
            )
        )
