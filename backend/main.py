"""Domain Market Intelligence Platform - FastAPI backend."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from trends import fetch_trend_keywords
from generator import generate_candidates
from availability import check_availability
from scoring import score_domain_breakdown, registration_cost_usd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Domain Market Intelligence", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    niche: str

    @field_validator("niche")
    @classmethod
    def niche_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("niche must not be empty")
        if len(v) > 80:
            raise ValueError("niche too long (max 80 chars)")
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


class SearchResponse(BaseModel):
    domains: list[DomainResult]
    niche: str
    keyword_seeds: list[str]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
async def search_domains(req: SearchRequest):
    niche = req.niche

    # Step 1: Trend keywords
    keywords = fetch_trend_keywords(niche)
    logging.getLogger(__name__).info("Keywords for '%s': %s", niche, keywords)

    # Step 2: Generate candidates
    candidates = generate_candidates(niche, keywords)
    logging.getLogger(__name__).info("Generated %d candidates", len(candidates))

    # Step 3: RDAP availability (limit to first 60 names to keep response times sane)
    candidates_to_check = candidates[:60]
    availability_records = await check_availability(candidates_to_check)

    # Step 4: Score and filter to available only
    domains: list[DomainResult] = []
    for rec in availability_records:
        if not rec["available"]:
            continue
        name = rec["name"]
        ext = rec["extension"]
        result = score_domain_breakdown(name, ext, keywords)
        bd = result["breakdown"]
        domains.append(DomainResult(
            name=name,
            extension=ext,
            available=True,
            score=result["total"],
            length=len(name),
            registration_cost_usd=registration_cost_usd(ext),
            score_breakdown=ScoreBreakdown(
                length=bd["length"],
                pronounceability=bd["pronounceability"],
                keyword_match=bd["keyword_match"],
                spelling=bd["spelling"],
                extension=bd["extension"],
            ),
        ))

    # Sort by score descending
    domains.sort(key=lambda r: r.score, reverse=True)

    return SearchResponse(domains=domains, niche=niche, keyword_seeds=keywords)
