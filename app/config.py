import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Zaruma Gestión")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/database.db")

PDF_BASE_DIR = os.getenv("PDF_BASE_DIR", "./pdf")
ESTIMATES_PDF_DIR = os.path.join(PDF_BASE_DIR, "presupuestos")
INVOICES_PDF_DIR = os.path.join(PDF_BASE_DIR, "facturas")

DEFAULT_VAT_RATE = float(os.getenv("DEFAULT_VAT_RATE", "21"))

COMPANY_NAME = os.getenv("COMPANY_NAME", "Zaruma")
COMPANY_NIF = os.getenv("COMPANY_NIF", "")
COMPANY_ADDRESS = os.getenv("COMPANY_ADDRESS", "")
COMPANY_PHONE = os.getenv("COMPANY_PHONE", "")
COMPANY_EMAIL = os.getenv("COMPANY_EMAIL", "")

NOTICE_EMAIL_TO = os.getenv("NOTICE_EMAIL_TO", "")
NOTICE_EMAIL_ENABLED = os.getenv("NOTICE_EMAIL_ENABLED", "no").lower() == "yes"

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() in ("true", "1", "yes", "si", "sí")
PDF_EMAIL_TO = os.getenv("PDF_EMAIL_TO", "")
