from typing import Optional
from fastapi import Header, HTTPException, status
from app.config import settings


async def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    """FastAPI dependency — validates X-API-Key header against env var."""
    if not x_api_key or x_api_key != settings.api_secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return x_api_key
