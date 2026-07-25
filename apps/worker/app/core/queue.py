"""
Minimal job queue placeholder.

MVP approach: a `jobs` table in Supabase that this worker polls.
Swap this out for Redis/RQ or a managed queue once render jobs
take long enough that polling latency matters.
"""


def enqueue(job_type: str, payload: dict) -> str:
    """Insert a row into the jobs table. Returns job id."""
    raise NotImplementedError("Wire this up to Supabase once schema is created.")


def poll_next_job():
    """Fetch the next pending job for this worker to process."""
    raise NotImplementedError
