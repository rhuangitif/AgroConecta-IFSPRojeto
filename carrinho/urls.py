from django.urls import path

from . import views

app_name = 'carrinho'

urlpatterns = [
    path('', views.ver_carrinho, name='ver'),
    path('adicionar/<int:produto_id>/', views.adicionar, name='adicionar'),
    path('atualizar/<int:item_id>/', views.atualizar, name='atualizar'),
    path('remover/<int:item_id>/', views.remover, name='remover'),
]
