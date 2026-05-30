from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import APP_NAME
from app.db import Base, engine
from app.routes import clients, estimate_photos, estimates, instructions, invoices, materials, proformas, settings
from app.utils import money

Base.metadata.create_all(bind=engine)

app = FastAPI(title=APP_NAME)

app.include_router(clients.router)
app.include_router(estimates.router)
app.include_router(estimate_photos.router)
app.include_router(instructions.router)
app.include_router(invoices.router)
app.include_router(materials.router)
app.include_router(proformas.router)
app.include_router(settings.router)

Path("uploads/estimate_photos").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/pdf", StaticFiles(directory="pdf"), name="pdf")

templates = Jinja2Templates(directory="templates")
templates.env.filters["money"] = money


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "app_name": APP_NAME,
        },
    )
