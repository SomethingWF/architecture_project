import uvicorn
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

# Настройки и БД
from balance_service.config import settings
from balance_service.database import engine, Base, get_db

# Схемы (DTO)
from balance_service.schemas import (
    CreateBalanceCommand, 
    ChangeBalanceCommand, 
    BalanceViewDTO, 
    BalanceHistoryDTO
)

# Модели
from balance_service.models import BalanceView, BalanceHistoryView, EventStore

# Бизнес-логика (CQRS, ES, ООП)
from balance_service.repository import EventStoreRepository, get_event_store_repo
from balance_service.projector import projector


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Автоматически создаем таблицы в БД при запуске приложения
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Balance Service (CQRS + ES + Rich Domain Model)", lifespan=lifespan)


# =====================================================================
# COMMAND API (Write Side)
# Изменяют состояние системы. Вся бизнес-логика и генерация событий 
# полностью инкапсулированы внутри Агрегата.
# =====================================================================

@app.post("/balance/create", status_code=status.HTTP_201_CREATED, tags=["Commands"])
async def create_balance(
    cmd: CreateBalanceCommand, 
    db: AsyncSession = Depends(get_db),
    repo: EventStoreRepository = Depends(get_event_store_repo)
):
    # 1. Загружаем историю кошелька
    aggregate = await repo.get_aggregate(cmd.user_id)
    
    # 2. Агрегат сам всё проверяет и сам генерирует событие
    try:
        aggregate.create()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # 3. Сохраняем все новые (незакоммиченные) события, которые создал Агрегат
    for event in aggregate.uncommitted_events:
        repo.save_event(event)
        await projector.project(db, event)
        
    await db.commit()
    
    return {"status": "ok", "message": "Balance created successfully"}


@app.post("/balance/{user_id}/credit", status_code=status.HTTP_200_OK, tags=["Commands"])
async def credit_balance(
    user_id: uuid.UUID, 
    cmd: ChangeBalanceCommand, 
    db: AsyncSession = Depends(get_db),
    repo: EventStoreRepository = Depends(get_event_store_repo)
):
    aggregate = await repo.get_aggregate(user_id)
    
    try:
        aggregate.credit(cmd.amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    for event in aggregate.uncommitted_events:
        repo.save_event(event)
        await projector.project(db, event)
        
    await db.commit()
    
    return {"status": "ok", "message": f"Credited {cmd.amount} successfully"}


@app.post("/balance/{user_id}/debit", status_code=status.HTTP_200_OK, tags=["Commands"])
async def debit_balance(
    user_id: uuid.UUID, 
    cmd: ChangeBalanceCommand, 
    db: AsyncSession = Depends(get_db),
    repo: EventStoreRepository = Depends(get_event_store_repo)
):
    aggregate = await repo.get_aggregate(user_id)
    
    # Страж инвариантов проверяет, хватает ли денег, и создает событие
    try:
        aggregate.debit(cmd.amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    for event in aggregate.uncommitted_events:
        repo.save_event(event)
        await projector.project(db, event)
        
    await db.commit()
    
    return {"status": "ok", "message": f"Debited {cmd.amount} successfully"}


# =====================================================================
# QUERY API (Read Side)
# Читают ТОЛЬКО оптимизированные View-таблицы (Read Models).
# =====================================================================

@app.get("/balance/{user_id}", response_model=BalanceViewDTO, tags=["Queries"])
async def get_balance(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BalanceView).where(BalanceView.aggregate_id == user_id))
    view = result.scalars().first()
    
    if not view:
        raise HTTPException(status_code=404, detail="Balance not found")
        
    return view


@app.get("/balance/{user_id}/history", response_model=list[BalanceHistoryDTO], tags=["Queries"])
async def get_history(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BalanceHistoryView)
        .where(BalanceHistoryView.aggregate_id == user_id)
        .order_by(BalanceHistoryView.timestamp.desc())  # Новые события сверху
    )
    return result.scalars().all()


# =====================================================================
# TESTING API (Для разработки и сброса тестового стенда)
# =====================================================================

@app.delete("/balance/all", status_code=status.HTTP_204_NO_CONTENT, tags=["Testing"])
async def delete_all_balances(db: AsyncSession = Depends(get_db)):
    """
    ВНИМАНИЕ: ЖЕСТКОЕ УДАЛЕНИЕ (Hard Delete). 
    Удаляет всю историю событий и все проекции. 
    Использовать только для очистки тестового окружения!
    """
    # Удаляем Read Models
    await db.execute(delete(BalanceView))
    await db.execute(delete(BalanceHistoryView))
    
    # Удаляем Write Model (Event Store)
    await db.execute(delete(EventStore))
    
    await db.commit()
    print("All balances, history, and events have been hard deleted.")


if __name__ == "__main__":
    uvicorn.run("balance_service.main:app", host="0.0.0.0", port=settings.server_port, reload=True)