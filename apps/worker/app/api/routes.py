"""
api/routes.py

Replaces the original stub. Two endpoints:

  POST /jobs       -- creates a job, kicks off the pipeline in the
                       background, returns a job_id immediately
  GET  /jobs/{id}  -- returns current status and, once done, clip URLs

Uses FastAPI's built-in BackgroundTasks for now -- no Redis/Celery
needed at this volume. Known limitation: jobs are lost if the server
restarts mid-run, and this won't scale across multiple server
instances. That's the trigger point for swapping in a real queue --
nothing in pipeline/orchestrator.py would need to change when you do.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.core import jobs
from app.pipeline.orchestrator import run_pipeline

router = APIRouter()


@router.post("/jobs")
def create_job(payload: dict, background_tasks: BackgroundTasks):
    """
    payload example: {"source": "C:/path/to/video.mp4"}
    or, once R2 upload is wired into the frontend: {"source": "r2://uploads/abc123.mp4"}
    """
    source = payload.get("source")
    if not source:
        raise HTTPException(status_code=400, detail="Missing 'source' in request body")

    job_id = jobs.create_job(source=source)
    background_tasks.add_task(run_pipeline, job_id, source)
    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job