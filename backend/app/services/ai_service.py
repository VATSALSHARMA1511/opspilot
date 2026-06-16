from typing import List

from fastapi import HTTPException
from groq import Groq
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import TicketStatus
from app.models.ticket import Ticket, TicketEmbedding


def _groq_client() -> Groq:
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY not configured")
    return Groq(api_key=settings.GROQ_API_KEY)


def generate_embedding(text: str) -> List[float]:
    """
    Groq doesn't have an embeddings API yet.
    We use a simple deterministic fallback for now:
    in production swap this for OpenAI / Cohere / any embeddings provider.
    """
    raise HTTPException(
        status_code=503,
        detail="Embedding generation requires an embeddings provider (OpenAI/Cohere). Add OPENAI_API_KEY to .env to enable."
    )


def find_similar_tickets(ticket_id: int, db: Session, limit: int = 5) -> List[Ticket]:
    source_emb = db.query(TicketEmbedding).filter(
        TicketEmbedding.ticket_id == ticket_id
    ).first()
    if not source_emb:
        raise HTTPException(status_code=404, detail="Ticket embedding not found. Run generate_embeddings.py first.")

    similar_embeddings = (
        db.query(TicketEmbedding)
        .join(Ticket, Ticket.id == TicketEmbedding.ticket_id)
        .filter(Ticket.id != ticket_id)
        .filter(Ticket.status == TicketStatus.RESOLVED)
        .order_by(TicketEmbedding.embedding.cosine_distance(source_emb.embedding))
        .limit(limit)
        .all()
    )

    tickets = [db.get(Ticket, emb.ticket_id) for emb in similar_embeddings]
    return [t for t in tickets if t is not None]


def generate_resolution_suggestion(ticket_id: int, db: Session) -> str:
    similar = find_similar_tickets(ticket_id, db, limit=3)
    if not similar:
        return "No similar resolved tickets found to generate a suggestion."

    prompt_parts = [
        "You are an IT support assistant. Based on the following similar resolved tickets, provide a concise resolution suggestion.",
        "---",
    ]
    for t in similar:
        prompt_parts.append(
            f"Title: {t.title}\nDescription: {t.description}\nResolution: {t.resolution_notes or 'N/A'}\n---"
        )
    prompt_parts.append("Provide a short, actionable resolution suggestion for the current ticket.")
    prompt = "\n".join(prompt_parts)

    client = _groq_client()
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Suggestion generation failed: {e}")