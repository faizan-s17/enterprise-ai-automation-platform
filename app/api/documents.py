import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import (
    APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status,
)
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user, record_audit, require_analyst
from app.database import get_db
from app.models import Document, DocumentStatus, DocumentType, User
from app.schemas import DocumentDetail, DocumentOut
from app.services import documents as docsvc

router = APIRouter(prefix="/documents", tags=["Document Intelligence"])


@router.post("/upload", response_model=DocumentDetail,
             status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    """Upload a document, then extract and analyse it.

    Runs synchronously so the caller gets the analysis in one round trip. A
    queue would be the right answer at higher volume; the trade-off is noted
    in the technical documentation.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in docsvc.SUPPORTED:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{suffix or 'unknown'}'. "
                   f"Supported: {', '.join(sorted(docsvc.SUPPORTED))}",
        )

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored = upload_dir / f"{uuid.uuid4().hex}{suffix}"

    with stored.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    size = stored.stat().st_size
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if size > max_bytes:
        stored.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File is {size / 1024 / 1024:.1f} MB; the limit is "
                   f"{settings.MAX_UPLOAD_MB} MB",
        )

    doc = Document(
        filename=file.filename or stored.name,
        content_type=file.content_type or "",
        size_bytes=size,
        storage_path=str(stored),
        status=DocumentStatus.PROCESSING,
        uploaded_by_id=user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        text = docsvc.extract_text(stored)
        doc.extracted_text = text
        doc.doc_type = docsvc.classify(text, doc.filename)
        summary, fields, model = docsvc.analyse(text, doc.doc_type)
        doc.ai_summary = summary
        doc.ai_fields = {**fields, "analysed_by": model}
        doc.status = DocumentStatus.ANALYZED
    except Exception as exc:
        # Keep the row so the failure is visible and retryable rather than
        # losing the upload entirely.
        doc.status = DocumentStatus.FAILED
        doc.error = str(exc)[:2000]
    finally:
        doc.processed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(doc)

    record_audit(db, "document.upload", user, "document", doc.id,
                 {"filename": doc.filename, "status": doc.status.value}, request)
    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(
    doc_type: DocumentType | None = None,
    doc_status: DocumentStatus | None = Query(None, alias="status"),
    search: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Document)
    if doc_type is not None:
        q = q.filter(Document.doc_type == doc_type)
    if doc_status is not None:
        q = q.filter(Document.status == doc_status)
    if search:
        like = f"%{search}%"
        q = q.filter(Document.filename.ilike(like) | Document.ai_summary.ilike(like))
    return q.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/{document_id}/reanalyse", response_model=DocumentDetail)
def reanalyse(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    """Re-run analysis on stored text, without re-uploading the file.

    Useful after configuring an AI key: documents processed by the local
    fallback can be upgraded in place.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.extracted_text:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This document has no extracted text to analyse",
        )

    summary, fields, model = docsvc.analyse(doc.extracted_text, doc.doc_type)
    doc.ai_summary = summary
    doc.ai_fields = {**fields, "analysed_by": model}
    doc.status = DocumentStatus.ANALYZED
    doc.error = ""
    doc.processed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(doc)
    record_audit(db, "document.reanalyse", user, "document", doc.id,
                 {"model": model}, request)
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.storage_path:
        Path(doc.storage_path).unlink(missing_ok=True)
    db.delete(doc)
    db.commit()
    record_audit(db, "document.delete", user, "document", document_id, request=request)
