from django.contrib import admin

from .models import Perfil


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
	list_display = (
		'usuario',
		'tipo',
		'telefone',
		'cidade',
		'estado',
		'aceite_termos_em',
		'anonimizado_em',
		'criado_em',
	)
	search_fields = ('usuario__username', 'usuario__email', 'usuario__first_name', 'usuario__last_name')
	list_filter = ('estado', 'criado_em', 'anonimizado_em')
	autocomplete_fields = ('usuario',)
	readonly_fields = ('aceite_termos_em', 'anonimizado_em')
