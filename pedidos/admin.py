from django.contrib import admin

from .models import HistoricoStatus, Pedido, PedidoFornecedor, PedidoItem


class PedidoItemInline(admin.TabularInline):
	model = PedidoItem
	extra = 0
	autocomplete_fields = ('produto',)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
	list_display = ('id', 'usuario', 'criado_em', 'valor_total', 'status')
	search_fields = ('usuario__username', 'usuario__email')
	list_filter = ('criado_em',)
	autocomplete_fields = ('usuario',)


@admin.register(PedidoFornecedor)
class PedidoFornecedorAdmin(admin.ModelAdmin):
	list_display = ('pedido', 'fornecedor', 'status', 'criado_em', 'atualizado_em')
	list_filter = ('status', 'criado_em')
	search_fields = ('pedido__usuario__username', 'fornecedor__empresa')
	autocomplete_fields = ('pedido', 'fornecedor')
	inlines = (PedidoItemInline,)
	readonly_fields = ('status',)

	def save_model(self, request, obj, form, change):
		obj._autor_status = request.user
		super().save_model(request, obj, form, change)


@admin.register(PedidoItem)
class PedidoItemAdmin(admin.ModelAdmin):
	list_display = ('pedido_fornecedor', 'produto', 'quantidade', 'preco_unitario', 'subtotal')
	search_fields = ('pedido_fornecedor__pedido__usuario__username', 'produto__nome')
	autocomplete_fields = ('pedido_fornecedor', 'produto')


@admin.register(HistoricoStatus)
class HistoricoStatusAdmin(admin.ModelAdmin):
	list_display = (
		'pedido_fornecedor',
		'status_anterior',
		'status_novo',
		'autor',
		'criado_em',
	)
	list_filter = ('status_anterior', 'status_novo', 'criado_em')
	search_fields = ('pedido_fornecedor__pedido__usuario__username', 'autor__username')
	readonly_fields = (
		'pedido_fornecedor',
		'status_anterior',
		'status_novo',
		'autor',
		'criado_em',
	)

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return False

	def has_delete_permission(self, request, obj=None):
		return False
