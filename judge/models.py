from django.db import models


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
    text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published', auto_now_add=True)
    state = models.IntegerField(choices=State.choices, default=State.PENDING)
    valid = models.NullBooleanField()

    def __str__(self):
        return self.text
