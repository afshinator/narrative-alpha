"""Local FastAPI backend for Narrative Alpha — replaces Modal orchestration."""

import asyncio
import concurrent.futures
import json
import logging
import os
import queue
import time
from typing import Optional
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from narrative.pipeline import _run_pipeline, _run_startup_init
from narrative.contracts import LLMConfig
from narrative.llm_client import load_llm_config, call_llm, get_embedding

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


def _run_pipeline_with_timeout(
    keyword: str, vertical: str, api_key: str, unlocker_zone: str, serp_zone: str, db_path: str,
    timeout: int = 1200,
) -> dict:
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        _run_pipeline, keyword, vertical, api_key, unlocker_zone, serp_zone, db_path
    )
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        executor.shutdown(wait=False)
        raise TimeoutError(f"Pipeline timed out after {timeout}s")


@app.post("/api/pipeline")
def execute_pipeline(payload: PipelinePayload) -> dict:
    api_key = os.environ.get("BRIGHTDATA_API_KEY", "")
    unlocker_zone = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE", "")
    serp_zone = os.environ.get("BRIGHTDATA_SERP_ZONE", "")

    if not api_key or not unlocker_zone or not serp_zone:
        raise HTTPException(
            status_code=503,
            detail="BRIGHTDATA_API_KEY, BRIGHTDATA_SERP_ZONE, and BRIGHTDATA_UNLOCKER_ZONE must be set"
        )

    db_path = os.path.join(_narrative_root(), "outlet_reputation.db")
    timeout = int(os.environ.get("NARRATIVE_PIPELINE_TIMEOUT", "1200"))

    try:
        report = _run_pipeline_with_timeout(
            payload.keyword, payload.vertical, api_key, unlocker_zone, serp_zone, db_path,
            timeout=timeout,
        )
    except TimeoutError as e:
        logger.error("Pipeline timed out")
        return JSONResponse(status_code=504, content={"error": "Pipeline execution timed out", "detail": str(e)})
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


@app.get("/api/pipeline/stream")
async def stream_pipeline(keyword: str, vertical: str = "TECHNOLOGY"):
    api_key = os.environ.get("BRIGHTDATA_API_KEY", "")
    unlocker_zone = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE", "")
    serp_zone = os.environ.get("BRIGHTDATA_SERP_ZONE", "")

    if not api_key or not unlocker_zone or not serp_zone:
        async def _error_stream():
            yield f"data: {json.dumps({'step': 'error', 'message': 'Server misconfigured', 'detail': 'BRIGHTDATA_API_KEY, BRIGHTDATA_SERP_ZONE, and BRIGHTDATA_UNLOCKER_ZONE must be set'})}\n\n"
        return StreamingResponse(_error_stream(), media_type="text/event-stream")

    progress_q: queue.SimpleQueue = queue.SimpleQueue()

    def _progress_cb(step: str, message: str, detail: Optional[dict] = None) -> None:
        progress_q.put((step, message, detail))

    db_path = os.path.join(_narrative_root(), "outlet_reputation.db")

    async def event_stream():
        yield ": ping\n\n"  # flush headers through proxy immediately

        loop = asyncio.get_running_loop()
        pipeline_future = loop.run_in_executor(
            None,
            lambda: _run_pipeline(
                keyword, vertical, api_key, unlocker_zone, serp_zone, db_path,
                progress_cb=_progress_cb,
            ),
        )

        done = False
        keepalive_interval = 30.0
        last_event_time = time.time()
        while not done:
            while True:
                try:
                    received = progress_q.get_nowait()
                    step, message = received[0], received[1]
                    detail = received[2] if len(received) > 2 else None
                    payload: dict = {'step': step, 'message': message}
                    if detail is not None:
                        payload['detail'] = detail
                    yield f"data: {json.dumps(payload)}\n\n"
                    last_event_time = time.time()
                except queue.Empty:
                    break
            if pipeline_future.done():
                done = True
            else:
                await asyncio.sleep(0.5)
                now = time.time()
                if now - last_event_time > keepalive_interval:
                    yield ": keepalive\n\n"
                    last_event_time = now

        # drain any events queued in the final tick
        while True:
            try:
                received = progress_q.get_nowait()
                step, message = received[0], received[1]
                detail = received[2] if len(received) > 2 else None
                payload: dict = {'step': step, 'message': message}
                if detail is not None:
                    payload['detail'] = detail
                yield f"data: {json.dumps(payload)}\n\n"
            except queue.Empty:
                break

        exc = pipeline_future.exception()
        if exc:
            logger.exception("Pipeline stream failed", exc_info=exc)
            yield f"data: {json.dumps({'step': 'error', 'message': 'Pipeline failed', 'detail': str(exc)})}\n\n"
            return

        report = pipeline_future.result()
        cluster_id = report.get("event_meta", {}).get("cluster_id", "unknown")
        os.makedirs(_reports_dir(), exist_ok=True)
        with open(os.path.join(_reports_dir(), f"{cluster_id}.json"), "w") as f:
            json.dump(report, f, indent=2)

        yield f"data: {json.dumps({'step': 'complete', 'message': 'Report ready', 'cluster_id': cluster_id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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


