from django.contrib import admin

from .models import Vendedor


@admin.register(Vendedor)
class VendedorAdmin(admin.ModelAdmin):
	list_display = ('empresa', 'cnpj', 'cidade_sede', 'uf_sede', 'ativo', 'criado_em')
	search_fields = ('empresa', 'cnpj', 'usuario__email')
	list_filter = ('ativo', 'uf_sede')
