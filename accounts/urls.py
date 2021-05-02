from django.contrib.auth.views import LoginView
from django.urls import path
from accounts import views

urlpatterns = [
    path('login/', LoginView.as_view(template_name='auth/login.html')),
    path('', views.login, name='login'),
    path('done/', views.callback, name='login-done'),
    path('logout/', views.logout, name='logout'),
]
