from fastapi import APIRouter

router = APIRouter()


@router.post("/jobs")
def submit_job(payload: dict):
    """
    MVP: accepts a YouTube URL or an R2 object key, enqueues a job.
    Replace body with a proper Pydantic model once the schema settles.
    """
    return {"status": "queued", "received": payload}


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    return {"job_id": job_id, "status": "pending"}
