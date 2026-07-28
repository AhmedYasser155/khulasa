"""
core/jobs.py

Minimal in-memory job store for local testing and early development.

Swap this for a real Supabase `jobs` table once you move past local
testing -- the function signatures here (create_job, update_job,
get_job) are exactly what would become Supabase queries later, so
nothing calling these functions needs to change when you do.

Known limitation (acceptable for now, worth knowing): this dict lives
in the worker process's memory. If the process restarts, all job
history is lost, and this won't work if you ever run more than one
worker process. That's the exact trigger point for migrating to a
real database-backed store.
"""

import time
import uuid

_jobs: dict[str, dict] = {}


def create_job(source: str) -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "job_id": job_id,
        "source": source,
        "status": "queued",
        "created_at": time.time(),
        "clip_urls": [],
        "error": None,
    }
    return job_id


def update_job(job_id: str, **fields):
    if job_id in _jobs:
        _jobs[job_id].update(fields)


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)