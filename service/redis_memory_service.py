import json
import os
from redis.asyncio import Redis
from utils.logger import logger

class RedisMemoryService:
    def __init__(self, redis_url: str = None):
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.ttl = 86400  # 24 hours

    async def get_history(self, session_id: str) -> str:
        """Retrieve conversation history for a session."""
        try:
            history = await self.redis.get(f"session:{session_id}")
            return history if history else "Conversation History:\n"
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return "Conversation History:\n"

    async def append_interaction(self, session_id: str, user_text: str, ai_text: str):
        """Append new user and AI interactions to the session memory."""
        try:
            history = await self.get_history(session_id)
            new_history = history + f"User: {user_text}\nAI: {ai_text}\n"
            await self.redis.setex(f"session:{session_id}", self.ttl, new_history)
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    async def clear_history(self, session_id: str):
        """Clear conversation history."""
        await self.redis.delete(f"session:{session_id}")

# Singleton instance
memory_service = RedisMemoryService()