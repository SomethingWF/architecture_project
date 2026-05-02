import uvicorn
import uuid
import threading
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

from eventsourcing.projection import ProjectionRunner
from balance_service.config import READ_MODEL_DB_URL
from balance_service.application import WalletApplication
from balance_service.projection import WalletProjection
from balance_service.view import CustomPostgresWalletView, WalletView, WalletHistoryView

class AmountRequestDTO(BaseModel):
    amount: float

class BalanceViewDTO(BaseModel):
    aggregate_id: uuid.UUID
    balance: float

class BalanceHistoryDTO(BaseModel):
    operation: str
    amount: float
    timestamp: datetime


wallet_app = WalletApplication()
read_engine = create_engine(READ_MODEL_DB_URL)
ReadSessionLocal = sessionmaker(bind=read_engine)

def start_projection_worker():
    print("Запуск фонового воркера (ProjectionRunner)...")
    runner = ProjectionRunner(
        application_class=WalletApplication,
        projection_class=WalletProjection,
        view_class=CustomPostgresWalletView
    )
    runner.run_forever()

@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_thread = threading.Thread(target=start_projection_worker, daemon=True)
    worker_thread.start()
    yield

app = FastAPI(title="Balance Service", lifespan=lifespan)

# Commands
@app.post("/wallets/{user_id}", status_code=201, tags=['Command'])
def create_wallet(user_id: str):
    wallet_id = wallet_app.create_wallet(user_id)
    return {"aggregate_id": wallet_id}

@app.post("/wallets/{wallet_id}/deposit", tags=['Command'])
def deposit_balance(wallet_id: str, req: AmountRequestDTO):
    try:
        wallet_app.deposit(wallet_id, req.amount)
        return {"status": "success", "message": "Событие Deposited зарегистрировано"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/wallets/{wallet_id}/withdraw", tags=['Command'])
def withdraw_balance(wallet_id: str, req: AmountRequestDTO):
    try:
        wallet_app.withdraw(wallet_id, req.amount)
        return {"status": "success", "message": "Событие Withdrawn зарегистрировано"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Query
@app.get("/wallets/{wallet_id}/balance", response_model=BalanceViewDTO, tags=['Query'])
def get_balance(wallet_id: uuid.UUID):
    with ReadSessionLocal() as session:
        view = session.query(WalletView).filter(WalletView.id == str(wallet_id)).first()
        if not view:
            raise HTTPException(status_code=404, detail="Кошелек не найден")
        return BalanceViewDTO(aggregate_id=uuid.UUID(view.id), balance=view.balance)

@app.get("/wallets/{wallet_id}/history", response_model=list[BalanceHistoryDTO], tags=['Query'])
def get_history(wallet_id: uuid.UUID):
    with ReadSessionLocal() as session:
        history = session.query(WalletHistoryView).filter(
            WalletHistoryView.wallet_id == str(wallet_id)
        ).order_by(WalletHistoryView.timestamp.desc()).all()
        
        return [
            BalanceHistoryDTO(
                operation=h.operation,
                amount=h.amount,
                timestamp=h.timestamp
            ) for h in history
        ]

# Dev
@app.get("/wallets", response_model=list[str], tags=['Dev'])
def get_all_wallets():
    with ReadSessionLocal() as session:
        wallets = session.query(WalletView.id).all()
        return [w.id for w in wallets]

@app.delete("/system/reset", status_code=204, tags=['Dev'])
def reset_entire_system():
    with ReadSessionLocal() as session:
        tables_to_truncate = [
            "wallet_read_model",
            "wallet_history_read_model",
            "stored_events",
            "wallet_projection_tracking"
        ]
        
        for table in tables_to_truncate:
            try:
                session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                session.commit()
            except Exception as e:
                session.rollback()
                print(f"Таблица {table} еще не создана или пуста. Пропускаем. Ошибка: {e}")

    print("Система полностью сброшена.")

if __name__ == "__main__":
    uvicorn.run("balance_service.main:app", host="0.0.0.0", port=8082, reload=True)