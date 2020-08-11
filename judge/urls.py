from django.urls import path

from . import views

app_name = 'judge'
urlpatterns = [
    path('', views.ProblemIndexView.as_view(), name='index'),
    path('<int:pk>/', views.ProblemDetailView.as_view(), name='detail'),
    path('<int:problem_id>/send/', views.send_solution, name='send'),
]
