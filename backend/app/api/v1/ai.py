from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.ticket import Ticket
from app.schemas.ticket import TicketResponse
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])

@router.get("/tickets/{ticket_id}/similar", response_model=list[TicketResponse])
def similar_tickets(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: "User" = Depends(get_current_user),
):
    # Ensure ticket exists (optional)
    return ai_service.find_similar_tickets(ticket_id, db)

@router.get("/tickets/{ticket_id}/suggestion", response_model=dict)
def ticket_suggestion(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: "User" = Depends(get_current_user),
):
    suggestion = ai_service.generate_resolution_suggestion(ticket_id, db)
    return {"suggestion": suggestion}
