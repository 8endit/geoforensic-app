import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


AmpelValue = Literal["gruen", "gelb", "rot"]
TokenType = Literal["bearer"]


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    company_name: str | None = None
    gutachter_type: str | None = None


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    company_name: str | None = None
    gutachter_type: str | None = None
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: TokenType = "bearer"
    user: UserResponse


class PreviewRequest(BaseModel):
    address: str = Field(min_length=5, max_length=500)


class PreviewResponse(BaseModel):
    ampel: AmpelValue
    point_count: int
    address_resolved: str
    latitude: float
    longitude: float


class ReportCreateRequest(BaseModel):
    address: str = Field(min_length=5, max_length=500)
    radius_m: int = Field(default=500, ge=100, le=2000)
    aktenzeichen: str | None = Field(default=None, max_length=255)


class ReportListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    address_input: str
    status: str
    ampel: str | None
    paid: bool
    geo_score: int | None
    created_at: datetime


class ReportDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    address_input: str
    status: str
    ampel: str | None
    paid: bool
    geo_score: int | None
    latitude: float
    longitude: float
    radius_m: int
    aktenzeichen: str | None
    pdf_available: bool
    report_data: dict[str, Any] | None
    created_at: datetime


class ReportCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    address_input: str
    status: str
    latitude: float
    longitude: float
    radius_m: int
    aktenzeichen: str | None
    created_at: datetime


class CheckoutRequest(BaseModel):
    report_id: uuid.UUID


class CheckoutResponse(BaseModel):
    checkout_url: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str

