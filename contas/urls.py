from django.urls import path

from . import views

app_name = 'contas'

urlpatterns = [
    path('termos/', views.termos_uso, name='termos'),
    path('privacidade/', views.politica_privacidade, name='privacidade'),
    path('cadastro/', views.cadastro, name='cadastro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('perfil/', views.perfil, name='perfil'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('perfil/anonimizar/', views.anonimizar_perfil, name='anonimizar'),
]
