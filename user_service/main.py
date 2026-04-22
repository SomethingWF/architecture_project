import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from contextlib import asynccontextmanager
import uuid

from user_service.database import engine, Base, get_db
from user_service.models import User
from user_service.schemas import UserCreateDTO, UserUpdateDTO, UserDTO
from user_service.config import settings

# Автоматическое создание таблиц при старте (для упрощения лабы)
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="User Service API", lifespan=lifespan)

@app.post("/users", response_model=UserDTO)
async def create_user(user_dto: UserCreateDTO, db: AsyncSession = Depends(get_db)):
    # Проверка на дубликат email
    result = await db.execute(select(User).where(User.email == user_dto.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(name=user_dto.name, email=user_dto.email)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@app.get("/users/{user_id}", response_model=UserDTO)
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/users", response_model=list[UserDTO])
async def get_all_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()

if __name__ == "__main__":
    uvicorn.run("user_service.main:app", host="0.0.0.0", port=settings.server_port, reload=True)