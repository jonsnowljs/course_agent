from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Response, Query
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from app.api.deps import CurrentUser
from app.core.notion_integration import fetch_all_pages, fetch_page_content, NotionAPIError
from app.core.qdrant_service import store_document
from app.core.notion_oauth import get_authorization_url, exchange_code_for_token
from app.models import User, NotionSyncStatus
from sqlmodel import Session, select
from app.core.db import engine
import uuid
from datetime import datetime

router = APIRouter(prefix="/notion", tags=["notion"])

class NotionSyncRequest(BaseModel):
    notion_token: str

class NotionSyncResponse(BaseModel):
    synced_pages: int
    details: list[str]

@router.post("/sync", response_model=NotionSyncResponse)
def sync_notion_pages(
    req: NotionSyncRequest,
    current_user: CurrentUser 
):
    """
    Sync all available Notion pages for the user and store them in the RAG vector store.
    """
    try:
        pages = fetch_all_pages(req.notion_token)
    except NotionAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    details = []
    synced = 0
    for page in pages:
        page_id = page["id"]
        title = "Untitled"
        # Try to extract title from properties
        props = page.get("properties", {})
        for prop in props.values():
            if prop.get("type") == "title":
                title_items = prop.get("title", [])
                if title_items:
                    title = title_items[0]["plain_text"]
                break
        try:
            content = fetch_page_content(req.notion_token, page_id)
            if not content.strip():
                details.append(f"Skipped empty page: {title}")
                continue
            store_document(content, filename=title, user_id=str(current_user.id))
            details.append(f"Synced: {title}")
            synced += 1
        except Exception as e:
            details.append(f"Failed: {title} ({e})")
    return NotionSyncResponse(synced_pages=synced, details=details)

@router.get("/oauth/start")
def notion_oauth_start(request: Request, current_user: CurrentUser = Depends()):
    # Use user ID as state to prevent CSRF
    state = str(current_user.id)
    url = get_authorization_url(state)
    return RedirectResponse(url)

@router.get("/oauth/callback")
def notion_oauth_callback(
    code: str, state: str, request: Request, response: Response
):
    # Find user by state (user_id)
    user_id = uuid.UUID(state)
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            return JSONResponse({"error": "User not found"}, status_code=404)
        try:
            access_token = exchange_code_for_token(code)
            user.notion_access_token = access_token
            session.add(user)
            session.commit()
            return RedirectResponse("/settings?notion=connected")
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

@router.get("/integration/status")
def notion_integration_status(current_user: CurrentUser = Depends()):
    return {
        "connected": bool(current_user.notion_access_token),
        # Optionally add last sync, error, etc.
    }

@router.post("/integration/disconnect")
def notion_integration_disconnect(current_user: CurrentUser = Depends(), session: Session = Depends()):
    user = session.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.notion_access_token = None
    session.add(user)
    session.commit()
    return {"disconnected": True}

@router.get("/sync/status")
def get_notion_sync_status(current_user: CurrentUser = Depends(), session: Session = Depends()):
    status = session.exec(
        select(NotionSyncStatus)
        .where(NotionSyncStatus.user_id == current_user.id)
        .order_by(NotionSyncStatus.started_at.desc())
    ).first()
    if not status:
        return {"status": "never", "last_sync": None, "error": None}
    return {
        "status": status.status,
        "last_sync": status.finished_at or status.started_at,
        "error": status.error_message,
    }

@router.post("/sync/async")
def sync_notion_pages_async(
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(),
    session: Session = Depends(),
):
    if not current_user.notion_access_token:
        raise HTTPException(status_code=400, detail="Notion not connected")
    # Create sync status record
    sync_status = NotionSyncStatus(user_id=current_user.id, status="pending")
    session.add(sync_status)
    session.commit()
    session.refresh(sync_status)
    def do_sync(user_id, token, sync_id):
        from app.core.notion_integration import fetch_all_pages, fetch_page_content
        from app.core.qdrant_service import store_document
        with Session(engine) as session:
            status = session.get(NotionSyncStatus, sync_id)
            if not status:
                return
            status.status = "running"
            session.add(status)
            session.commit()
            try:
                user = session.get(User, user_id)
                if not user:
                    raise Exception("User not found")
                pages = fetch_all_pages(token)
                for page in pages:
                    page_id = page["id"]
                    title = "Untitled"
                    props = page.get("properties", {})
                    for prop in props.values():
                        if prop.get("type") == "title":
                            title_items = prop.get("title", [])
                            if title_items:
                                title = title_items[0]["plain_text"]
                            break
                    content = fetch_page_content(token, page_id)
                    if content.strip():
                        store_document(content, filename=title, user_id=str(user_id))
                status.status = "success"
                status.finished_at = datetime.utcnow()
                status.error_message = None
            except Exception as e:
                status.status = "error"
                status.finished_at = datetime.utcnow()
                status.error_message = str(e)
            session.add(status)
            session.commit()
    background_tasks.add_task(do_sync, current_user.id, current_user.notion_access_token, sync_status.id)
    return {"status": "sync started"}

@router.get("/sync/history")
def get_notion_sync_history(
    current_user: CurrentUser = Depends(),
    session: Session = Depends(),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    search: str | None = Query(None),
):
    q = select(NotionSyncStatus).where(NotionSyncStatus.user_id == current_user.id)
    if status:
        q = q.where(NotionSyncStatus.status == status)
    if start_date:
        try:
            dt = datetime.fromisoformat(start_date)
            q = q.where(NotionSyncStatus.started_at >= dt)
        except Exception:
            pass
    if end_date:
        try:
            dt = datetime.fromisoformat(end_date)
            q = q.where(NotionSyncStatus.started_at <= dt)
        except Exception:
            pass
    if search:
        q = q.where(
            (NotionSyncStatus.error_message.ilike(f"%{search}%")) |
            (NotionSyncStatus.status.ilike(f"%{search}%"))
        )
    total = session.exec(q).count()
    q = q.order_by(NotionSyncStatus.started_at.desc()).offset(offset).limit(limit)
    history = session.exec(q).all()
    return {
        "total": total,
        "items": [
            {
                "status": h.status,
                "started_at": h.started_at,
                "finished_at": h.finished_at,
                "error": h.error_message,
            }
            for h in history
        ]
    } 
