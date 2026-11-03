from django.test import TestCase

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from carrinho.models import Carrinho
from contas.models import Perfil
from produtos.models import Categoria, Produto
from vendedores.models import Vendedor

from .models import Pedido, PedidoFornecedor

User = get_user_model()


class PedidoTests(TestCase):
	def setUp(self):
		self.usuario = User.objects.create_user(
			username='agricultor@teste.local',
			password='Senha#2026',
		)
		Perfil.objects.create(usuario=self.usuario, tipo=Perfil.Tipo.AGRICULTOR)
		fornecedor_user = User.objects.create_user(
			username='fornecedor@teste.local',
			password='Senha#2026',
		)
		Perfil.objects.create(usuario=fornecedor_user, tipo=Perfil.Tipo.FORNECEDOR)
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
		self.fornecedor = fornecedor
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
		self.assertEqual(pedido.fornecedores.count(), 1)
		self.assertEqual(pedido.fornecedores.get().itens.count(), 1)
		self.assertEqual(self.produto.estoque, 3)
		self.assertEqual(Carrinho.objects.get(usuario=self.usuario).itens.count(), 0)

	def test_checkout_separa_itens_e_status_por_fornecedor(self):
		outro_fornecedor_user = User.objects.create_user(
			username='outro-fornecedor@teste.local',
			password='Senha#2026',
		)
		Perfil.objects.create(
			usuario=outro_fornecedor_user,
			tipo=Perfil.Tipo.FORNECEDOR,
		)
		outro_fornecedor = Vendedor.objects.create(
			usuario=outro_fornecedor_user,
			empresa='Outro fornecedor',
			cnpj='33.333.333/0001-91',
			endereco='Rua E',
			cidade='Maceio',
			estado='AL',
		)
		outro_produto = Produto.objects.create(
			nome='Semente',
			descricao='Descricao',
			categoria=self.produto.categoria,
			fornecedor=outro_fornecedor,
			preco=10,
			estoque=5,
		)
		self.adicionar_ao_carrinho(1)
		self.client.post(
			reverse('carrinho:adicionar', args=[outro_produto.pk]),
			{'quantidade': 2},
		)

		response = self.client.post(reverse('pedidos:finalizar'))

		pedido = Pedido.objects.get(usuario=self.usuario)
		self.assertRedirects(response, reverse('pedidos:detalhe', args=[pedido.pk]))
		self.assertEqual(pedido.fornecedores.count(), 2)
		self.assertEqual(pedido.itens.count(), 2)
		pedido_a = pedido.fornecedores.get(fornecedor=self.fornecedor)
		pedido_b = pedido.fornecedores.get(fornecedor=outro_fornecedor)
		self.assertEqual(pedido_a.itens.count(), 1)
		self.assertEqual(pedido_b.itens.count(), 1)

		self.client.logout()
		self.client.login(username='fornecedor@teste.local', password='Senha#2026')
		response = self.client.get(reverse('pedidos:recebidos'))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.context['pedidos']), 1)
		self.assertEqual(response.context['pedidos'][0].fornecedor, self.fornecedor)
		response = self.client.post(
			reverse('fornecedor_pedido_status', args=[pedido_a.pk]),
			{'status': PedidoFornecedor.Status.CONFIRMADO},
		)
		self.assertRedirects(response, reverse('pedidos:recebidos'))
		pedido_a.refresh_from_db()
		pedido_b.refresh_from_db()
		self.assertEqual(pedido_a.status, PedidoFornecedor.Status.CONFIRMADO)
		self.assertEqual(pedido_b.status, PedidoFornecedor.Status.PENDENTE)

		response = self.client.post(
			reverse('fornecedor_pedido_status', args=[pedido_b.pk]),
			{'status': PedidoFornecedor.Status.ENVIADO},
		)
		self.assertEqual(response.status_code, 404)
		pedido_b.refresh_from_db()
		self.assertEqual(pedido_b.status, PedidoFornecedor.Status.PENDENTE)

	def test_status_geral_e_derivado_dos_status_dos_fornecedores(self):
		self.adicionar_ao_carrinho(1)
		self.client.post(reverse('pedidos:finalizar'))
		pedido = Pedido.objects.get(usuario=self.usuario)
		pedido_fornecedor = pedido.fornecedores.get()
		self.assertEqual(pedido.status, Pedido.Status.PENDENTE)

		for status in (
			PedidoFornecedor.Status.CONFIRMADO,
			PedidoFornecedor.Status.PREPARANDO,
			PedidoFornecedor.Status.ENVIADO,
			PedidoFornecedor.Status.ENTREGUE,
		):
			pedido_fornecedor.alterar_status(status)

		self.assertEqual(pedido.status, Pedido.Status.ENTREGUE)

	def test_transicoes_validas_de_status(self):
		self.adicionar_ao_carrinho(1)
		self.client.post(reverse('pedidos:finalizar'))
		pedido_fornecedor = Pedido.objects.get(usuario=self.usuario).fornecedores.get()

		for status in (
			PedidoFornecedor.Status.CONFIRMADO,
			PedidoFornecedor.Status.PREPARANDO,
			PedidoFornecedor.Status.ENVIADO,
			PedidoFornecedor.Status.ENTREGUE,
		):
			with self.subTest(status=status):
				self.assertTrue(pedido_fornecedor.alterar_status(status))
				pedido_fornecedor.refresh_from_db()
				self.assertEqual(pedido_fornecedor.status, status)

	def test_cancelamento_e_permitido_antes_do_envio_e_e_final(self):
		self.adicionar_ao_carrinho(1)
		self.client.post(reverse('pedidos:finalizar'))
		pedido_fornecedor = Pedido.objects.get(usuario=self.usuario).fornecedores.get()

		self.assertTrue(
			pedido_fornecedor.alterar_status(PedidoFornecedor.Status.CANCELADO)
		)
		with self.assertRaisesMessage(ValidationError, 'de Cancelado para Confirmado'):
			pedido_fornecedor.alterar_status(PedidoFornecedor.Status.CONFIRMADO)

		pedido_fornecedor.refresh_from_db()
		self.assertEqual(pedido_fornecedor.status, PedidoFornecedor.Status.CANCELADO)

	def test_transicoes_invalidas_e_status_final_sao_rejeitados(self):
		self.adicionar_ao_carrinho(1)
		self.client.post(reverse('pedidos:finalizar'))
		pedido_fornecedor = Pedido.objects.get(usuario=self.usuario).fornecedores.get()

		with self.assertRaisesMessage(ValidationError, 'de Pendente para Entregue'):
			pedido_fornecedor.alterar_status(PedidoFornecedor.Status.ENTREGUE)

		pedido_fornecedor.alterar_status(PedidoFornecedor.Status.CONFIRMADO)
		pedido_fornecedor.alterar_status(PedidoFornecedor.Status.PREPARANDO)
		pedido_fornecedor.alterar_status(PedidoFornecedor.Status.ENVIADO)
		pedido_fornecedor.alterar_status(PedidoFornecedor.Status.ENTREGUE)
		with self.assertRaisesMessage(ValidationError, 'de Entregue para Pendente'):
			pedido_fornecedor.alterar_status(PedidoFornecedor.Status.PENDENTE)

		pedido_fornecedor.refresh_from_db()
		self.assertEqual(pedido_fornecedor.status, PedidoFornecedor.Status.ENTREGUE)

	def test_view_retorna_erro_amigavel_para_transicao_invalida(self):
		self.adicionar_ao_carrinho(1)
		self.client.post(reverse('pedidos:finalizar'))
		pedido_fornecedor = Pedido.objects.get(usuario=self.usuario).fornecedores.get()
		pedido_fornecedor.alterar_status(PedidoFornecedor.Status.CONFIRMADO)

		self.client.logout()
		self.client.login(username='fornecedor@teste.local', password='Senha#2026')
		response = self.client.post(
			reverse('fornecedor_pedido_status', args=[pedido_fornecedor.pk]),
			{'status': PedidoFornecedor.Status.PENDENTE},
			follow=True,
		)

		self.assertContains(response, 'Não é possível alterar o status')
		self.assertContains(response, 'Etapa não permitida')
		self.assertContains(response, 'status-step')
		self.assertContains(response, 'alert-status-transition')
		pedido_fornecedor.refresh_from_db()
		self.assertEqual(pedido_fornecedor.status, PedidoFornecedor.Status.CONFIRMADO)

	def test_finalizacao_cancelada_se_estoque_mudou(self):
		self.adicionar_ao_carrinho(4)
		self.produto.estoque = 2
		self.produto.save(update_fields=['estoque', 'atualizado_em'])

		response = self.client.post(reverse('pedidos:finalizar'))

		self.assertRedirects(response, reverse('carrinho:ver'))
		self.assertFalse(Pedido.objects.filter(usuario=self.usuario).exists())
		self.assertEqual(Carrinho.objects.get(usuario=self.usuario).itens.count(), 1)
