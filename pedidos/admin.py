from django.contrib import admin

from .models import Pedido, PedidoFornecedor, PedidoItem


class PedidoItemInline(admin.TabularInline):
	model = PedidoItem
	extra = 0
	autocomplete_fields = ('produto',)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
	list_display = ('id', 'usuario', 'data', 'valor_total', 'status')
	search_fields = ('usuario__username', 'usuario__email')
	list_filter = ('data',)
	autocomplete_fields = ('usuario',)


@admin.register(PedidoFornecedor)
class PedidoFornecedorAdmin(admin.ModelAdmin):
	list_display = ('pedido', 'fornecedor', 'status', 'criado_em', 'atualizado_em')
	list_filter = ('status', 'criado_em')
	search_fields = ('pedido__usuario__username', 'fornecedor__empresa')
	autocomplete_fields = ('pedido', 'fornecedor')
	inlines = (PedidoItemInline,)


@admin.register(PedidoItem)
class PedidoItemAdmin(admin.ModelAdmin):
	list_display = ('pedido_fornecedor', 'produto', 'quantidade', 'preco_unitario', 'subtotal')
	search_fields = ('pedido_fornecedor__pedido__usuario__username', 'produto__nome')
	autocomplete_fields = ('pedido_fornecedor', 'produto')
