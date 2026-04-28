import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from balance_service.database import Base

class EventStore(Base):
    __tablename__ = "event_store"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class BalanceView(Base):
    __tablename__ = "balance_views"
    
    aggregate_id = Column(UUID(as_uuid=True), primary_key=True)
    balance = Column(Float, default=0.0)

class BalanceHistoryView(Base):
    __tablename__ = "balance_history_views"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_id = Column(UUID(as_uuid=True), index=True)
    operation = Column(String)
    amount = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)