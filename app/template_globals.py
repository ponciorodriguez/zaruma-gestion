from app import models
from app.db import SessionLocal


def get_open_notes_count():
    db = SessionLocal()
    try:
        return (
            db.query(models.InternalNote)
            .filter(models.InternalNote.status == "open")
            .count()
        )
    except Exception:
        return 0
    finally:
        db.close()


def register_template_globals(templates):
    templates.env.globals["get_open_notes_count"] = get_open_notes_count
    return templates
