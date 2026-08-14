from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, record_audit
from app.database import get_db
from app.models import User
from app.schemas import AssistantAnswer, AssistantQuery
from app.services import assistant as assistantsvc

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])


@router.post("/ask", response_model=AssistantAnswer)
def ask(
    payload: AssistantQuery,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Answer a business question from the platform's own records.

    The assistant retrieves matching documents and tickets first and is
    instructed to answer only from them, so an unanswerable question returns
    "not on record" rather than an invented figure.
    """
    result = assistantsvc.ask(db, payload.question, payload.include_documents)
    record_audit(db, "assistant.ask", user, "assistant", None,
                 {"question": payload.question[:300],
                  "sources": len(result["sources"])}, request)
    return result


@router.get("/suggestions", response_model=list[str])
def suggestions(_: User = Depends(get_current_user)):
    """Starter questions, so the assistant is not a blank box in a demo."""
    return [
        "How many documents have been processed?",
        "What invoices are on record and what are they worth?",
        "Which tickets are still open?",
        "Are there any urgent tickets right now?",
        "What approvals are waiting for a decision?",
        "Summarise the contracts we hold.",
    ]
