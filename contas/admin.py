from django.contrib import admin

from .models import Perfil


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
	list_display = ('usuario', 'tipo', 'telefone', 'cidade', 'estado', 'criado_em')
	search_fields = ('usuario__username', 'usuario__email', 'usuario__first_name', 'usuario__last_name')
	list_filter = ('tipo', 'estado', 'criado_em')
	autocomplete_fields = ('usuario',)
