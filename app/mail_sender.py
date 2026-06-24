import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from app.config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASS,
    SMTP_FROM,
    SMTP_USE_SSL,
    COMPANY_NAME,
    COMPANY_EMAIL,
)


def send_pdf_email(to_email: str, subject: str, body: str, pdf_path: str):
    if not to_email:
        raise ValueError("El cliente no tiene email informado.")

    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        raise ValueError("Configuración SMTP incompleta. Revisa SMTP_HOST, SMTP_USER y SMTP_PASS.")

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"No existe el PDF: {pdf_path}")

    from_email = SMTP_FROM or SMTP_USER
    from_name = COMPANY_NAME or "Zaruma"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email

    if COMPANY_EMAIL:
        msg["Reply-To"] = COMPANY_EMAIL

    msg.set_content(body)

    with pdf_file.open("rb") as f:
        pdf_data = f.read()

    msg.add_attachment(
        pdf_data,
        maintype="application",
        subtype="pdf",
        filename=pdf_file.name,
    )

    if SMTP_USE_SSL:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
