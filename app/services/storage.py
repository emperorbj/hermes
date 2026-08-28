import os

import boto3
from dotenv import load_dotenv

load_dotenv()

R2_ENDPOINT_URL = os.environ["R2_ENDPOINT_URL"]
R2_ACCESS_KEY_ID = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
R2_BUCKET_NAME = os.environ["R2_BUCKET_NAME"]

s3_client = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT_URL,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    region_name="auto",
)


def upload_file(key: str, file_bytes: bytes) -> None:
    s3_client.put_object(Bucket=R2_BUCKET_NAME, Key=key, Body=file_bytes)


def download_file(key: str) -> bytes:
    response = s3_client.get_object(Bucket=R2_BUCKET_NAME, Key=key)
    return response["Body"].read()


def delete_file(key: str) -> None:
    s3_client.delete_object(Bucket=R2_BUCKET_NAME, Key=key)
