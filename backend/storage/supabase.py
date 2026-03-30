"""Storage layer — Supabase Storage with local filesystem fallback."""

import os
import logging

from config import settings

logger = logging.getLogger(__name__)

BUCKETS = ["papers", "visuals", "audio"]

# Local storage root (fallback when Supabase not configured)
LOCAL_STORAGE_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "local_storage")

_use_supabase = bool(settings.supabase_url and settings.supabase_service_key)


def _get_supabase():
    from deps import get_supabase
    return get_supabase()


def ensure_buckets():
    """Create storage buckets (Supabase) or local directories."""
    if _use_supabase:
        sb = _get_supabase()
        existing = {b.name for b in sb.storage.list_buckets()}
        for bucket in BUCKETS:
            if bucket not in existing:
                public = bucket in ("visuals", "audio")
                sb.storage.create_bucket(bucket, options={"public": public})
        logger.info("Supabase storage buckets ready")
    else:
        for bucket in BUCKETS:
            os.makedirs(os.path.join(LOCAL_STORAGE_ROOT, bucket), exist_ok=True)
        logger.info(f"Local storage ready at {LOCAL_STORAGE_ROOT}")


def upload_file(bucket: str, path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload a file. Returns a URL (Supabase CDN or local file:// path)."""
    if _use_supabase:
        sb = _get_supabase()
        sb.storage.from_(bucket).upload(path, data, file_options={"content-type": content_type})
        return get_public_url(bucket, path)
    else:
        # Local filesystem fallback
        full_path = os.path.join(LOCAL_STORAGE_ROOT, bucket, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(data)
        # Return a URL the backend can serve
        return f"/api/storage/{bucket}/{path}"


def get_public_url(bucket: str, path: str) -> str:
    """Get public URL for a stored file."""
    if _use_supabase:
        sb = _get_supabase()
        return sb.storage.from_(bucket).get_public_url(path)
    else:
        return f"/api/storage/{bucket}/{path}"


def download_file(bucket: str, path: str) -> bytes:
    """Download a file from storage."""
    if _use_supabase:
        sb = _get_supabase()
        return sb.storage.from_(bucket).download(path)
    else:
        full_path = os.path.join(LOCAL_STORAGE_ROOT, bucket, path)
        with open(full_path, "rb") as f:
            return f.read()
