from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from produtos.models import Produto


class StatusPedidoFornecedor(models.TextChoices):
	PENDENTE = 'pendente', 'Pendente'
	CONFIRMADO = 'confirmado', 'Confirmado'
	PREPARANDO = 'preparando', 'Preparando'
	ENVIADO = 'enviado', 'Enviado'
	ENTREGUE = 'entregue', 'Entregue'
	CANCELADO = 'cancelado', 'Cancelado'


class PedidoFornecedor(models.Model):
	Status = StatusPedidoFornecedor

	pedido = models.ForeignKey(
		'pedidos.Pedido',
		on_delete=models.CASCADE,
		related_name='fornecedores',
	)
	fornecedor = models.ForeignKey(
		'vendedores.Vendedor',
		on_delete=models.PROTECT,
		related_name='pedidos',
	)
	status = models.CharField(
		max_length=20,
		choices=Status.choices,
		default=Status.PENDENTE,
	)
	criado_em = models.DateTimeField(auto_now_add=True)
	atualizado_em = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=('pedido', 'fornecedor'),
				name='pedido_fornecedor_unico',
			),
		]
		ordering = ('-criado_em',)

	@property
	def valor_total(self):
		return sum(item.subtotal for item in self.itens.all())

	def __str__(self):
		return f'{self.pedido} - {self.fornecedor}'


class Pedido(models.Model):
	Status = StatusPedidoFornecedor

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
	status_legado = models.CharField(
		db_column='status',
		max_length=20,
		choices=Status.choices,
		default=Status.PENDENTE,
		editable=False,
	)
	class Meta:
		ordering = ('-data',)

	@property
	def status(self):
		statuses = list(self.fornecedores.values_list('status', flat=True))
		if not statuses:
			return self.Status.PENDENTE
		if all(status == self.Status.CANCELADO for status in statuses):
			return self.Status.CANCELADO

		statuses_ativos = [
			status for status in statuses if status != self.Status.CANCELADO
		]
		prioridade = {
			self.Status.PENDENTE: 0,
			self.Status.CONFIRMADO: 1,
			self.Status.PREPARANDO: 2,
			self.Status.ENVIADO: 3,
			self.Status.ENTREGUE: 4,
		}
		return min(statuses_ativos, key=lambda status: prioridade[status])

	def get_status_display(self):
		statuses = set(self.fornecedores.values_list('status', flat=True))
		if len(statuses) > 1 and self.Status.CANCELADO in statuses:
			return 'Parcialmente cancelado'
		return dict(self.Status.choices).get(self.status, self.status)

	@property
	def itens(self):
		return PedidoItem.objects.filter(pedido_fornecedor__pedido=self)

	def __str__(self):
		return f'Pedido #{self.pk}'


class PedidoItem(models.Model):
	pedido_fornecedor = models.ForeignKey(
		PedidoFornecedor,
		on_delete=models.CASCADE,
		related_name='itens',
	)
	pedido_legado = models.ForeignKey(
		Pedido,
		db_column='pedido_id',
		on_delete=models.CASCADE,
		related_name='itens_legados',
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
		if not self.pedido_legado_id and self.pedido_fornecedor_id:
			self.pedido_legado_id = self.pedido_fornecedor.pedido_id
		self.subtotal = self.preco_unitario * self.quantidade
		super().save(*args, **kwargs)

	@property
	def pedido(self):
		return self.pedido_fornecedor.pedido

	def __str__(self):
		return f'{self.quantidade}x {self.produto}'
