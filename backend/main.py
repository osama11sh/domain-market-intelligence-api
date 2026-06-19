"""Domain Market Intelligence Platform - FastAPI backend."""

import logging
from typing import Literal, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from trends import fetch_trend_data
from generator import generate_candidates
from availability import check_availability, group_by_name, ALL_EXTENSIONS
from scoring import enrich_domain
from semantics import SUPPORTED_LANGUAGES, classify_and_explain
import trend_engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Domain Market Intelligence", version="2.0.0")

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
    available: bool
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


class SearchResponse(BaseModel):
    domains: list[DomainResult]
    niche: str
    keyword_seeds: list[str]
    trend_source: str


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
    return {"status": "ok", "version": "2.0.0"}


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
    """Return the top trending niches for auto-niche selection.

    Scores are computed by the independent baseline (no external call needed).
    The frontend can call this when the niche field is empty to show suggestions.
    """
    return {"niches": trend_engine.get_trending_niches(limit=max(1, min(limit, 10)))}


@app.post("/search", response_model=SearchResponse)
async def search_domains(req: SearchRequest):
    # When niche is empty, pick the top trending niche from the scored baseline.
    niche = req.niche or trend_engine.get_trending_niches(limit=1)[0]["niche"]
    category = trend_engine.category_for_niche(niche)
    extensions = req.extensions or ALL_EXTENSIONS
    candidate_limit = min(max(req.num_results or 20, 5), 100)

    # Step 1: Trend keywords (pytrends optional - independent trend_engine baseline always works)
    trend_data = fetch_trend_data(niche)
    keywords = trend_data["keywords"]
    pytrends_scores = trend_data["pytrends_scores"]
    logger.info("Keywords for '%s' (source=%s): %s", niche, trend_data["source"], keywords)

    # Step 2: Generate candidates (with provenance for semantics + multi-language support)
    candidates = generate_candidates(niche, keywords, req.languages)
    logger.info("Generated %d candidates", len(candidates))

    # Pre-filter by length and domain type before spending RDAP calls
    filtered_candidates: dict[str, dict] = {}
    for name, provenance in candidates.items():
        if not _passes_length_filter(name, req.min_length, req.max_length):
            continue
        semantic = classify_and_explain(name, provenance)
        if not _passes_domain_type_filter(semantic["type"], req.domain_type):
            continue
        filtered_candidates[name] = provenance

    names_to_check = sorted(filtered_candidates.keys())[:candidate_limit * 3]

    # Step 3: RDAP availability across the requested extensions only
    availability_records = await check_availability(names_to_check, extensions)
    grouped = group_by_name(availability_records)

    # Step 4: Score + enrich, keep rows where the *requested* extension is available
    domains: list[DomainResult] = []
    for name in names_to_check:
        ext_map = grouped.get(name, {})
        registrar_availability: dict[str, Optional[bool]] = {
            e: ext_map.get(e) for e in ALL_EXTENSIONS
        }
        for ext, available in ext_map.items():
            if not available:
                continue
            enriched = enrich_domain(
                name=name,
                extension=ext,
                keywords=keywords,
                provenance=filtered_candidates[name],
                category=category,
                trend_location=req.trend_location,
                pytrends_scores=pytrends_scores,
                registrar_availability=registrar_availability,
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

    domains.sort(key=lambda r: r.score, reverse=True)
    domains = domains[:candidate_limit]

    return SearchResponse(
        domains=domains,
        niche=niche,
        keyword_seeds=keywords,
        trend_source=trend_data["source"],
    )
