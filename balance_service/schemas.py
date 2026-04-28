from pydantic import BaseModel
import uuid
from datetime import datetime

class CreateBalanceCommand(BaseModel):
    user_id: uuid.UUID

class ChangeBalanceCommand(BaseModel):
    amount: float

class BalanceViewDTO(BaseModel):
    aggregate_id: uuid.UUID
    balance: float

class BalanceHistoryDTO(BaseModel):
    operation: str
    amount: float
    timestamp: datetime