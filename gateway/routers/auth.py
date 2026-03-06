"""gateway/routers/auth.py — API key + JWT auth endpoints."""

import secrets
from datetime import datetime, timedelta
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "config"))
from settings import settings

logger = structlog.get_logger()
router = APIRouter()
security = HTTPBearer()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ApiKeyRequest(BaseModel):
    api_key: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.api_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.api_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


@router.post("/token", response_model=TokenResponse)
async def get_token(request: ApiKeyRequest):
    """Exchange an API key for a JWT token."""
    if not request.api_key:
        raise HTTPException(status_code=400, detail="API key required")

    token = create_access_token({"sub": request.api_key, "key": request.api_key})
    logger.info("auth.token_issued")
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get("/validate")
async def validate_api_key(api_key: str = ""):
    """
    Simple API key validation used by the Telegram and Discord bots.
    Accepts the key as a query param or X-API-Key header.
    In production, validate against the users table in PostgreSQL.
    For now, any non-empty key is accepted.
    """
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    # TODO: query users table: SELECT id FROM users WHERE api_key = $1
    return {"valid": True, "user_key": api_key}


@router.get("/me")
async def get_me(payload: dict = Depends(verify_token)):
    return {"user_key": payload.get("sub"), "authenticated": True}
