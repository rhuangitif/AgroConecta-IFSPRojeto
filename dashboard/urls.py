from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('agricultor/', views.agricultor_dashboard, name='agricultor'),
    path('fornecedor/', views.fornecedor_dashboard, name='fornecedor'),
    path('administrador/', views.administrador_dashboard, name='administrador'),
]
