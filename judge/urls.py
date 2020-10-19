from django.urls import path

from . import views

app_name = 'judge'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('courses/', views.CourseListView.as_view(), name='courses'),
    path('course/<int:pk>/problems/', views.ProblemListView.as_view(), name='problems'),
    path('problem/<int:pk>/', views.ProblemDetailView.as_view(), name='detail'),
    path('<int:problem_id>/send/', views.send_solution, name='send'),
]
