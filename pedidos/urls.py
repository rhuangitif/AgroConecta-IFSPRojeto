from django.urls import path

from . import views

app_name = 'pedidos'

urlpatterns = [
    path('', views.meus_pedidos, name='lista'),
    path('<int:pk>/', views.pedido_detalhe, name='detalhe'),
    path('finalizar/', views.finalizar_pedido, name='finalizar'),
    path('fornecedor/', views.pedidos_recebidos, name='recebidos'),
    path('fornecedor/<int:pk>/status/', views.atualizar_status, name='atualizar_status'),
]
