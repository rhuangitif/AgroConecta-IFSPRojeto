from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from produtos import views as produtos_views
from pedidos import views as pedidos_views
from dashboard import views as dashboard_views


urlpatterns = [
	path('admin/dashboard/', dashboard_views.administrador_dashboard, name='admin_dashboard'),
	path('admin/', admin.site.urls),
	path('', RedirectView.as_view(pattern_name='produtos:catalogo', permanent=False)),
	path('', include('contas.urls')),
	path('produtos/', include('produtos.urls')),
	path('carrinho/', include('carrinho.urls')),
	path('pedidos/', include('pedidos.urls')),
	path('recomendacoes/', include('recomendacoes.urls')),
	path('dashboard/', include('dashboard.urls')),
	path('fornecedor/dashboard/', dashboard_views.fornecedor_dashboard, name='fornecedor_dashboard'),
	path('fornecedor/pedidos/', pedidos_views.pedidos_recebidos, name='fornecedor_pedidos'),
	path('fornecedor/pedidos/<int:pk>/status/', pedidos_views.atualizar_status, name='fornecedor_pedido_status'),
	path('fornecedor/produtos/', produtos_views.meus_produtos, name='fornecedor_meus_produtos'),
	path('fornecedor/produtos/novo/', produtos_views.produto_novo, name='fornecedor_produto_novo'),
	path('fornecedor/produtos/<int:pk>/editar/', produtos_views.produto_editar, name='fornecedor_produto_editar'),
	path('fornecedor/produtos/<int:pk>/excluir/', produtos_views.produto_excluir, name='fornecedor_produto_excluir'),
]

if settings.DEBUG:
	urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
