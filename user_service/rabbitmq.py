import aio_pika
from user_service.config import settings
from user_service.schemas import UserCreatedEvent

class UserEventPublisher:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange("user.exchange", aio_pika.ExchangeType.TOPIC, durable=True)

    async def close(self):
        if self.connection:
            await self.connection.close()

    async def publish_user_event(self, event: UserCreatedEvent):
        message_body = event.model_dump_json().encode("utf-8")
        message = aio_pika.Message(
            body=message_body,
            content_type="application/json"
        )
        await self.exchange.publish(message, routing_key="user.created")

publisher = UserEventPublisher()