import logging
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.routes.tickets import create_ticket
from app.core.config import settings
from app.models.outbox_event import OutboxEvent
from app.schemas.ticket import TicketCreate


def make_db():
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    async def flush():
        ticket = db.add.call_args_list[0].args[0]

        if ticket.id is None:
            ticket.id = uuid.uuid4()

    db.flush = AsyncMock(side_effect=flush)

    return db


def make_user():
    return SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
    )


@pytest.mark.asyncio
async def test_notification_feature_enabled_creates_outbox_event(
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "feature_ticket_notifications_enabled",
        True,
    )

    db = make_db()

    ticket = await create_ticket(
        payload=TicketCreate(
            title="Feature flag test",
            description="Notifications enabled",
            priority="medium",
        ),
        db=db,
        current_user=make_user(),
    )

    assert ticket.id is not None
    assert db.add.call_count == 2

    outbox_event = db.add.call_args_list[1].args[0]

    assert isinstance(outbox_event, OutboxEvent)
    assert outbox_event.event_type == "ticket_created"
    assert outbox_event.payload["ticket_id"] == str(ticket.id)


@pytest.mark.asyncio
async def test_notification_feature_disabled_skips_outbox_event(
    monkeypatch,
    caplog,
):
    monkeypatch.setattr(
        settings,
        "feature_ticket_notifications_enabled",
        False,
    )

    db = make_db()

    with caplog.at_level(
        logging.WARNING,
        logger="opspilot.tickets",
    ):
        ticket = await create_ticket(
            payload=TicketCreate(
                title="Feature flag regression",
                description="Notifications disabled",
                priority="medium",
            ),
            db=db,
            current_user=make_user(),
        )

    assert ticket.id is not None
    assert db.add.call_count == 1

    assert (
        "Ticket notification feature disabled; "
        "outbox event skipped"
        in caplog.text
    )