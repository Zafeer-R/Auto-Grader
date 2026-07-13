"""Dev-mode routes for local testing without Canvas LTI.

Only mounted when DEBUG=true. Simulates LTI launch with test users.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/dev", tags=["dev"])

DEV_USERS = {
    "student": {"lti_user_id": "dev-student-001", "display_name": "Test Student", "role": "student"},
    "ta": {"lti_user_id": "dev-ta-001", "display_name": "Test TA", "role": "ta"},
    "instructor": {"lti_user_id": "dev-instructor-001", "display_name": "Test Instructor", "role": "instructor"},
}


@router.get("/launch")
@router.get("/launch/{role}")
async def dev_launch(
    request: Request,
    role: str = "student",
    assignment_id: str = "lab01",
    db: AsyncSession = Depends(get_db),
):
    """Simulate an LTI launch for local development.

    Usage:
        /dev/launch              → launch as student for lab01
        /dev/launch/ta           → launch as TA
        /dev/launch?assignment_id=lab08  → launch for lab08
    """
    if role not in DEV_USERS:
        return {"error": f"Invalid role. Use one of: {', '.join(DEV_USERS.keys())}"}

    user_data = DEV_USERS[role]

    # Upsert user
    result = await db.execute(
        select(User).where(User.lti_user_id == user_data["lti_user_id"])
    )
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            lti_user_id=user_data["lti_user_id"],
            display_name=user_data["display_name"],
            role=user_data["role"],
            course_id="dev-course-001",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Store session info
    request.session["user_id"] = user.id
    request.session["role"] = user.role
    request.session["assignment_id"] = assignment_id

    return RedirectResponse(url=f"/assignment/{assignment_id}", status_code=303)
