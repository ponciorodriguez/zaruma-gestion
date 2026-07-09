from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import models
from app.db import get_db
from app.template_globals import register_template_globals

router = APIRouter()
templates = register_template_globals(Jinja2Templates(directory="templates"))


@router.get("/notes")
def list_notes(request: Request, db: Session = Depends(get_db)):
    notes = (
        db.query(models.InternalNote)
        .order_by(models.InternalNote.status.asc(), models.InternalNote.created_at.desc())
        .all()
    )

    open_count = (
        db.query(models.InternalNote)
        .filter(models.InternalNote.status == "open")
        .count()
    )

    return templates.TemplateResponse(
        request=request,
        name="notes.html",
        context={
            "notes": notes,
            "open_notes_count": open_count,
        },
    )


@router.post("/notes")
def create_note(
    title: str = Form("Nota interna"),
    message: str = Form(...),
    db: Session = Depends(get_db),
):
    note = models.InternalNote(
        title=(title or "Nota interna").strip(),
        message=message.strip(),
        status="open",
    )
    db.add(note)
    db.commit()

    return RedirectResponse(url="/notes", status_code=303)




@router.get("/notes/{note_id}/edit")
def edit_note_page(note_id: int, request: Request, db: Session = Depends(get_db)):
    note = db.query(models.InternalNote).filter(models.InternalNote.id == note_id).first()

    if not note:
        return RedirectResponse(url="/notes", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="edit_note.html",
        context={
            "note": note,
        },
    )


@router.post("/notes/{note_id}/edit")
def update_note(
    note_id: int,
    title: str = Form("Nota interna"),
    message: str = Form(...),
    db: Session = Depends(get_db),
):
    note = db.query(models.InternalNote).filter(models.InternalNote.id == note_id).first()

    if note:
        note.title = (title or "Nota interna").strip()
        note.message = message.strip()
        db.commit()

    return RedirectResponse(url="/notes", status_code=303)


@router.post("/notes/{note_id}/close")
def close_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(models.InternalNote).filter(models.InternalNote.id == note_id).first()

    if note:
        note.status = "closed"
        note.closed_at = datetime.utcnow()
        db.commit()

    return RedirectResponse(url="/notes", status_code=303)


@router.post("/notes/{note_id}/reopen")
def reopen_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(models.InternalNote).filter(models.InternalNote.id == note_id).first()

    if note:
        note.status = "open"
        note.closed_at = None
        db.commit()

    return RedirectResponse(url="/notes", status_code=303)


@router.post("/notes/{note_id}/delete")
def delete_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(models.InternalNote).filter(models.InternalNote.id == note_id).first()

    if note:
        db.delete(note)
        db.commit()

    return RedirectResponse(url="/notes", status_code=303)
