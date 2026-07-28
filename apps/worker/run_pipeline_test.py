"""
run_pipeline_test.py

Place this at apps/worker/ (same level as the `app/` folder).

Calls the orchestrator DIRECTLY -- no FastAPI server, no HTTP calls.
This is the fastest way to verify the whole pipeline works end to end
before adding the API layer on top. Run this first; only move on to
actually starting the server (uvicorn app.main:app) once this passes.

Usage:
    python run_pipeline_test.py
"""

from dotenv import load_dotenv
load_dotenv()

from app.core import jobs
from app.pipeline.orchestrator import run_pipeline

# Point this at a real, short test video (reuse one from your earlier
# standalone testing -- 20-60 seconds is plenty for this smoke test).
SOURCE_VIDEO_PATH = r"C:\Users\aayasser\Desktop\PLAYGROUND\zatoona\playground\tests\media\sample_5min.mp4"


def main():
    job_id = jobs.create_job(source=SOURCE_VIDEO_PATH)
    print(f"Created job: {job_id}")

    run_pipeline(job_id, SOURCE_VIDEO_PATH)  # runs synchronously, in this process

    job = jobs.get_job(job_id)
    print("\n" + "=" * 60)
    print(f"Final status: {job['status']}")
    if job["status"] == "done":
        print(f"\n{len(job['clip_urls'])} clip(s) produced:")
        for clip in job["clip_urls"]:
            print(f"  - {clip['title']} (score {clip['hook_score']})")
            print(f"    {clip['start']}s - {clip['end']}s")
            print(f"    {clip['url']}\n")
    else:
        print(f"Error: {job.get('error')}")
    print("=" * 60)


if __name__ == "__main__":
    main()