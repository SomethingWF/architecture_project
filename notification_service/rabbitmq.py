import aio_pika
import json
import logging
import asyncio
from notification_service.config import settings

logger = logging.getLogger("uvicorn")

class EventConsumerListener:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        self.queue = None

    async def process_message(self, message: aio_pika.IncomingMessage):
        async with message.process():
            event_data = json.loads(message.body.decode("utf-8"))
            logger.info(f"Получено событие: {message.routing_key}, {event_data['id']}, {event_data['name']}, {event_data['email']}")
    
    async def connect(self):
        self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange("user.exchange", aio_pika.ExchangeType.TOPIC, durable=True)
        self.queue = await self.channel.declare_queue("user.events", durable=True)
        await self.queue.bind(self.exchange, routing_key="user.#")
        logger.info("Notification Service listener запущен")

    async def consume_events(self):
        await self.queue.consume(self.process_message)
        logger.info("Listener готов принимать сообщения")

    async def close(self):
        if self.connection:
            await self.connection.close()
        logger.info("Listener остановлен")

listener = EventConsumerListener()