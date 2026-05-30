"""Local FastAPI backend for Narrative Alpha — replaces Modal orchestration."""

import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from narrative.pipeline import _run_pipeline, _run_startup_init
from narrative.contracts import LLMConfig
from narrative.llm_client import load_llm_config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    os.makedirs(_reports_dir(), exist_ok=True)
    _run_startup_init()
    yield


app = FastAPI(title="Narrative Alpha API", lifespan=lifespan)


def _narrative_root() -> str:
    return os.environ.get("NARRATIVE_ALPHA_ROOT", os.path.expanduser("~/.narrative_alpha"))


def _config_path() -> str:
    return os.path.join(_narrative_root(), "llm_config.json")


def _reports_dir() -> str:
    return os.path.join(_narrative_root(), "data", "reports")


class PipelinePayload(BaseModel):
    keyword: str
    vertical: str = "TECHNOLOGY"


@app.post("/api/pipeline")
def execute_pipeline(payload: PipelinePayload) -> dict:
    api_key = os.environ.get("BRIGHTDATA_API_KEY", "")
    unlocker_zone = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE", "")

    if not api_key or not unlocker_zone:
        raise HTTPException(
            status_code=503,
            detail="BRIGHTDATA_API_KEY and BRIGHTDATA_UNLOCKER_ZONE environment variables must be set"
        )

    db_path = os.path.join(_narrative_root(), "outlet_reputation.db")

    try:
        report = _run_pipeline(payload.keyword, payload.vertical, api_key, unlocker_zone, db_path)
    except Exception:
        logger.exception("Pipeline execution failed")
        return JSONResponse(
            status_code=500,
            content={"error": "Pipeline execution failed. Check server logs for details."}
        )

    cluster_id = report.get("event_meta", {}).get("cluster_id", "unknown")
    os.makedirs(_reports_dir(), exist_ok=True)
    report_path = os.path.join(_reports_dir(), f"{cluster_id}.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return report


@app.get("/api/reports")
def list_reports() -> list[dict]:
    reports_dir = _reports_dir()
    if not os.path.isdir(reports_dir):
        return []

    summaries = []
    for fname in sorted(os.listdir(reports_dir), reverse=True):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(reports_dir, fname)) as f:
                report = json.load(f)
            meta = report.get("event_meta", {})
            summaries.append({
                "cluster_id": meta.get("cluster_id", ""),
                "search_query": meta.get("search_query", ""),
                "industry_vertical": meta.get("industry_vertical", ""),
                "timestamp_utc": meta.get("timestamp_utc", ""),
                "corpus_count": meta.get("corpus_count", 0),
                "corpus_capped": meta.get("corpus_capped", False),
            })
        except (json.JSONDecodeError, OSError):
            continue
    return summaries


@app.get("/api/reports/{cluster_id}")
def get_report(cluster_id: str) -> dict:
    if "/" in cluster_id or ".." in cluster_id or "\\" in cluster_id:
        raise HTTPException(status_code=400, detail="Invalid cluster_id")
    report_path = os.path.join(_reports_dir(), f"{cluster_id}.json")
    if not os.path.isfile(report_path):
        raise HTTPException(status_code=404, detail={"error": f"Report {cluster_id} not found"})
    with open(report_path) as f:
        return json.load(f)


@app.get("/api/config")
def get_config() -> dict:
    return load_llm_config()


@app.post("/api/config")
def update_config(payload: LLMConfig) -> dict:
    config = payload.model_dump()
    with open(_config_path(), "w") as f:
        json.dump(config, f, indent=2)
    return {"status": "ok", "config": config}
