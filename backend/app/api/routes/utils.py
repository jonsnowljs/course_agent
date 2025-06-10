from fastapi import APIRouter, Depends, HTTPException
from pydantic.networks import EmailStr

from app.api.deps import get_current_active_superuser
from app.models import Message
from app.utils import generate_test_email, send_email
from app.core.qdrant import get_qdrant_client

router = APIRouter(prefix="/utils", tags=["utils"])


@router.post(
    "/test-email/",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=201,
)
def test_email(email_to: EmailStr) -> Message:
    """
    Test emails.
    """
    email_data = generate_test_email(email_to=email_to)
    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Test email sent")


@router.get("/health-check/")
async def health_check() -> bool:
    return True


@router.get("/qdrant-health/")
async def qdrant_health_check() -> bool:
    """Check if Qdrant is accessible."""
    try:
        client = get_qdrant_client()
        # Simple collection list call to check connection
        client.get_collections()
        return True
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Qdrant service unavailable: {str(e)}"
        )
