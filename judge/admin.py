from django.contrib import admin

from .models import Course, Problem, Solution, TestCase, TestRun

admin.site.register(Course)
admin.site.register(Problem)
admin.site.register(Solution)
admin.site.register(TestCase)
admin.site.register(TestRun)
