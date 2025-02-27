from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class OpenIdUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_username = models.CharField(max_length=150)