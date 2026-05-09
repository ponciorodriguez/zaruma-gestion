from datetime import date

from sqlalchemy.orm import Session

from app import models


def money(value):
    try:
        return f"{float(value):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00 €"


def generate_estimate_number(db: Session):
    year = date.today().year
    prefix = f"P-{year}-"

    last = (
        db.query(models.Estimate)
        .filter(models.Estimate.number.like(f"{prefix}%"))
        .order_by(models.Estimate.id.desc())
        .first()
    )

    if not last:
        next_num = 1
    else:
        try:
            next_num = int(last.number.split("-")[-1]) + 1
        except Exception:
            next_num = 1

    return f"{prefix}{next_num:04d}"


def generate_invoice_number(db: Session):
    year = date.today().year
    prefix = f"F-{year}-"

    last = (
        db.query(models.Invoice)
        .filter(models.Invoice.number.like(f"{prefix}%"))
        .order_by(models.Invoice.id.desc())
        .first()
    )

    if not last:
        next_num = 1
    else:
        try:
            next_num = int(last.number.split("-")[-1]) + 1
        except Exception:
            next_num = 1

    return f"{prefix}{next_num:04d}"


def calculate_totals(lines, vat_rate=21):
    subtotal_labor = 0
    subtotal_materials = 0
    subtotal_others = 0

    for line in lines:
        quantity = float(line.get("quantity") or 0)
        unit_price = float(line.get("unit_price") or 0)
        line_total = quantity * unit_price
        line["line_total"] = line_total

        line_type = line.get("line_type") or "otros"

        if line_type == "mano_obra":
            subtotal_labor += line_total
        elif line_type == "material":
            subtotal_materials += line_total
        else:
            subtotal_others += line_total

    base_amount = subtotal_labor + subtotal_materials + subtotal_others
    vat_amount = base_amount * float(vat_rate) / 100
    total_amount = base_amount + vat_amount

    return {
        "subtotal_labor": subtotal_labor,
        "subtotal_materials": subtotal_materials,
        "subtotal_others": subtotal_others,
        "base_amount": base_amount,
        "vat_rate": float(vat_rate),
        "vat_amount": vat_amount,
        "total_amount": total_amount,
        "lines": lines,
    }
