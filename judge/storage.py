from django.conf import settings
from minio import Minio

s3 = Minio(
    settings.S3_HOST,
    access_key=settings.S3_ACCESS_KEY,
    secret_key=settings.S3_SECRET_KEY,
    secure=False
)
