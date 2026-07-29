from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Route = Literal["direct", "retrieve_docs", "web_search"]


class RouterDecision(BaseModel):
    route: Route
    reasoning: str


class RetrievedChunk(BaseModel):
    source: str
    text: str
    score: float


class StageTrace(BaseModel):
    stage: str
    duration_ms: float
    metadata: dict = {}


class PipelineResult(BaseModel):
    query: str
    route: Route
    answer: str
    retrieved: list[RetrievedChunk] = []
    trace: list[StageTrace] = []
