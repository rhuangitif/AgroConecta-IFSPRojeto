from django.contrib import admin

from .models import Categoria, Produto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
	list_display = ('nome', 'ativa')
	search_fields = ('nome',)
	list_filter = ('ativa',)
	readonly_fields = ('slug',)


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
	actions = ('desativar_produtos',)
	list_display = ('nome', 'fornecedor', 'categoria', 'preco', 'estoque', 'ativo')
	search_fields = ('nome', 'descricao', 'fornecedor__empresa')
	list_filter = ('ativo', 'categoria', 'fornecedor')
	autocomplete_fields = ('categoria', 'fornecedor')

	@admin.action(description='Desativar produtos selecionados')
	def desativar_produtos(self, request, queryset):
		queryset.update(ativo=False)

	def delete_model(self, request, obj):
		obj.delete()

	def get_actions(self, request):
		actions = super().get_actions(request)
		actions.pop('delete_selected', None)
		return actions
