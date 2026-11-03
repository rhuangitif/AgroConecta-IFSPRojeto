from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from produtos.models import Produto, validar_quantidade_unidade


class StatusPedidoFornecedor(models.TextChoices):
	PENDENTE = 'pendente', 'Pendente'
	CONFIRMADO = 'confirmado', 'Confirmado'
	PREPARANDO = 'preparando', 'Preparando'
	ENVIADO = 'enviado', 'Enviado'
	ENTREGUE = 'entregue', 'Entregue'
	CANCELADO = 'cancelado', 'Cancelado'


TRANSICOES_STATUS_PEDIDO = {
	StatusPedidoFornecedor.PENDENTE: {
		StatusPedidoFornecedor.CONFIRMADO,
		StatusPedidoFornecedor.CANCELADO,
	},
	StatusPedidoFornecedor.CONFIRMADO: {
		StatusPedidoFornecedor.PREPARANDO,
		StatusPedidoFornecedor.CANCELADO,
	},
	StatusPedidoFornecedor.PREPARANDO: {
		StatusPedidoFornecedor.ENVIADO,
		StatusPedidoFornecedor.CANCELADO,
	},
	StatusPedidoFornecedor.ENVIADO: {
		StatusPedidoFornecedor.ENTREGUE,
	},
	StatusPedidoFornecedor.ENTREGUE: set(),
	StatusPedidoFornecedor.CANCELADO: set(),
}


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

	def alterar_status(self, novo_status):
		if novo_status not in self.Status.values:
			raise ValidationError('O status informado é inválido.')
		if novo_status == self.status:
			return False
		if novo_status not in TRANSICOES_STATUS_PEDIDO[self.status]:
			status_atual = self.get_status_display()
			status_novo = dict(self.Status.choices)[novo_status]
			raise ValidationError(
				f'Não é possível alterar o status de {status_atual} '
				f'para {status_novo}.'
			)

		self.status = novo_status
		self.save(update_fields=['status', 'atualizado_em'])
		return True

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
		max_digits=22,
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
	quantidade = models.DecimalField(
		max_digits=10,
		decimal_places=3,
		validators=[MinValueValidator(Decimal('0.001'))],
	)
	preco_unitario = models.DecimalField(
		max_digits=12,
		decimal_places=2,
		validators=[MinValueValidator(0)],
	)
	subtotal = models.DecimalField(
		max_digits=22,
		decimal_places=2,
		default=0,
		validators=[MinValueValidator(0)],
	)

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

	def save(self, *args, **kwargs):
		if not self.pedido_legado_id and self.pedido_fornecedor_id:
			self.pedido_legado_id = self.pedido_fornecedor.pedido_id
		self.subtotal = (
			Decimal(str(self.preco_unitario)) * Decimal(str(self.quantidade))
		).quantize(
			Decimal('0.01'),
			rounding=ROUND_HALF_UP,
		)
		super().save(*args, **kwargs)

	@property
	def pedido(self):
		return self.pedido_fornecedor.pedido

	def __str__(self):
		return f'{self.quantidade}x {self.produto}'
