from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.template_globals import register_template_globals

from app.config import (
    APP_NAME,
    COMPANY_ADDRESS,
    COMPANY_EMAIL,
    COMPANY_NAME,
    COMPANY_NIF,
    COMPANY_PHONE,
    DEFAULT_VAT_RATE,
    NOTICE_EMAIL_ENABLED,
    NOTICE_EMAIL_TO,
)

router = APIRouter()
templates = register_template_globals(Jinja2Templates(directory="templates"))


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "request": request,
            "app_name": APP_NAME,
            "company_name": COMPANY_NAME,
            "company_nif": COMPANY_NIF,
            "company_address": COMPANY_ADDRESS,
            "company_phone": COMPANY_PHONE,
            "company_email": COMPANY_EMAIL,
            "default_vat_rate": DEFAULT_VAT_RATE,
            "notice_email_to": NOTICE_EMAIL_TO,
            "notice_email_enabled": NOTICE_EMAIL_ENABLED,
        },
    )
