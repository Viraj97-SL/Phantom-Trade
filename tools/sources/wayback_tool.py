"""
tools/sources/wayback_tool.py
Wayback Machine CDX API — verify whether a URL or domain was ever archived.
Key signal: if claim cites Reuters but no reuters.com article exists → fabricated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import aiohttp

from utils.logging import get_logger

log = get_logger(__name__)

_CDX_URL = "https://web.archive.org/cdx/search/cdx"
_TIMEOUT_S = 3


@dataclass(frozen=True)
class WaybackVerification:
    url_queried: str
    found: Optional[bool]  # None = unknown (timeout/error)
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    status_code: Optional[str] = None
    snapshot_count: int = 0


async def verify_url(url_or_domain: str) -> WaybackVerification:
    """
    Check whether a URL or domain has been archived in the Wayback Machine.

    Returns WaybackVerification with found=None if the request times out or fails.
    """
    params = {
        "url": url_or_domain,
        "output": "json",
        "limit": "5",
        "fl": "timestamp,statuscode,original",
        "collapse": "urlkey",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                _CDX_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=_TIMEOUT_S),
            ) as resp:
                if resp.status != 200:
                    return WaybackVerification(url_queried=url_or_domain, found=None)
                rows = await resp.json(content_type=None)
    except Exception as e:
        log.warning("Wayback verification failed", url=url_or_domain, error=str(e))
        return WaybackVerification(url_queried=url_or_domain, found=None)

    # rows[0] is the header ["timestamp", "statuscode", "original"]
    if not rows or len(rows) <= 1:
        return WaybackVerification(url_queried=url_or_domain, found=False)

    data_rows = rows[1:]
    first = data_rows[0] if data_rows else None
    last = data_rows[-1] if data_rows else None
    return WaybackVerification(
        url_queried=url_or_domain,
        found=True,
        first_seen=first[0] if first else None,
        last_seen=last[0] if last else None,
        status_code=first[1] if first else None,
        snapshot_count=len(data_rows),
    )
