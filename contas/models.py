from django.conf import settings
from django.db import models

from .choices import UnidadeFederativa


class Perfil(models.Model):
	class Tipo(models.TextChoices):
		AGRICULTOR = 'agricultor', 'Agricultor'
		FORNECEDOR = 'fornecedor', 'Fornecedor'

	usuario = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='perfil',
	)
	telefone = models.CharField(max_length=20, blank=True)
	cidade = models.CharField(max_length=100, blank=True)
	estado = models.CharField(
		max_length=2,
		choices=UnidadeFederativa.choices,
		blank=True,
	)
	criado_em = models.DateTimeField(auto_now_add=True)
	atualizado_em = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('usuario__first_name', 'usuario__last_name')

	@property
	def tipo(self):
		if hasattr(self.usuario, 'vendedor'):
			return self.Tipo.FORNECEDOR
		return self.Tipo.AGRICULTOR

	def get_tipo_display(self):
		return self.tipo.label

	def __str__(self):
		return self.usuario.get_full_name() or self.usuario.username
