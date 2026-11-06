from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from contas.choices import UnidadeFederativa
from .validators import normalizar_cnpj, validar_cnpj


class Vendedor(models.Model):
	usuario = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='vendedor',
	)
	empresa = models.CharField(max_length=150)
	cnpj = models.CharField(max_length=14, unique=True)
	logo = models.ImageField(upload_to='vendedores/', blank=True, null=True)
	endereco = models.CharField(max_length=255, blank=True)
	# These fields describe the company's registered address, not the user's location.
	cidade_sede = models.CharField(max_length=100, blank=True)
	uf_sede = models.CharField(
		max_length=2,
		choices=UnidadeFederativa.choices,
		blank=True,
	)
	descricao = models.TextField(blank=True)
	ativo = models.BooleanField(default=True)
	criado_em = models.DateTimeField(auto_now_add=True)
	atualizado_em = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('empresa',)
		verbose_name = 'Fornecedor'
		verbose_name_plural = 'Fornecedores'

	def clean(self):
		super().clean()
		if not self.cnpj:
			return
		try:
			cnpj = normalizar_cnpj(self.cnpj)
		except ValidationError:
			raise
		self.cnpj = cnpj

		cnpj_anterior = None
		if self.pk:
			cnpj_anterior = type(self).objects.filter(pk=self.pk).values_list(
				'cnpj',
				flat=True,
			).first()
		if cnpj_anterior != cnpj:
			validar_cnpj(cnpj)

	def save(self, *args, **kwargs):
		cnpj = normalizar_cnpj(self.cnpj)
		cnpj_anterior = None
		if self.pk:
			cnpj_anterior = type(self).objects.filter(pk=self.pk).values_list(
				'cnpj',
				flat=True,
			).first()
		if cnpj_anterior != cnpj:
			validar_cnpj(cnpj)
		self.cnpj = cnpj
		super().save(*args, **kwargs)

	def __str__(self):
		return self.empresa
