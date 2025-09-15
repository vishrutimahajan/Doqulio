from fastapi import APIRouter, HTTPException
from google.cloud import storage

router = APIRouter(prefix="/docs", tags=["Media"])  # changed prefix for clarity

BUCKET_NAME = "docquliobucket"
storage_client = storage.Client()

@router.get("/{user_id}")
async def list_user_docs(user_id: str):
    """
    List all docs for a given user_id stored in GCS under docs/{user_id}/
    """
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blobs = bucket.list_blobs(prefix=f"docs/{user_id}/")

        files = []
        for blob in blobs:
            # Avoid returning empty 'folder' placeholder
            if not blob.name.endswith("/"):
                files.append({
                    "filename": blob.name.split("/")[-1],
                    "gcs_url": f"https://storage.googleapis.com/{BUCKET_NAME}/{blob.name}"
                })

        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
