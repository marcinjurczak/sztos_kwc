import datetime

from django.db import models
from django.utils import timezone


class Question(models.Model):
    question_title = models.CharField(max_length=100)
    question_description = models.CharField(max_length=1000)
    pub_date = models.DateTimeField('date published')

    def __str__(self):
        return self.question_title

    def was_published_recently(self):
        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)


class Solution(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    solution_text = models.CharField(max_length=200)

    def __str__(self):
        return self.solution_text
