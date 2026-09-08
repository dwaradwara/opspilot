import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate, TicketRead, TicketUpdate
from app.services.jobs import enqueue_ticket_created

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
async def create_ticket(payload: TicketCreate, db: DbSession, current_user: CurrentUser) -> Ticket:
    ticket = Ticket(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    await enqueue_ticket_created(str(ticket.id), str(ticket.organization_id))
    return ticket


@router.get("", response_model=list[TicketRead])
async def list_tickets(db: DbSession, current_user: CurrentUser) -> list[Ticket]:
    result = await db.scalars(
        select(Ticket)
        .where(Ticket.organization_id == current_user.organization_id)
        .order_by(Ticket.created_at.desc())
    )
    return list(result)


@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket(ticket_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> Ticket:
    ticket = await db.scalar(
        select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.organization_id == current_user.organization_id,
        )
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketRead)
async def update_ticket(
    ticket_id: uuid.UUID,
    payload: TicketUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Ticket:
    ticket = await db.scalar(
        select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.organization_id == current_user.organization_id,
        )
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)

    await db.commit()
    await db.refresh(ticket)
    return ticket
