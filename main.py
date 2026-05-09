from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import APP_NAME
from app.db import Base, engine
from app.utils import money

Base.metadata.create_all(bind=engine)

app = FastAPI(title=APP_NAME)

app.mount("/static", StaticFiles(directory="static"), name="static")
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
