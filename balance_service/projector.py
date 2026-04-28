from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from balance_service.models import EventStore, BalanceView, BalanceHistoryView

class BalanceProjector:
    async def project(self, db: AsyncSession, event: EventStore):
        handler_method_name = f"handle_{event.event_type}"
        handler = getattr(self, handler_method_name, self._unhandled_event)
        await handler(db, event)

    async def handle_BalanceCreated(self, db: AsyncSession, event: EventStore):
        result = await db.execute(select(BalanceView).where(BalanceView.aggregate_id == event.aggregate_id))
        if not result.scalars().first():
            view = BalanceView(aggregate_id=event.aggregate_id, balance=0.0)
            db.add(view)

    async def handle_BalanceCredited(self, db: AsyncSession, event: EventStore):
        result = await db.execute(select(BalanceView).where(BalanceView.aggregate_id == event.aggregate_id))
        view = result.scalars().first()
        if view:
            view.balance += event.payload["amount"]
            db.add(BalanceHistoryView(
                aggregate_id=event.aggregate_id, operation="CREDIT", 
                amount=event.payload["amount"], timestamp=event.timestamp
            ))

    async def handle_BalanceDebited(self, db: AsyncSession, event: EventStore):
        result = await db.execute(select(BalanceView).where(BalanceView.aggregate_id == event.aggregate_id))
        view = result.scalars().first()
        if view:
            view.balance -= event.payload["amount"]
            db.add(BalanceHistoryView(
                aggregate_id=event.aggregate_id, operation="DEBIT", 
                amount=event.payload["amount"], timestamp=event.timestamp
            ))

    async def _unhandled_event(self, db: AsyncSession, event: EventStore):
        print(f"Warning: No handler found for event type: {event.event_type}")

projector = BalanceProjector()