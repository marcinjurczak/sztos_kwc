from typing import Dict, Iterable

import minio
from django.conf import settings
from minio import Minio

s3 = Minio(
    settings.S3_HOST,
    access_key=settings.S3_ACCESS_KEY,
    secret_key=settings.S3_SECRET_KEY,
    secure=False
)


def get_object(bucket_name: str, object_name: str) -> str:
    response = None
    try:
        response = s3.get_object(bucket_name, object_name)
        return response.data.decode("utf-8")
    finally:
        if response:
            response.close()
            response.release_conn()


def get_directory(bucket: str, prefix: str) -> Dict[str, str]:
    objects: Iterable[minio.Object] = s3.list_objects(bucket, prefix)
    files = {
        object.object_name[len(prefix):]: get_object(object.bucket_name, object.object_name)
        for object in objects
    }
    return files
