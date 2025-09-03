from google.cloud import storage
import os

key_path = "C:/Users/Vishruti/.credentials/gcloudkey.json"
client = storage.Client.from_service_account_json(key_path)

def upload_file(local_path: str, bucket_name: str, destination_blob_name: str):
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_path)
    return f"gs://{bucket_name}/{destination_blob_name}"

def download_file(blob_name: str, bucket_name: str, local_path: str = None):
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    if not local_path:
        local_path = os.path.basename(blob_name)
    blob.download_to_filename(local_path)
    return local_path
    