_REQUIRED_ENV_VARS = [
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "BRIGHTDATA_API_KEY",
    "BRIGHTDATA_SERP_ZONE",
    "BRIGHTDATA_UNLOCKER_ZONE",
]


def _check_env() -> dict:
    present_list = []
    missing_list = []
    for var in _REQUIRED_ENV_VARS:
        if os.environ.get(var):
            present_list.append(var)
        else:
            missing_list.append(var)
    status = "ok" if not missing_list else "degraded"
    detail = "All required vars set" if not missing_list else f"Missing: {', '.join(missing_list)}"
    return {"status": status, "detail": detail, "present": present_list, "missing": missing_list}


@app.get("/api/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/api/health/env")
def health_env() -> dict:
    return _check_env()


PROBE_PROMPT = 'Respond with JSON: {"status":"ok"}'


@app.get("/api/health/deep")
def health_deep() -> dict:
    checks = {}
    llm_config = load_llm_config()

    try:
        LLMConfig(**llm_config)
        checks["config"] = {"status": "ok"}
    except Exception as e:
        checks["config"] = {"status": "error", "detail": str(e)}

    checks["env_vars"] = _check_env()

    flash_cfg = llm_config.get("call_1_entity_normalization", {})
    if flash_cfg.get("provider"):
        start = time.time()
        messages = [{"role": "user", "content": PROBE_PROMPT}]
        try:
            raw = call_llm(flash_cfg, messages, json_mode=True, retries=0)
            json.loads(raw)
            latency = round((time.time() - start) * 1000)
            checks["deepseek_flash"] = {"status": "ok", "latency_ms": latency, "model": flash_cfg.get("model", "")}
        except BaseException as e:
            latency = round((time.time() - start) * 1000)
            detail = str(e) if isinstance(e, Exception) else "Non-Exception raised"
            checks["deepseek_flash"] = {"status": "error", "latency_ms": latency, "detail": detail, "model": flash_cfg.get("model", "")}

    pro_cfg = llm_config.get("call_3_graph_extraction", {})
    if pro_cfg.get("provider"):
        start = time.time()
        messages = [{"role": "user", "content": PROBE_PROMPT}]
        try:
            raw = call_llm(pro_cfg, messages, json_mode=True, retries=0)
            json.loads(raw)
            latency = round((time.time() - start) * 1000)
            checks["deepseek_pro_thinking"] = {"status": "ok", "latency_ms": latency, "model": pro_cfg.get("model", "")}
        except BaseException as e:
            latency = round((time.time() - start) * 1000)
            detail = str(e) if isinstance(e, Exception) else "Non-Exception raised"
            checks["deepseek_pro_thinking"] = {"status": "error", "latency_ms": latency, "detail": detail, "model": pro_cfg.get("model", "")}

    start = time.time()
    try:
        get_embedding("health check", retries=0)
        latency = round((time.time() - start) * 1000)
        checks["openai_embedding"] = {"status": "ok", "latency_ms": latency}
    except BaseException as e:
        latency = round((time.time() - start) * 1000)
        detail = str(e) if isinstance(e, Exception) else "Non-Exception raised"
        checks["openai_embedding"] = {"status": "error", "latency_ms": latency, "detail": detail}

    total = sum(
        c.get("latency_ms", 0) for c in checks.values()
        if isinstance(c, dict) and "latency_ms" in c
    )
    overall = "ok" if all(
        c.get("status") == "ok" for c in checks.values() if isinstance(c, dict)
    ) else "degraded"

    return {"status": overall, "checks": checks, "total_latency_ms": total}


@app.get("/api/config")
def get_config() -> dict:
    return load_llm_config()


@app.post("/api/config")
def update_config(payload: LLMConfig) -> dict:
    config = payload.model_dump()
    with open(_config_path(), "w") as f:
        json.dump(config, f, indent=2)
    return {"status": "ok", "config": config}
