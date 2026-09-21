from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from produtos.models import Produto


class Pedido(models.Model):
	class Status(models.TextChoices):
		PENDENTE = 'pendente', 'Pendente'
		CONFIRMADO = 'confirmado', 'Confirmado'
		PREPARANDO = 'preparando', 'Preparando'
		ENVIADO = 'enviado', 'Enviado'
		ENTREGUE = 'entregue', 'Entregue'
		CANCELADO = 'cancelado', 'Cancelado'

	usuario = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.PROTECT,
		related_name='pedidos',
	)
	data = models.DateTimeField(auto_now_add=True)
	valor_total = models.DecimalField(
		max_digits=12,
		decimal_places=2,
		default=0,
		validators=[MinValueValidator(0)],
	)
	status = models.CharField(
		max_length=20,
		choices=Status.choices,
		default=Status.PENDENTE,
	)

	class Meta:
		ordering = ('-data',)

	def __str__(self):
		return f'Pedido #{self.pk}'


class PedidoItem(models.Model):
	pedido = models.ForeignKey(
		Pedido,
		on_delete=models.CASCADE,
		related_name='itens',
	)
	produto = models.ForeignKey(
		Produto,
		on_delete=models.PROTECT,
		related_name='itens_pedido',
	)
	quantidade = models.PositiveIntegerField()
	preco_unitario = models.DecimalField(
		max_digits=12,
		decimal_places=2,
		validators=[MinValueValidator(0)],
	)
	subtotal = models.DecimalField(
		max_digits=12,
		decimal_places=2,
		default=0,
		validators=[MinValueValidator(0)],
	)

	def save(self, *args, **kwargs):
		self.subtotal = self.preco_unitario * self.quantidade
		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.quantidade}x {self.produto}'
