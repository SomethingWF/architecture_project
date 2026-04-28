import uuid
from typing import List
from balance_service.models import EventStore

class BalanceAggregate:
    def __init__(self, aggregate_id: uuid.UUID):
        self.aggregate_id = aggregate_id
        self.balance: float = 0.0
        self.exists: bool = False
        
        self.uncommitted_events: List[EventStore] = []

    def load_from_history(self, events: List[EventStore]):
        for event in events:
            self.apply_event(event)

    def apply_event(self, event: EventStore):
        handler_name = f"apply_{event.event_type}"
        handler = getattr(self, handler_name, self._unhandled_event)
        handler(event)

    def apply_BalanceCreated(self, event: EventStore):
        self.exists = True
        self.balance = 0.0

    def apply_BalanceCredited(self, event: EventStore):
        self.balance += event.payload["amount"]

    def apply_BalanceDebited(self, event: EventStore):
        self.balance -= event.payload["amount"]

    def _unhandled_event(self, event: EventStore):
        pass 


    def create(self):
        if self.exists:
            raise ValueError("Balance already exists for this user")
        event = EventStore(aggregate_id=self.aggregate_id, event_type="BalanceCreated", payload={})
        self.apply_event(event)
        self.uncommitted_events.append(event)

    def credit(self, amount: float):
        if not self.exists:
            raise ValueError("Balance not found")
        if amount <= 0:
            raise ValueError("Amount must be strictly greater than 0")
            
        event = EventStore(aggregate_id=self.aggregate_id, event_type="BalanceCredited", payload={"amount": amount})
        self.apply_event(event)
        self.uncommitted_events.append(event)

    def debit(self, amount: float):
        if not self.exists:
            raise ValueError("Balance not found")
        if amount <= 0:
            raise ValueError("Amount must be strictly greater than 0")
        if self.balance < amount:
            raise ValueError("Insufficient funds")
        event = EventStore(aggregate_id=self.aggregate_id, event_type="BalanceDebited", payload={"amount": amount})
        self.apply_event(event)
        self.uncommitted_events.append(event)