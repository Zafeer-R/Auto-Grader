from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/lti", tags=["lti"])


@router.post("/login")
async def lti_login(request: Request):
    """OIDC login initiation endpoint — Canvas redirects here first."""
    # TODO: Implement full OIDC login initiation with pylti1p3 when Canvas is configured
    # For now, this is a placeholder; dev-mode bypass in dev.py handles local testing
    return {"error": "LTI not configured. Use /dev/launch for local testing."}


@router.post("/launch")
async def lti_launch(request: Request, db: AsyncSession = Depends(get_db)):
    """LTI 1.3 resource link launch — Canvas posts here after OIDC auth."""
    # TODO: Validate JWT, extract claims, create session
    # Placeholder until Canvas admin provides developer key
    return {"error": "LTI not configured. Use /dev/launch for local testing."}
