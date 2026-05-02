"""
db/connection.py
MongoDB Atlas async connection — motor driver.
Single client instance shared across all agents.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from config.settings import settings
from utils.logging import get_logger

log = get_logger(__name__)

_async_client: AsyncIOMotorClient | None = None
_sync_client: MongoClient | None = None


def get_async_client() -> AsyncIOMotorClient:
    global _async_client
    if _async_client is None:
        _async_client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            maxPoolSize=50,
            minPoolSize=5,
        )
        log.info("MongoDB async client initialised")
    return _async_client


def get_sync_client() -> MongoClient:
    global _sync_client
    if _sync_client is None:
        _sync_client = MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
        )
        log.info("MongoDB sync client initialised")
    return _sync_client


def get_db() -> AsyncIOMotorDatabase:
    """Returns the phantom_trade async database handle."""
    return get_async_client()[settings.mongodb_db]


def get_sync_db():
    """Returns the phantom_trade sync database handle (for seed scripts)."""
    return get_sync_client()[settings.mongodb_db]


async def ping_db() -> bool:
    """Health check — returns True if Atlas is reachable."""
    try:
        await get_async_client().admin.command("ping")
        log.info("MongoDB Atlas ping successful")
        return True
    except Exception as e:
        log.error("MongoDB Atlas ping failed", error=str(e))
        return False


async def close_connections() -> None:
    global _async_client, _sync_client
    if _async_client:
        _async_client.close()
        _async_client = None
    if _sync_client:
        _sync_client.close()
        _sync_client = None
    log.info("MongoDB connections closed")
