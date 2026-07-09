from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import models
from app.config import APP_NAME
from app.db import get_db
from app.utils import money
from app.template_globals import register_template_globals
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = register_template_globals(Jinja2Templates(directory="templates"))
templates.env.filters["money"] = money


@router.get("/clients", response_class=HTMLResponse)
def clients_page(request: Request, db: Session = Depends(get_db)):
    clients = db.query(models.Client).order_by(models.Client.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="clients.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "clients": clients,
        },
    )


@router.get("/new-client", response_class=HTMLResponse)
def new_client_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="new_client.html",
        context={
            "request": request,
            "app_name": APP_NAME,
        },
    )


@router.post("/clients")
def create_client(
    name: str = Form(...),
    tax_id: str = Form(""),
    address: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    client = models.Client(
        name=name,
        tax_id=tax_id,
        address=address,
        phone=phone,
        email=email,
        notes=notes,
    )

    db.add(client)
    db.commit()

    return RedirectResponse(url="/clients", status_code=303)


@router.get("/edit-client/{client_id}", response_class=HTMLResponse)
def edit_client_page(
    client_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    client = db.query(models.Client).filter(models.Client.id == client_id).first()

    if not client:
        return RedirectResponse(url="/clients", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="edit_client.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "client": client,
        },
    )


@router.post("/edit-client/{client_id}")
def update_client(
    client_id: int,
    name: str = Form(...),
    tax_id: str = Form(""),
    address: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    client = db.query(models.Client).filter(models.Client.id == client_id).first()

    if not client:
        return RedirectResponse(url="/clients", status_code=303)

    client.name = name
    client.tax_id = tax_id
    client.address = address
    client.phone = phone
    client.email = email
    client.notes = notes

    db.commit()

    return RedirectResponse(url="/clients", status_code=303)
