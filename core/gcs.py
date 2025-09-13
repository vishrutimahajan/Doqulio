from google.cloud import storage
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

if not key_path or not os.path.exists(key_path):
    raise FileNotFoundError(
        f"Google credentials file not found. Expected at {key_path}"
    )

client = storage.Client.from_service_account_json(key_path)


def upload_file(local_path: str,BUCKET_NAME: str, destination_blob_name: str):
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_path)
    return f"gs://{BUCKET_NAME}/{destination_blob_name}"

def download_file(blob_name: str, bucket_name: str, local_path: str):
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(local_path)
    return local_path
