import uvicorn
import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager

from notification_service.rabbitmq import listener

@asynccontextmanager
async def lifespan(app: FastAPI):
    await listener.connect()
    task = asyncio.create_task(listener.consume_events())
    yield
    task.cancel()
    await listener.close()

app = FastAPI(title="Notification Service", lifespan=lifespan)

if __name__ == "__main__":
    uvicorn.run("notification_service.main:app", host="0.0.0.0", port=8081, reload=True)