import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import models
from app.db import get_db

router = APIRouter()

UPLOAD_DIR = Path("uploads/estimate_photos")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@router.post("/estimates/{estimate_id}/photos")
async def upload_estimate_photos(
    estimate_id: int,
    photos: list[UploadFile] = File([]),
    db: Session = Depends(get_db),
):
    estimate = db.query(models.Estimate).filter(models.Estimate.id == estimate_id).first()

    if not estimate:
        return RedirectResponse(url="/estimates", status_code=303)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    current_count = (
        db.query(models.EstimatePhoto)
        .filter(models.EstimatePhoto.estimate_id == estimate.id)
        .count()
    )

    position = current_count + 1

    for uploaded in photos:
        if not uploaded.filename:
            continue

        ext = Path(uploaded.filename).suffix.lower()

        if ext not in ALLOWED_EXTENSIONS:
            continue

        filename = f"estimate_{estimate.id}_{uuid.uuid4().hex}{ext}"
        destination = UPLOAD_DIR / filename

        content = await uploaded.read()

        if not content:
            continue

        with destination.open("wb") as f:
            f.write(content)

        db.add(
            models.EstimatePhoto(
                estimate_id=estimate.id,
                file_path=str(destination),
                caption="",
                include_in_report=True,
                position=position,
            )
        )

        position += 1

    estimate.pdf_path = None

    db.commit()

    return RedirectResponse(url=f"/estimates/{estimate.id}", status_code=303)


@router.post("/estimate-photos/{photo_id}/update")
def update_estimate_photo(
    photo_id: int,
    caption: str = Form(""),
    include_in_report: str = Form("no"),
    db: Session = Depends(get_db),
):
    photo = db.query(models.EstimatePhoto).filter(models.EstimatePhoto.id == photo_id).first()

    if not photo:
        return RedirectResponse(url="/estimates", status_code=303)

    photo.caption = caption.strip()
    photo.include_in_report = include_in_report == "yes"

    if photo.estimate:
        photo.estimate.pdf_path = None

    db.commit()

    return RedirectResponse(url=f"/estimates/{photo.estimate_id}", status_code=303)


@router.post("/estimate-photos/{photo_id}/delete")
def delete_estimate_photo(
    photo_id: int,
    db: Session = Depends(get_db),
):
    photo = db.query(models.EstimatePhoto).filter(models.EstimatePhoto.id == photo_id).first()

    if not photo:
        return RedirectResponse(url="/estimates", status_code=303)

    estimate_id = photo.estimate_id
    file_path = photo.file_path

    db.delete(photo)

    estimate = db.query(models.Estimate).filter(models.Estimate.id == estimate_id).first()
    if estimate:
        estimate.pdf_path = None

    db.commit()

    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass

    return RedirectResponse(url=f"/estimates/{estimate_id}", status_code=303)
