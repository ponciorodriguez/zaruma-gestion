from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_NAME

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/instructions", response_class=HTMLResponse)
def instructions_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="instructions.html",
        context={
            "request": request,
            "app_name": APP_NAME,
        },
    )
