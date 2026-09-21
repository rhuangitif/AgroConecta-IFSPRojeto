from django.contrib import admin

from .models import Pedido, PedidoItem


class PedidoItemInline(admin.TabularInline):
	model = PedidoItem
	extra = 0
	autocomplete_fields = ('produto',)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
	list_display = ('id', 'usuario', 'data', 'valor_total', 'status')
	search_fields = ('usuario__username', 'usuario__email')
	list_filter = ('status', 'data')
	autocomplete_fields = ('usuario',)
	inlines = (PedidoItemInline,)


@admin.register(PedidoItem)
class PedidoItemAdmin(admin.ModelAdmin):
	list_display = ('pedido', 'produto', 'quantidade', 'preco_unitario', 'subtotal')
	search_fields = ('pedido__usuario__username', 'produto__nome')
	autocomplete_fields = ('pedido', 'produto')
