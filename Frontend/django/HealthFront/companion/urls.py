from django.urls import path
from .views import welcome, auth_view, dashboard

urlpatterns = [
    path('', welcome, name='welcome'),       # Starting page - welcome page
    path('auth/', auth_view, name='auth'),   # Login page
    path('dashboard/', dashboard, name='dashboard'),  # Dashboard
]