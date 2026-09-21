from django.contrib import admin

from .models import Categoria, Produto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
	list_display = ('nome', 'ativa')
	search_fields = ('nome',)
	list_filter = ('ativa',)
	prepopulated_fields = {'slug': ('nome',)}


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
	list_display = ('nome', 'fornecedor', 'categoria', 'preco', 'estoque', 'ativo')
	search_fields = ('nome', 'descricao', 'fornecedor__empresa')
	list_filter = ('ativo', 'categoria', 'fornecedor')
	autocomplete_fields = ('categoria', 'fornecedor')
