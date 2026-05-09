from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import models
from app.config import APP_NAME
from app.db import get_db
from fastapi.templating import Jinja2Templates
from app.utils import money

router = APIRouter()

templates = Jinja2Templates(directory="templates")
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
