from django.urls import path

from . import views

app_name = 'recomendacoes'

urlpatterns = [
    path('', views.painel_recomendacoes, name='painel'),
]
