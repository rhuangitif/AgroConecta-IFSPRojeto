from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from vendedores.models import Vendedor


class UnidadeMedida(models.TextChoices):
	UN = 'un', 'Unidade'
	KG = 'kg', 'Quilograma'
	G = 'g', 'Grama'
	SACO = 'saco', 'Saco'
	LITRO = 'litro', 'Litro'
	ML = 'ml', 'Mililitro'
	TONELADA = 'tonelada', 'Tonelada'
	CAIXA = 'caixa', 'Caixa'


UNIDADES_INTEIRAS = {
	UnidadeMedida.UN,
	UnidadeMedida.SACO,
	UnidadeMedida.CAIXA,
}


def validar_quantidade_unidade(quantidade, unidade, permitir_zero=False):
	if quantidade is None:
		return

	try:
		valor = Decimal(quantidade)
	except (TypeError, ValueError):
		raise ValidationError('Informe uma quantidade valida.') from None

	if valor < 0 or (valor == 0 and not permitir_zero):
		raise ValidationError('A quantidade deve ser maior que zero.')
	if valor.as_tuple().exponent < -3:
		raise ValidationError('A quantidade aceita no maximo tres casas decimais.')
	if unidade in UNIDADES_INTEIRAS and valor != valor.to_integral_value():
		nome_unidade = dict(UnidadeMedida.choices).get(unidade, unidade)
		raise ValidationError(
			f'A unidade de medida {nome_unidade.lower()} nao aceita fracao.'
		)


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
	estoque = models.DecimalField(
		max_digits=10,
		decimal_places=3,
		default=0,
		validators=[MinValueValidator(0)],
	)
	unidade_medida = models.CharField(
		max_length=10,
		choices=UnidadeMedida.choices,
		default=UnidadeMedida.UN,
	)
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

	def clean(self):
		super().clean()
		if self.estoque is not None and self.unidade_medida:
			try:
				validar_quantidade_unidade(
					self.estoque,
					self.unidade_medida,
					permitir_zero=True,
				)
			except ValidationError as erro:
				raise ValidationError({'estoque': erro.messages}) from erro

	@property
	def unidade_inteira(self):
		return self.unidade_medida in UNIDADES_INTEIRAS

	def __str__(self):
		return self.nome
