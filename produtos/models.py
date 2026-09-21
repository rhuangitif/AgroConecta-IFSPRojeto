from django.core.validators import MinValueValidator
from django.db import models

from vendedores.models import Vendedor


class Categoria(models.Model):
	nome = models.CharField(max_length=80, unique=True)
	descricao = models.TextField(blank=True)
	slug = models.SlugField(max_length=90, unique=True, blank=True, null=True)
	ativa = models.BooleanField(default=True)

	class Meta:
		ordering = ('nome',)
		verbose_name = 'Categoria'
		verbose_name_plural = 'Categorias'

	def __str__(self):
		return self.nome


class Produto(models.Model):
	nome = models.CharField(max_length=160)
	descricao = models.TextField()
	categoria = models.ForeignKey(
		Categoria,
		on_delete=models.PROTECT,
		related_name='produtos',
	)
	fornecedor = models.ForeignKey(
		Vendedor,
		on_delete=models.CASCADE,
		related_name='produtos',
	)
	preco = models.DecimalField(
		max_digits=12,
		decimal_places=2,
		validators=[MinValueValidator(0)],
	)
	estoque = models.PositiveIntegerField(default=0)
	unidade_medida = models.CharField(max_length=30, default='unidade')
	imagem = models.ImageField(upload_to='produtos/', blank=True)
	ativo = models.BooleanField(default=True)
	criado_em = models.DateTimeField(auto_now_add=True)
	atualizado_em = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('nome',)
		indexes = [
			models.Index(fields=('ativo', 'categoria')),
			models.Index(fields=('fornecedor', 'ativo')),
		]

	def __str__(self):
		return self.nome
