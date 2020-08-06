from typing import List
from uuid import uuid4

import minio
from django.conf import settings
from django.core.files import File
from django.db import models

from judge.storage import s3


class Problem(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=1000)
    pub_date = models.DateTimeField('date published')

    def __str__(self):
        return self.title


class Solution(models.Model):
    class State(models.IntegerChoices):
        PENDING = 0
        IN_PROGRESS = 1
        VALIDATED = 2

    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    pub_date = models.DateTimeField('date published', auto_now_add=True)
    state = models.IntegerField(choices=State.choices, default=State.PENDING)
    valid = models.NullBooleanField()
    uuid = models.UUIDField(default=uuid4, editable=False)

    def save_file(self, file: File) -> None:
        s3.put_object(settings.S3_SUBMISSION_BUCKET, f"{self.uuid}/files/{file.name}", file, file.size)

    def get_source(self) -> str:
        files: List[minio.Object] = list(s3.list_objects(settings.S3_SUBMISSION_BUCKET, f"{self.uuid}/files/"))
        response = None
        try:
            response = s3.get_object(files[0].bucket_name, files[0].object_name)
            return response.data.decode("utf-8")
        finally:
            if response:
                response.close()
                response.release_conn()

    def __str__(self):
        return f"Solution({self.id})"
