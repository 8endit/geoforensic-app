import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


AmpelValue = Literal["gruen", "gelb", "rot"]
AuthProvider = Literal["email", "google", "apple"]
VALID_MODULES = {
    "classic", "timeseries", "rawdata", "compliance",
    "insar-bodenbewegung", "hochwasser-ror", "klimaatlas", "altlasten",
    "funderingslabel", "bergbau", "radon", "bodenqualitaet", "gebaeudedaten",
}
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
    auth_provider: str = "email"
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
    selected_modules: list[str] = Field(
        default_factory=lambda: ["insar-bodenbewegung"],
        min_length=1,
        max_length=10,
        alias="modules",
        validation_alias="modules",
    )

    @field_validator("selected_modules")
    @classmethod
    def sanitize_modules(cls, v: list[str]) -> list[str]:
        # Strip unknown module IDs, deduplicate, ensure "classic" is always present
        seen: set[str] = set()
        clean: list[str] = []
        for m in v:
            if m in VALID_MODULES and m not in seen:
                seen.add(m)
                clean.append(m)
        if "insar-bodenbewegung" not in seen and "classic" not in seen:
            clean.insert(0, "insar-bodenbewegung")
        return clean


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
    pdf_available: bool = False
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


class SocialAuthRequest(BaseModel):
    provider: AuthProvider
    id_token: str
    name: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str

