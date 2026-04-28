import uuid
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from balance_service.database import get_db
from balance_service.models import EventStore
from balance_service.aggregate import BalanceAggregate

class EventStoreRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_aggregate(self, aggregate_id: uuid.UUID) -> BalanceAggregate:
        result = await self.db.execute(
            select(EventStore)
            .where(EventStore.aggregate_id == aggregate_id)
            .order_by(EventStore.timestamp)
        )
        events = result.scalars().all()
        
        aggregate = BalanceAggregate(aggregate_id)
        aggregate.load_from_history(events)
        return aggregate

    def save_event(self, event: EventStore):
        self.db.add(event)

def get_event_store_repo(db: AsyncSession = Depends(get_db)) -> EventStoreRepository:
    return EventStoreRepository(db)