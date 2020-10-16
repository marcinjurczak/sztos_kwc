from django.urls import path

from . import views

app_name = 'judge'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('courses/', views.CourseListView.as_view(), name='courses'),
    path('courses/add/', views.CourseCreate.as_view(), name='add_course'),
    path('course/<int:pk>/problems/', views.ProblemListView.as_view(), name='problems'),
    path('course/<int:pk>/problem/add/', views.ProblemCreate.as_view(), name='add_problem'),
    path('course/<int:course_pk>/problem/<int:problem_pk>/', views.ProblemDetailView.as_view(), name='detail'),
    path('<int:problem_id>/send/', views.send_solution, name='send'),
]
