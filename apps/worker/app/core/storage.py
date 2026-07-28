"""
core/storage.py

R2 (Cloudflare) storage helpers -- S3-compatible via boto3.
Migrated from test_r2_upload.py: same mechanism, now parameterized
functions instead of a script with hardcoded test paths.

Two usage patterns:
  - The BROWSER uploads the original source video directly to R2
    using a presigned PUT url (server never touches those bytes).
  - The WORKER uploads FINAL rendered clips directly via boto3 --
    it's trusted server-side code, so no presigned URL is needed
    for this direction.
"""

import boto3

from app.core.config import settings

# load the .env file in the root of the project to get R2 credentials

from dotenv import load_dotenv
load_dotenv()

def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


def generate_presigned_upload_url(key: str, expires_in: int = 3600) -> str:
    """Used by the API to hand the browser a direct-upload URL."""
    client = get_r2_client()
    return client.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": settings.r2_bucket_name, "Key": key},
        ExpiresIn=expires_in,
    )


def generate_presigned_download_url(key: str, expires_in: int = 3600) -> str:
    """Used to hand the client a link to a finished clip."""
    client = get_r2_client()
    return client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": settings.r2_bucket_name, "Key": key},
        ExpiresIn=expires_in,
    )


def download_to_local(key: str, local_path: str) -> str:
    """Worker pulls an already-uploaded source file down for processing."""
    client = get_r2_client()
    client.download_file(settings.r2_bucket_name, key, local_path)
    return local_path


def upload_local_file(local_path: str, key: str) -> str:
    """Worker uploads a finished render (e.g. a captioned clip). Returns the object key."""
    client = get_r2_client()
    client.upload_file(local_path, settings.r2_bucket_name, key)
    return key