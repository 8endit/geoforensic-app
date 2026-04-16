from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models import Lead
from app.rate_limit import limiter

router = APIRouter(prefix="/api/leads", tags=["leads"])


class LeadCreate(BaseModel):
    email: EmailStr
    answers: dict | None = None
    timestamp: str | None = None
    source: str = "quiz"


class LeadResponse(BaseModel):
    id: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/hour")
async def capture_lead(
    request: Request,
    payload: LeadCreate,
    db: AsyncSession = Depends(get_db),
):
    lead = Lead(
        email=payload.email,
        quiz_answers=payload.answers,
        source=payload.source,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return LeadResponse(
        id=str(lead.id),
        email=lead.email,
        created_at=lead.created_at,
    )
