from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction

from contas.choices import UnidadeFederativa
from produtos.models import Produto, UnidadeMedida, validar_quantidade_unidade


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

	def alterar_status(self, novo_status, autor=None):
		with transaction.atomic():
			pedido_fornecedor = type(self).objects.select_for_update().get(pk=self.pk)
			if novo_status not in self.Status.values:
				raise ValidationError('O status informado é inválido.')
			if novo_status == pedido_fornecedor.status:
				self.status = pedido_fornecedor.status
				return False
			if novo_status not in TRANSICOES_STATUS_PEDIDO[pedido_fornecedor.status]:
				status_atual = pedido_fornecedor.get_status_display()
				status_novo = dict(self.Status.choices)[novo_status]
				raise ValidationError(
					f'Não é possível alterar o status de {status_atual} '
					f'para {status_novo}.'
				)

			if novo_status == self.Status.CANCELADO:
				quantidades = {}
				for produto_id, quantidade in PedidoItem.objects.filter(
					pedido_fornecedor=pedido_fornecedor,
				).values_list('produto_id', 'quantidade'):
					quantidades[produto_id] = (
						quantidades.get(produto_id, Decimal('0')) + quantidade
					)
				produtos = {
					produto.pk: produto
					for produto in Produto.objects.select_for_update()
					.filter(pk__in=quantidades)
					.order_by('pk')
				}
				for produto_id, quantidade in quantidades.items():
					produto = produtos[produto_id]
					produto.estoque += quantidade
					produto.full_clean()
					produto.save(update_fields=['estoque', 'atualizado_em'])

			pedido_fornecedor.status = novo_status
			pedido_fornecedor._autor_status = autor
			pedido_fornecedor.save(update_fields=['status', 'atualizado_em'])
			self.status = novo_status
			return True

	def save(self, *args, **kwargs):
		novo_registro = self._state.adding
		update_fields = kwargs.get('update_fields')
		status_sendo_salvo = update_fields is None or 'status' in update_fields
		with transaction.atomic():
			status_anterior = None
			if not novo_registro and status_sendo_salvo:
				status_anterior = (
					type(self).objects.select_for_update()
					.filter(pk=self.pk)
					.values_list('status', flat=True)
					.first()
				)
			super().save(*args, **kwargs)
			if (
				status_anterior is not None
				and status_sendo_salvo
				and status_anterior != self.status
			):
				HistoricoStatus.objects.create(
					pedido_fornecedor=self,
					status_anterior=status_anterior,
					status_novo=self.status,
					autor=getattr(self, '_autor_status', None),
				)

	def __str__(self):
		return f'{self.pedido} - {self.fornecedor}'


class Pedido(models.Model):
	Status = StatusPedidoFornecedor

	class FormaPagamento(models.TextChoices):
		PIX = 'pix', 'Pix'
		CARTAO_CREDITO = 'cartao_credito', 'Cartão de crédito'
		CARTAO_DEBITO = 'cartao_debito', 'Cartão de débito'
		BOLETO = 'boleto', 'Boleto'

	usuario = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.PROTECT,
		related_name='pedidos',
	)
	criado_em = models.DateTimeField(auto_now_add=True)
	endereco_entrega = models.CharField(max_length=255, blank=True)
	cidade_entrega = models.CharField(max_length=100, blank=True)
	estado_entrega = models.CharField(
		max_length=2,
		choices=UnidadeFederativa.choices,
		blank=True,
	)
	forma_pagamento = models.CharField(
		max_length=20,
		choices=FormaPagamento.choices,
		default=FormaPagamento.PIX,
	)
	observacoes = models.TextField(blank=True)
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
		ordering = ('-criado_em',)

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

	@transaction.atomic
	def cancelar(self, autor=None):
		pedido = type(self).objects.select_for_update().get(pk=self.pk)
		fornecedores = pedido.fornecedores.select_for_update().order_by('pk')
		alterado = False
		for pedido_fornecedor in fornecedores:
			alterado = (
				pedido_fornecedor.alterar_status(
					self.Status.CANCELADO,
					autor=autor,
				)
				or alterado
			)
		return alterado

	@property
	def itens(self):
		return PedidoItem.objects.filter(pedido_fornecedor__pedido=self)

	def __str__(self):
		return f'Pedido #{self.pk}'


class HistoricoStatus(models.Model):
	pedido_fornecedor = models.ForeignKey(
		PedidoFornecedor,
		on_delete=models.CASCADE,
		related_name='historico_status',
	)
	status_anterior = models.CharField(
		max_length=20,
		choices=StatusPedidoFornecedor.choices,
	)
	status_novo = models.CharField(
		max_length=20,
		choices=StatusPedidoFornecedor.choices,
	)
	autor = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='alteracoes_status_pedidos',
	)
	criado_em = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ('criado_em', 'pk')

	def __str__(self):
		return f'{self.pedido_fornecedor}: {self.status_anterior} -> {self.status_novo}'


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
	nome_produto = models.CharField(max_length=160)
	unidade_medida = models.CharField(max_length=10, choices=UnidadeMedida.choices)
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
		if self._state.adding:
			if not self.nome_produto:
				self.nome_produto = self.produto.nome
			if not self.unidade_medida:
				self.unidade_medida = self.produto.unidade_medida
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
