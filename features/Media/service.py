# features/Media/service.py
from google.cloud import storage
from fastapi import HTTPException

BUCKET_NAME = "docquliobucket"
storage_client = storage.Client()

def list_user_docs(user_id: str):
    """
    Return all documents for a specific user from GCS (docs/{user_id}/)
    """
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blobs = bucket.list_blobs(prefix=f"docs/{user_id}/")

        files = []
        for blob in blobs:
            if not blob.name.endswith("/"):  # skip empty "folders"
                files.append({
                    "filename": blob.name.split("/")[-1],
                    "gcs_url": f"https://storage.googleapis.com/{BUCKET_NAME}/{blob.name}"
                })

        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GCS error: {str(e)}")
