from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from produtos.models import Produto, validar_quantidade_unidade


class Carrinho(models.Model):
	usuario = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='carrinho',
	)
	criado_em = models.DateTimeField(auto_now_add=True)
	atualizado_em = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f'Carrinho de {self.usuario}'

	@property
	def total(self):
		return sum(item.subtotal for item in self.itens.select_related('produto'))


class ItemCarrinho(models.Model):
	carrinho = models.ForeignKey(
		Carrinho,
		on_delete=models.CASCADE,
		related_name='itens',
	)
	produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
	quantidade = models.DecimalField(
		max_digits=10,
		decimal_places=3,
		default=1,
		validators=[MinValueValidator(Decimal('0.001'))],
	)
	adicionado_em = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=('carrinho', 'produto'),
				name='item_unico_por_carrinho',
			),
		]

	def clean(self):
		super().clean()
		if self.produto_id and self.quantidade is not None:
			try:
				validar_quantidade_unidade(
					self.quantidade,
					self.produto.unidade_medida,
				)
			except ValidationError as erro:
				raise ValidationError({'quantidade': erro.messages}) from erro

	@property
	def subtotal(self):
		return (
			Decimal(str(self.produto.preco)) * Decimal(str(self.quantidade))
		).quantize(
			Decimal('0.01'),
			rounding=ROUND_HALF_UP,
		)

	def __str__(self):
		return f'{self.quantidade}x {self.produto}'
