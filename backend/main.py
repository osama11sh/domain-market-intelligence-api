"""Domain Market Intelligence Platform - FastAPI backend.

4-step workflow:
  Step 1 — Dual trend streams (brandable + meaningful), run in parallel
  Step 2 — Balanced domain generation (exact count, 50/50 split)
  Step 3 — RDAP availability checking
  Step 4 — 4-dimension scoring (semantic_value, trend_relevance, market_potential, brandability)
"""

import asyncio
import logging
from typing import Literal, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from trends import fetch_dual_trend_streams
from generator import generate_candidates, generate_candidates_balanced
from availability import check_availability, group_by_name, ALL_EXTENSIONS
from scoring import enrich_domain
from semantics import SUPPORTED_LANGUAGES, classify_and_explain
import trend_engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Domain Market Intelligence", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DomainType = Literal["brandable", "meaningful", "both"]


class SearchRequest(BaseModel):
    niche: Optional[str] = None
    languages: Optional[list[str]] = None
    domain_type: DomainType = "both"
    trend_location: str = "auto"
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    cost_min: Optional[float] = None
    cost_max: Optional[float] = None
    score_heat_min: Optional[int] = None
    extensions: Optional[list[str]] = None
    num_results: Optional[int] = None

    @field_validator("niche")
    @classmethod
    def niche_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) > 80:
            raise ValueError("niche too long (max 80 chars)")
        return v

    @field_validator("extensions")
    @classmethod
    def extensions_valid(cls, v):
        if v is None:
            return v
        invalid = [e for e in v if e not in ALL_EXTENSIONS]
        if invalid:
            raise ValueError(f"unsupported extensions: {invalid}")
        return v


class ScoreBreakdown(BaseModel):
    length: int
    pronounceability: int
    keyword_match: int
    spelling: int
    extension: int


class DomainResult(BaseModel):
    name: str
    extension: str
    available: Optional[bool]
    score: int
    length: int
    registration_cost_usd: int
    score_breakdown: ScoreBreakdown
    type: str
    language_origin: str
    meaning: str
    trend_score: int
    heat_index: int
    registrar_availability: dict[str, Optional[bool]]
    geo_breakdown: dict[str, int]
    expected_monthly_clicks: int
    # 4-dimension scores (each 0-10, total 0-40)
    semantic_value: int
    trend_relevance: int
    market_potential: int
    brandability: int
    domain_score_total: int


class SearchResponse(BaseModel):
    domains: list[DomainResult]
    niche: str
    keyword_seeds: list[str]
    trend_source: str
    brandable_keywords: list[str]
    meaningful_keywords: list[str]
    partial_result_note: Optional[str] = None


def _passes_length_filter(name: str, min_length: Optional[int], max_length: Optional[int]) -> bool:
    n = len(name)
    if min_length is not None and n < min_length:
        return False
    if max_length is not None and n > max_length:
        return False
    return True


def _passes_domain_type_filter(semantic_type: str, domain_type: DomainType) -> bool:
    if domain_type == "both":
        return True
    return semantic_type.lower() == domain_type


@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}


@app.get("/meta")
async def meta():
    """Filter option metadata for the frontend (languages, countries, extensions)."""
    return {
        "languages": SUPPORTED_LANGUAGES,
        "countries": sorted(trend_engine._COUNTRY_NAMES.items(), key=lambda kv: kv[1]),
        "extensions": ALL_EXTENSIONS,
    }


@app.get("/trending-niches")
async def trending_niches(limit: int = 6):
    """Return the top trending niches for auto-niche selection."""
    return {"niches": trend_engine.get_trending_niches(limit=max(1, min(limit, 10)))}


_MAX_RETRY_ROUNDS = 5
_ROUND_BATCH_MULTIPLIER = 2  # check 2× requested per round


