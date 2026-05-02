"""
tests/conftest.py
Shared pytest fixtures — session-scoped event loop so the Motor singleton
stays valid across all tests.
"""
import asyncio
import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop shared by all async tests in the session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
