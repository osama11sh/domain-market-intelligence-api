"""Step 3 - RDAP domain availability checking for .com, .net, .ai, .org."""

import asyncio
import logging
import httpx

logger = logging.getLogger(__name__)

# .com/.net hit Verisign's RDAP directly (fast, proven reliable). .org and .ai
# go through rdap.org, a free public RFC 7484 bootstrap proxy that redirects
# to the authoritative registry's RDAP server - avoids hardcoding registry
# endpoints we can't verify for every TLD.
_DIRECT_BASES = {
    ".com": "https://rdap.verisign.com/com/v1/domain",
    ".net": "https://rdap.verisign.com/net/v1/domain",
}
_BOOTSTRAP_BASE = "https://rdap.org/domain"

ALL_EXTENSIONS = [".com", ".net", ".ai", ".org", ".store", ".site", ".online", ".co", ".io", ".app", ".dev"]
_BATCH_SIZE = 10
_DELAY_BETWEEN_BATCHES = 0.75   # seconds — Verisign is stricter than rdap.org
_REQUEST_TIMEOUT = 8.0


def _rdap_url(domain: str, ext: str) -> str:
    if ext in _DIRECT_BASES:
        return f"{_DIRECT_BASES[ext]}/{domain}"
    return f"{_BOOTSTRAP_BASE}/{domain}"


async def _check_one(client: httpx.AsyncClient, name: str, ext: str) -> dict:
    domain = name + ext
    url = _rdap_url(domain, ext)
    available: bool | None = False
    try:
        resp = await client.get(url, timeout=_REQUEST_TIMEOUT)
        if resp.status_code == 404:
            available = True
        elif resp.status_code == 200:
            available = False
        elif resp.status_code == 403:
            available = None  # CentralNic blocks RDAP queries for .store/.site/.online — treat as unknown
        # 429 / 5xx → assume registered (conservative)
    except (httpx.TimeoutException, httpx.RequestError):
        pass  # treat as registered on network error
    return {"name": name, "extension": ext, "domain": domain, "available": available}


async def check_availability(names: list[str], extensions: list[str] | None = None) -> list[dict]:
    """Return availability records for all names × the requested extensions.

    Only the requested extensions are checked (default: all 4), which both
    keeps RDAP call volume down when a filter narrows extensions and avoids
    unnecessary load on the upstream registries.
    """
    exts = extensions or ALL_EXTENSIONS
    pairs = [(name, ext) for name in names for ext in exts]
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


def group_by_name(records: list[dict]) -> dict[str, dict[str, bool | None]]:
    """Collapse flat availability records into name -> {ext: available}."""
    grouped: dict[str, dict[str, bool | None]] = {}
    for rec in records:
        grouped.setdefault(rec["name"], {})[rec["extension"]] = rec["available"]
    return grouped
