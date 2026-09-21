from django.conf import settings
from django.db import models

from produtos.models import Produto


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
	quantidade = models.PositiveIntegerField(default=1)
	adicionado_em = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=('carrinho', 'produto'),
				name='item_unico_por_carrinho',
			),
		]

	@property
	def subtotal(self):
		return self.produto.preco * self.quantidade

	def __str__(self):
		return f'{self.quantidade}x {self.produto}'
