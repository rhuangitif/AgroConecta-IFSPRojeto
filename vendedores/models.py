from django.conf import settings
from django.db import models


class Vendedor(models.Model):
	usuario = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='vendedor',
	)
	empresa = models.CharField(max_length=150)
	cnpj = models.CharField(max_length=18, unique=True)
	email = models.EmailField(blank=True)
	telefone = models.CharField(max_length=20, blank=True)
	logo = models.ImageField(upload_to='vendedores/', blank=True, null=True)
	endereco = models.CharField(max_length=255, blank=True)
	cidade = models.CharField(max_length=100, blank=True)
	estado = models.CharField(max_length=2, blank=True)
	descricao = models.TextField(blank=True)
	ativo = models.BooleanField(default=True)
	data_cadastro = models.DateTimeField(auto_now_add=True)
	data_atualizacao = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('empresa',)
		verbose_name = 'Fornecedor'
		verbose_name_plural = 'Fornecedores'

	def __str__(self):
		return self.empresa
