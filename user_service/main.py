import logging
import uuid
from contextlib import asynccontextmanager
import time

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from prometheus_client import make_asgi_app

from user_service.database import engine, Base, get_db
from user_service.models import User
from user_service.schemas import UserCreateDTO, UserUpdateDTO, UserCreatedEvent, UserDTO
from user_service.config import settings
from user_service.cache import redis_client, UserCacheService, get_cache_service
from user_service.rabbitmq import publisher
from user_service.metrics import USERS_CREATED_TOTAL, API_REQUEST_DURATION

logger = logging.getLogger("uvicorn")

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await publisher.connect()
    yield
    await redis_client.aclose()
    await publisher.close()

app = FastAPI(title="User Service API", lifespan=lifespan)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.post("/users", response_model=UserDTO)
async def create_user(user_dto: UserCreateDTO, db: AsyncSession = Depends(get_db)):
    start_time = time.time()

    result = await db.execute(select(User).where(User.email == user_dto.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(name=user_dto.name, email=user_dto.email)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # RabbitMQ
    event = UserCreatedEvent(id=new_user.id, email=new_user.email, name=new_user.name)
    await publisher.publish_user_event(event)

    # Метрики
    USERS_CREATED_TOTAL.inc()
    API_REQUEST_DURATION.labels(method="post", endpoint="/users").observe(time.time() - start_time)
    
    return new_user

@app.get("/users/{user_id}", response_model=UserDTO)
async def get_user(
    user_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db),
    cache: UserCacheService = Depends(get_cache_service)
):
    start_time = time.time()

    # Кэширование
    cached_user = await cache.get_from_cache(user_id)
    if cached_user:
        return cached_user

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_dto = UserDTO.model_validate(user)
    await cache.save_to_cache(user_dto)

    # Метрики
    API_REQUEST_DURATION.labels(method="get", endpoint="/users/{id}").observe(time.time() - start_time)

    return user_dto

@app.patch("/users/{user_id}", response_model=UserDTO)
async def update_user(
    user_id: uuid.UUID,
    user_dto: UserUpdateDTO,
    db: AsyncSession = Depends(get_db),
    cache: UserCacheService = Depends(get_cache_service)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_dto.name:
        user.name = user_dto.name
    if user_dto.email:
        user.email = user_dto.email
        
    await db.commit()
    await db.refresh(user)
    
    # Кэширование
    logger.info("User cache evict on update")
    await cache.remove_from_cache(user_id)
    
    return user

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db),
    cache: UserCacheService = Depends(get_cache_service)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    
    # Кэширование
    logger.info("User cache evict on delete")
    await cache.remove_from_cache(user_id)

@app.get("/users", response_model=list[UserDTO])
async def get_all_users(db: AsyncSession = Depends(get_db)):
    start_time = time.time()
    result = await db.execute(select(User))
    API_REQUEST_DURATION.labels(method="get", endpoint="/users").observe(time.time() - start_time)
    return result.scalars().all()

@app.delete("/users", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_users(
    db: AsyncSession = Depends(get_db),
    cache: UserCacheService = Depends(get_cache_service)
):
    result = await db.execute(select(User.id))
    user_ids = result.scalars().all()

    await db.execute(delete(User))
    await db.commit()

    for uid in user_ids:
        await cache.remove_from_cache(uid)
    
    logger.info(f"Deleted {len(user_ids)} users from DB and Cache.")

if __name__ == "__main__":
    uvicorn.run("user_service.main:app", host="0.0.0.0", port=settings.server_port, reload=True)