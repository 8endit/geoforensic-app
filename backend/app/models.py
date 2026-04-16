import enum
import uuid
from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class ReportStatus(str, enum.Enum):
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Ampel(str, enum.Enum):
    gruen = "gruen"
    gelb = "gelb"
    rot = "rot"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255))
    gutachter_type: Mapped[str | None] = mapped_column(String(255))
    auth_provider: Mapped[str] = mapped_column(String(20), nullable=False, default="email")
    auth_provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    reports: Mapped[list["Report"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    address_input: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    radius_m: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    aktenzeichen: Mapped[str | None] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="DE")
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), nullable=False, default=ReportStatus.processing)
    ampel: Mapped[Ampel | None] = mapped_column(Enum(Ampel))
    geo_score: Mapped[int | None] = mapped_column(Integer)
    paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    report_data: Mapped[dict | None] = mapped_column(JSONB)
    pdf_path: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="reports")
    payment: Mapped["Payment | None"] = relationship(back_populates="report", uselist=False)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reports.id"), nullable=False, unique=True)
    stripe_session_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.pending)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    report: Mapped["Report"] = relationship(back_populates="payment")


class EgmsPoint(Base):
    __tablename__ = "egms_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    geom: Mapped[str] = mapped_column(Geometry("POINT", srid=4326, spatial_index=True), nullable=False)
    mean_velocity_mm_yr: Mapped[float] = mapped_column(Float, nullable=False)
    velocity_std: Mapped[float | None] = mapped_column(Float)
    coherence: Mapped[float | None] = mapped_column(Float)
    measurement_start: Mapped[date | None] = mapped_column(Date)
    measurement_end: Mapped[date | None] = mapped_column(Date)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="DE")

    timeseries: Mapped[list["EgmsTimeSeries"]] = relationship(
        back_populates="point",
        cascade="all, delete-orphan",
    )


class EgmsTimeSeries(Base):
    __tablename__ = "egms_timeseries"

    point_id: Mapped[int] = mapped_column(ForeignKey("egms_points.id"), primary_key=True)
    measurement_date: Mapped[date] = mapped_column(Date, primary_key=True)
    displacement_mm: Mapped[float] = mapped_column(Float, nullable=False)

    point: Mapped["EgmsPoint"] = relationship(back_populates="timeseries")

