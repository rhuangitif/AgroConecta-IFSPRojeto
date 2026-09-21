from django.conf import settings
from django.db import models


class Perfil(models.Model):
	class Tipo(models.TextChoices):
		AGRICULTOR = 'agricultor', 'Agricultor'
		FORNECEDOR = 'fornecedor', 'Fornecedor'

	usuario = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='perfil',
	)
	tipo = models.CharField(max_length=20, choices=Tipo.choices)
	telefone = models.CharField(max_length=20, blank=True)
	cidade = models.CharField(max_length=100, blank=True)
	estado = models.CharField(max_length=2, blank=True)
	criado_em = models.DateTimeField(auto_now_add=True)
	atualizado_em = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('usuario__first_name', 'usuario__last_name')

	def __str__(self):
		return self.usuario.get_full_name() or self.usuario.username
