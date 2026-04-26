import logging
from typing import Optional
import uuid

import redis.asyncio as aioredis

from user_service.config import settings
from user_service.schemas import UserDTO

logger = logging.getLogger("uvicorn")
redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

class UserCacheService:
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis
        self.cache_prefix = "user:v1:"
        self.ttl = 60

    async def get_from_cache(self, user_id: uuid.UUID) -> Optional[UserDTO]:
        data = await self.redis.get(f"{self.cache_prefix}{user_id}")
        if data:
            logger.info("User cache hit")
            return UserDTO.model_validate_json(data)
        logger.info("User cache miss")
        return None

    async def save_to_cache(self, user: UserDTO):
        await self.redis.set(
            f"{self.cache_prefix}{user.id}",
            user.model_dump_json(),
            ex=self.ttl
        )

    async def remove_from_cache(self, user_id: uuid.UUID):
        await self.redis.delete(f"{self.cache_prefix}{user_id}")

def get_cache_service():
    return UserCacheService(redis_client)