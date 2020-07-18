from django.contrib import admin

from .models import Question, Solution

admin.site.register(Question)
admin.site.register(Solution)
