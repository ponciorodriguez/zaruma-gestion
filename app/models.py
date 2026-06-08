from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    tax_id = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    phone = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    estimates = relationship("Estimate", back_populates="client")
    invoices = relationship("Invoice", back_populates="client")


class Estimate(Base):
    __tablename__ = "estimates"

    id = Column(Integer, primary_key=True, index=True)

    number = Column(String(50), unique=True, nullable=False)
    date = Column(Date, default=date.today)

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    client = relationship("Client", back_populates="estimates")

    title = Column(String(255), nullable=True)
    work_address = Column(Text, nullable=True)
    status = Column(String(50), default="borrador")

    notes = Column(Text, nullable=True)

    subtotal_labor = Column(Float, default=0)
    subtotal_materials = Column(Float, default=0)
    subtotal_others = Column(Float, default=0)

    base_amount = Column(Float, default=0)
    vat_rate = Column(Float, default=21)
    vat_amount = Column(Float, default=0)
    total_amount = Column(Float, default=0)

    pdf_path = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    lines = relationship(
        "EstimateLine",
        back_populates="estimate",
        cascade="all, delete-orphan",
    )

    photos = relationship(
        "EstimatePhoto",
        back_populates="estimate",
        cascade="all, delete-orphan",
        order_by="EstimatePhoto.position",
    )


class EstimateLine(Base):
    __tablename__ = "estimate_lines"

    id = Column(Integer, primary_key=True, index=True)

    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=False)
    estimate = relationship("Estimate", back_populates="lines")

    line_type = Column(String(50), default="otros")
    description = Column(Text, nullable=False)
    quantity = Column(Float, default=1)
    unit_price = Column(Float, default=0)
    line_total = Column(Float, default=0)

    position = Column(Integer, default=0)


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)

    number = Column(String(50), unique=True, nullable=False)
    date = Column(Date, default=date.today)

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    client = relationship("Client", back_populates="invoices")

    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=True)

    title = Column(String(255), nullable=True)
    work_address = Column(Text, nullable=True)
    status = Column(String(50), default="pendiente")

    notes = Column(Text, nullable=True)
    payment_terms = Column(Text, nullable=True)

    subtotal_labor = Column(Float, default=0)
    subtotal_materials = Column(Float, default=0)
    subtotal_others = Column(Float, default=0)

    base_amount = Column(Float, default=0)
    vat_rate = Column(Float, default=21)
    vat_amount = Column(Float, default=0)
    total_amount = Column(Float, default=0)

    pdf_path = Column(String(500), nullable=True)

    is_rectifying = Column(Boolean, default=False)
    rectifies_invoice_number = Column(String(50), nullable=True)
    rectifies_invoice_date = Column(Date, nullable=True)
    rectification_reason = Column(Text, nullable=True)


    created_at = Column(DateTime, default=datetime.utcnow)

    lines = relationship(
        "InvoiceLine",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id = Column(Integer, primary_key=True, index=True)

    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    invoice = relationship("Invoice", back_populates="lines")

    line_type = Column(String(50), default="otros")
    description = Column(Text, nullable=False)
    quantity = Column(Float, default=1)
    unit_price = Column(Float, default=0)
    line_total = Column(Float, default=0)

    position = Column(Integer, default=0)


class Proforma(Base):
    __tablename__ = "proformas"

    id = Column(Integer, primary_key=True, index=True)

    number = Column(String(50), unique=True, nullable=False)
    date = Column(Date, default=date.today)

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    client = relationship("Client")

    title = Column(String(255), nullable=True)
    work_address = Column(Text, nullable=True)
    status = Column(String(50), default="borrador")

    notes = Column(Text, nullable=True)

    subtotal_labor = Column(Float, default=0)
    subtotal_materials = Column(Float, default=0)
    subtotal_others = Column(Float, default=0)

    base_amount = Column(Float, default=0)
    vat_rate = Column(Float, default=21)
    vat_amount = Column(Float, default=0)
    total_amount = Column(Float, default=0)

    pdf_path = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    lines = relationship(
        "ProformaLine",
        back_populates="proforma",
        cascade="all, delete-orphan",
    )


class ProformaLine(Base):
    __tablename__ = "proforma_lines"

    id = Column(Integer, primary_key=True, index=True)

    proforma_id = Column(Integer, ForeignKey("proformas.id"), nullable=False)
    proforma = relationship("Proforma", back_populates="lines")

    line_type = Column(String(50), default="otros")
    description = Column(Text, nullable=False)
    quantity = Column(Float, default=1)
    unit_price = Column(Float, default=0)
    line_total = Column(Float, default=0)

    position = Column(Integer, default=0)


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    unit = Column(String(50), default="ud")
    default_price = Column(Float, default=0)

    notes = Column(Text, nullable=True)
    active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class EstimatePhoto(Base):
    __tablename__ = "estimate_photos"

    id = Column(Integer, primary_key=True, index=True)

    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=False)
    estimate = relationship("Estimate", back_populates="photos")

    file_path = Column(String(500), nullable=False)
    caption = Column(Text, nullable=True)
    include_in_report = Column(Boolean, default=True)

    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
