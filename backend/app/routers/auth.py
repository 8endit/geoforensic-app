import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, hash_password, verify_password
from app.dependencies import get_current_user, get_db
from app.models import User
from app.oauth import verify_apple_token, verify_google_token
from app.schemas import (
    AuthResponse,
    SocialAuthRequest,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        company_name=payload.company_name,
        gutachter_type=payload.gutachter_type,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id))
    return AuthResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(payload: UserLoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()
    if user is None or user.password_hash is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(str(user.id))
    return AuthResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/social", response_model=AuthResponse)
async def social_login(payload: SocialAuthRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """Authenticate via Google or Apple ID token. Creates account on first use, links if email matches."""
    # 1. Verify the ID token with the provider
    try:
        if payload.provider == "google":
            claims = verify_google_token(payload.id_token)
        elif payload.provider == "apple":
            claims = await verify_apple_token(payload.id_token)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported provider")
    except ValueError as exc:
        logger.warning("OAuth token verification failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    email = claims["email"]
    provider_id = claims["sub"]

    # 2. Look up by (auth_provider, auth_provider_id) — fast path for returning OAuth users
    result = await db.execute(
        select(User).where(User.auth_provider == payload.provider, User.auth_provider_id == provider_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        # 3. Look up by email — account linking for existing email/password users
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is not None:
            # Link: set provider_id on existing account for future fast-path lookups
            user.auth_provider_id = provider_id
            if user.auth_provider == "email":
                user.auth_provider = payload.provider
            await db.commit()
            await db.refresh(user)
        else:
            # 4. New user — create OAuth-only account (no password)
            user = User(
                email=email,
                password_hash=None,
                auth_provider=payload.provider,
                auth_provider_id=provider_id,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

    token = create_access_token(str(user.id))
    return AuthResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)