@app.post("/search", response_model=SearchResponse)
async def search_domains(req: SearchRequest):
    # When niche is empty, pick the top trending niche from the scored baseline.
    niche = req.niche or trend_engine.get_trending_niches(limit=1)[0]["niche"]
    category = trend_engine.category_for_niche(niche)
    extensions = req.extensions or ALL_EXTENSIONS
    candidate_limit = min(max(req.num_results or 20, 5), 100)

    # ── Step 1: Dual trend streams (both run independently) ──────────────────
    # Run in a thread pool since pytrends is sync I/O
    trend_data = await asyncio.get_event_loop().run_in_executor(
        None, fetch_dual_trend_streams, niche
    )
    brandable_keywords: list[str] = trend_data["brandable_keywords"]
    meaningful_keywords: list[str] = trend_data["meaningful_keywords"]
    pytrends_scores: dict[str, int] = trend_data["pytrends_scores"]
    # Combined keywords used for scoring / keyword-match bonuses
    all_keywords = list(dict.fromkeys(meaningful_keywords + brandable_keywords))
    logger.info(
        "Step 1 done — niche='%s' source=%s brandable=%d meaningful=%d",
        niche, trend_data["source"], len(brandable_keywords), len(meaningful_keywords),
    )

    # ── Step 2: Generate a large candidate pool upfront (enough for all retry rounds) ─
    # pool_target drives the generator's internal pool_size = pool_target * 3,
    # giving half = pool_target * 1.5 items per stream. We want at least
    # MAX_ROUNDS * BATCH_MULTIPLIER * candidate_limit total candidates.
    pool_target = max(
        candidate_limit * _MAX_RETRY_ROUNDS * _ROUND_BATCH_MULTIPLIER // 3,
        30,
    )
    candidates = generate_candidates_balanced(
        niche=niche,
        brandable_keywords=brandable_keywords,
        meaningful_keywords=meaningful_keywords,
        target_count=pool_target,
        languages=req.languages,
    )
    logger.info("Step 2 done — generated %d balanced candidates (pool_target=%d)", len(candidates), pool_target)

    # Pre-filter by length and domain type once over the full pool
    filtered_candidates: dict[str, dict] = {}
    for name, provenance in candidates.items():
        if not _passes_length_filter(name, req.min_length, req.max_length):
            continue
        semantic = classify_and_explain(name, provenance)
        if not _passes_domain_type_filter(semantic["type"], req.domain_type):
            continue
        filtered_candidates[name] = provenance

    # Preserve generator priority ordering (niche-matching → shorter → alpha)
    pool_ordered = list(filtered_candidates.keys())
    batch_size = max(candidate_limit * _ROUND_BATCH_MULTIPLIER, 20)
    logger.info("Step 2 filter done — %d candidates pass length/type filter", len(pool_ordered))

    # ── Steps 3-4: Retry loop — check batches until quota filled or pool exhausted ─
    domains: list[DomainResult] = []
    checked_offset = 0
    partial_result_note: Optional[str] = None

    for round_num in range(_MAX_RETRY_ROUNDS):
        if len(domains) >= candidate_limit:
            break

        batch = pool_ordered[checked_offset:checked_offset + batch_size]
        if not batch:
            partial_result_note = (
                f"Exhausted all {len(pool_ordered)} matching candidates after {round_num} round(s) "
                f"— found {len(domains)} of {candidate_limit} requested. "
                "Try widening your character length or extension filters."
            )
            break

        checked_offset += len(batch)
        logger.info(
            "Round %d/%d: RDAP-checking %d names (have %d/%d so far)",
            round_num + 1, _MAX_RETRY_ROUNDS, len(batch), len(domains), candidate_limit,
        )

        # ── Step 3: RDAP availability ──────────────────────────────────────
        availability_records = await check_availability(batch, extensions)
        grouped = group_by_name(availability_records)

        # ── Step 4: 4-dimension scoring + enrichment ───────────────────────
        for name in batch:
            ext_map = grouped.get(name, {})
            registrar_availability: dict[str, Optional[bool]] = {
                e: ext_map.get(e) for e in ALL_EXTENSIONS
            }
            for ext, available in ext_map.items():
                if available is False:
                    continue
                enriched = enrich_domain(
                    name=name,
                    extension=ext,
                    available=available,
                    keywords=all_keywords,
                    provenance=filtered_candidates[name],
                    category=category,
                    trend_location=req.trend_location,
                    pytrends_scores=pytrends_scores,
                    registrar_availability=registrar_availability,
                    brandable_keywords=brandable_keywords,
                    meaningful_keywords=meaningful_keywords,
                )

                if req.cost_min is not None and enriched["registration_cost_usd"] < req.cost_min:
                    continue
                if req.cost_max is not None and enriched["registration_cost_usd"] > req.cost_max:
                    continue
                if req.score_heat_min is not None and enriched["heat_index"] < req.score_heat_min:
                    continue
                if req.score_heat_min is not None and enriched["trend_score"] < req.score_heat_min:
                    continue

                domains.append(DomainResult(**enriched))

    # If we exhausted all retry rounds without filling the quota, surface a note
    if len(domains) < candidate_limit and partial_result_note is None:
        partial_result_note = (
            f"Found {len(domains)} of {candidate_limit} requested domains after "
            f"{_MAX_RETRY_ROUNDS} rounds ({checked_offset} candidates checked). "
            "Try widening your character length or extension filters."
        )

    # Sort by composite: rule-based score weighted with domain_score_total
    domains.sort(key=lambda r: r.score + r.domain_score_total, reverse=True)
    domains = domains[:candidate_limit]
    logger.info("Done — returning %d scored domains (note=%s)", len(domains), bool(partial_result_note))

    return SearchResponse(
        domains=domains,
        niche=niche,
        keyword_seeds=all_keywords[:15],
        trend_source=trend_data["source"],
        brandable_keywords=brandable_keywords,
        meaningful_keywords=meaningful_keywords,
        partial_result_note=partial_result_note,
    )
