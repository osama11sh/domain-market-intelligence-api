"""Step 3 - RDAP domain availability checking for .com and .net."""

import asyncio
import logging
import httpx

logger = logging.getLogger(__name__)

_RDAP_BASES = {
    ".com": "https://rdap.verisign.com/com/v1/domain",
    ".net": "https://rdap.verisign.com/net/v1/domain",
}
_EXTENSIONS = [".com", ".net"]
_BATCH_SIZE = 10
_DELAY_BETWEEN_BATCHES = 0.75   # seconds — Verisign is stricter than rdap.org
_REQUEST_TIMEOUT = 8.0


async def _check_one(client: httpx.AsyncClient, name: str, ext: str) -> dict:
    domain = name + ext
    url = f"{_RDAP_BASES[ext]}/{domain}"
    available = False
    try:
        resp = await client.get(url, timeout=_REQUEST_TIMEOUT)
        if resp.status_code == 404:
            available = True
        elif resp.status_code == 200:
            available = False
        # 429 / 5xx → assume registered (conservative)
    except (httpx.TimeoutException, httpx.RequestError):
        pass  # treat as registered on network error
    return {"name": name, "extension": ext, "domain": domain, "available": available}


async def check_availability(names: list[str]) -> list[dict]:
    """Return availability records for all names × [.com, .net]."""
    pairs = [(name, ext) for name in names for ext in _EXTENSIONS]
    results: list[dict] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": "DomainMarketIntelligence/1.0 (research)"},
        follow_redirects=True,
    ) as client:
        for i in range(0, len(pairs), _BATCH_SIZE):
            batch = pairs[i : i + _BATCH_SIZE]
            batch_results = await asyncio.gather(
                *[_check_one(client, name, ext) for name, ext in batch],
                return_exceptions=True,
            )
            for item in batch_results:
                if isinstance(item, dict):
                    results.append(item)
                else:
                    logger.warning("RDAP batch error: %s", item)
            if i + _BATCH_SIZE < len(pairs):
                await asyncio.sleep(_DELAY_BETWEEN_BATCHES)

    return results
