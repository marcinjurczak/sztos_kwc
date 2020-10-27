from typing import Dict, Optional
from uuid import uuid4

from django.conf import settings
from django.core.files import File
from django.core.validators import MinValueValidator
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum, Q, Subquery, Max

from judge.storage import s3, get_directory


class Course(models.Model):
    name = models.CharField(max_length=100)
    assigned_users = models.ManyToManyField(User)

    def __str__(self):
        return self.name


class Problem(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    pub_date = models.DateTimeField('date published', auto_now_add=True)

    def __str__(self):
        return self.title

    def get_grades(self) -> Dict[User, Optional[float]]:
        newest = Subquery(self.solution_set.values("user__pk").annotate(Max("pk")).values("pk__max"))
        solutions = Solution.objects.filter(pk__in=newest).order_by("user__pk")

        return {
            solution.user: solution.get_grade() for solution in solutions
        }

    class Meta:
        permissions = (
            ("view_grades", "Can view grades"),
        )


class TestCase(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="test_cases")
    input = models.TextField(blank=True)
    expected_output = models.TextField()
    points = models.FloatField(default=1, validators=(MinValueValidator(0),))
    memory_limit = models.IntegerField(null=True, blank=True, default=50 * 1024 * 1024)
    time_limit = models.FloatField(validators=(MinValueValidator(0),))


class Solution(models.Model):
    class State(models.IntegerChoices):
        COMPILATION_PENDING = 0
        COMPILATION_IN_PROGRESS = 1
        COMPILATION_SUCCESSFUL = 2
        COMPILATION_FAILED = 3

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="solutions", default=None)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    pub_date = models.DateTimeField('date published', auto_now_add=True)
    state = models.IntegerField(choices=State.choices, default=State.COMPILATION_PENDING)
    uuid = models.UUIDField(default=uuid4, editable=False)

    def save_file(self, file: File) -> None:
        s3.put_object(settings.S3_SUBMISSION_BUCKET, f"{self.uuid}/files/{file.name}", file, file.size)

    def get_sources(self) -> Dict[str, str]:
        return get_directory(settings.S3_SUBMISSION_BUCKET, f"{self.uuid}/files/")

    def get_grade(self) -> Optional[float]:
        if self.test_runs.count() == 0:
            return None

        aggregated = self.test_runs.all().aggregate(
            max_points=Sum("test_case__points"),
            points=Sum("test_case__points", filter=Q(state=TestRun.State.VALID)),
        )

        if aggregated["max_points"] == 0:
            return None

        if aggregated["points"] is None:
            return 0

        return aggregated["points"] / aggregated["max_points"]

    def __str__(self):
        return f"Solution({self.id})"


class TestRun(models.Model):
    class State(models.IntegerChoices):
        VALID = 0
        CRASHED = 1
        INVALID = 2
        TIMED_OUT = 3
        PENDING = 4

    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    solution = models.ForeignKey(Solution, on_delete=models.DO_NOTHING, related_name="test_runs")
    stdout = models.TextField(null=True)
    stderr = models.TextField(null=True)
    return_code = models.IntegerField(null=True)
    state = models.IntegerField(choices=State.choices, default=State.PENDING)
    time = models.FloatField(null=True)
