from django.urls import path

from . import views

app_name = 'produtos'

urlpatterns = [
    path('', views.catalogo, name='catalogo'),
    path('mais-vendidos/', views.mais_vendidos, name='mais_vendidos'),
    path('<int:pk>/', views.produto_detalhe, name='detalhe'),
    path('fornecedor/meus-produtos/', views.meus_produtos, name='meus_produtos'),
    path('fornecedor/novo/', views.produto_novo, name='novo'),
    path('fornecedor/<int:pk>/editar/', views.produto_editar, name='editar'),
    path('fornecedor/<int:pk>/excluir/', views.produto_excluir, name='excluir'),
]
