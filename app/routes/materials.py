from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import models
from app.config import APP_NAME
from app.db import get_db
from app.utils import money
from app.template_globals import register_template_globals

router = APIRouter()
templates = register_template_globals(Jinja2Templates(directory="templates"))
templates.env.filters["money"] = money


@router.get("/materials", response_class=HTMLResponse)
def materials_page(request: Request, db: Session = Depends(get_db)):
    materials = (
        db.query(models.Material)
        .order_by(models.Material.active.desc(), models.Material.name.asc())
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="materials.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "materials": materials,
        },
    )


@router.get("/new-material", response_class=HTMLResponse)
def new_material_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="new_material.html",
        context={
            "request": request,
            "app_name": APP_NAME,
        },
    )


@router.post("/materials")
def create_material(
    name: str = Form(...),
    category: str = Form(""),
    unit: str = Form("ud"),
    default_price: float = Form(0),
    notes: str = Form(""),
    active: str = Form("yes"),
    db: Session = Depends(get_db),
):
    material = models.Material(
        name=name.strip(),
        category=category.strip(),
        unit=unit.strip() or "ud",
        default_price=default_price,
        notes=notes,
        active=(active == "yes"),
    )

    db.add(material)
    db.commit()

    return RedirectResponse(url="/materials", status_code=303)


@router.get("/edit-material/{material_id}", response_class=HTMLResponse)
def edit_material_page(
    material_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    material = db.query(models.Material).filter(models.Material.id == material_id).first()

    if not material:
        return RedirectResponse(url="/materials", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="edit_material.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "material": material,
        },
    )


@router.post("/edit-material/{material_id}")
def update_material(
    material_id: int,
    name: str = Form(...),
    category: str = Form(""),
    unit: str = Form("ud"),
    default_price: float = Form(0),
    notes: str = Form(""),
    active: str = Form("yes"),
    db: Session = Depends(get_db),
):
    material = db.query(models.Material).filter(models.Material.id == material_id).first()

    if not material:
        return RedirectResponse(url="/materials", status_code=303)

    material.name = name.strip()
    material.category = category.strip()
    material.unit = unit.strip() or "ud"
    material.default_price = default_price
    material.notes = notes
    material.active = active == "yes"

    db.commit()

    return RedirectResponse(url="/materials", status_code=303)


@router.get("/api/materials")
def api_materials(db: Session = Depends(get_db)):
    materials = (
        db.query(models.Material)
        .filter(models.Material.active == True)
        .order_by(models.Material.category.asc(), models.Material.name.asc())
        .all()
    )

    return [
        {
            "id": material.id,
            "name": material.name,
            "category": material.category or "",
            "unit": material.unit or "ud",
            "default_price": material.default_price or 0,
            "notes": material.notes or "",
        }
        for material in materials
    ]
