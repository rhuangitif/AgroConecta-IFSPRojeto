from django.test import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse

from carrinho.models import Carrinho
from contas.models import Perfil
from produtos.models import Categoria, Produto
from vendedores.models import Vendedor

from .models import Pedido

User = get_user_model()


class PedidoTests(TestCase):
	def setUp(self):
		self.usuario = User.objects.create_user(
			username='agricultor@teste.local',
			password='Senha#2026',
		)
		Perfil.objects.create(usuario=self.usuario, tipo=Perfil.Tipo.AGRICULTOR)
		fornecedor_user = User.objects.create_user(username='fornecedor@teste.local')
		fornecedor = Vendedor.objects.create(
			usuario=fornecedor_user,
			empresa='Fornecedor',
			cnpj='44.444.444/0001-44',
			email='fornecedor@teste.local',
			telefone='4',
			endereco='Rua D',
			cidade='Maceio',
			estado='AL',
		)
		categoria = Categoria.objects.create(nome='Ferramentas', slug='ferramentas')
		self.produto = Produto.objects.create(
			nome='Enxada',
			descricao='Descricao',
			categoria=categoria,
			fornecedor=fornecedor,
			preco=25,
			estoque=5,
		)
		self.client.login(username=self.usuario.username, password='Senha#2026')

	def adicionar_ao_carrinho(self, quantidade):
		self.client.post(
			reverse('carrinho:adicionar', args=[self.produto.pk]),
			{'quantidade': quantidade},
		)

	def test_finalizacao_cria_pedido_reduz_estoque_e_limpa_carrinho(self):
		self.adicionar_ao_carrinho(2)

		response = self.client.post(reverse('pedidos:finalizar'))

		pedido = Pedido.objects.get(usuario=self.usuario)
		self.produto.refresh_from_db()
		self.assertRedirects(response, reverse('pedidos:detalhe', args=[pedido.pk]))
		self.assertEqual(pedido.valor_total, 50)
		self.assertEqual(pedido.itens.get().preco_unitario, 25)
		self.assertEqual(self.produto.estoque, 3)
		self.assertEqual(Carrinho.objects.get(usuario=self.usuario).itens.count(), 0)

	def test_finalizacao_cancelada_se_estoque_mudou(self):
		self.adicionar_ao_carrinho(4)
		self.produto.estoque = 2
		self.produto.save(update_fields=['estoque', 'atualizado_em'])

		response = self.client.post(reverse('pedidos:finalizar'))

		self.assertRedirects(response, reverse('carrinho:ver'))
		self.assertFalse(Pedido.objects.filter(usuario=self.usuario).exists())
		self.assertEqual(Carrinho.objects.get(usuario=self.usuario).itens.count(), 1)
