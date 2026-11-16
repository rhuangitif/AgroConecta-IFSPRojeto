from decimal import Decimal

from django.test import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse

from contas.models import Perfil
from pedidos.models import Pedido, PedidoFornecedor, PedidoItem
from produtos.models import Categoria, Produto
from vendedores.models import Vendedor

User = get_user_model()


class DashboardPermissaoTests(TestCase):
	def setUp(self):
		self.agricultor = User.objects.create_user(
			username='agricultor@teste.local', password='Senha#2026',
		)
		Perfil.objects.create(usuario=self.agricultor)
		self.admin = User.objects.create_superuser(
			username='admin@teste.local', password='Senha#2026', email='admin@teste.local',
		)

	def test_agricultor_acessa_seu_dashboard_mas_nao_admin(self):
		self.client.login(username=self.agricultor.username, password='Senha#2026')

		self.assertEqual(self.client.get(reverse('dashboard:agricultor')).status_code, 200)
		self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 302)

	def test_staff_acessa_dashboard_administrativo(self):
		self.client.login(username=self.admin.username, password='Senha#2026')

		self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 200)

	def test_total_de_vendas_agrega_pedidos_e_formata_duas_casas(self):
		Pedido.objects.create(usuario=self.agricultor, valor_total='12.30')
		Pedido.objects.create(usuario=self.admin, valor_total='0.05')
		self.client.login(username=self.admin.username, password='Senha#2026')

		response = self.client.get(reverse('admin_dashboard'))

		self.assertEqual(response.context['total_vendas'].as_tuple().exponent, -2)
		self.assertEqual(response.context['total_vendas'], Decimal('12.35'))

	def test_painel_fornecedor_formata_estoque_sem_zeros_finais(self):
		fornecedor_usuario = User.objects.create_user(
			username='fornecedor@teste.local',
			password='Senha#2026',
		)
		Perfil.objects.create(usuario=fornecedor_usuario)
		fornecedor = Vendedor.objects.create(
			usuario=fornecedor_usuario,
			empresa='Fornecedor de teste',
			cnpj='12345678000195',
			endereco='Rua de teste',
			cidade_sede='Maceió',
			uf_sede='AL',
		)
		categoria = Categoria.objects.create(nome='Categoria de teste')
		Produto.objects.create(
			nome='Produto fracionável',
			descricao='Produto para teste de estoque',
			categoria=categoria,
			fornecedor=fornecedor,
			preco='10.00',
			estoque='2.500',
			unidade_medida='kg',
		)
		self.client.force_login(fornecedor_usuario)

		response = self.client.get(reverse('fornecedor_dashboard'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, '2,5 kg')
		self.assertNotContains(response, '2.500 kg')

	def test_painel_fornecedor_formata_total_vendido_em_centavos(self):
		fornecedor_usuario = User.objects.create_user(
			username='fornecedor-vendas@teste.local',
			password='Senha#2026',
		)
		Perfil.objects.create(usuario=fornecedor_usuario)
		fornecedor = Vendedor.objects.create(
			usuario=fornecedor_usuario,
			empresa='Fornecedor de vendas',
			cnpj='12345678000276',
			endereco='Rua de teste',
			cidade_sede='Maceió',
			uf_sede='AL',
		)
		categoria = Categoria.objects.create(nome='Categoria de vendas')
		produto = Produto.objects.create(
			nome='Produto vendido',
			descricao='Produto para teste de total',
			categoria=categoria,
			fornecedor=fornecedor,
			preco='78.82',
			estoque=5,
		)
		pedido = Pedido.objects.create(usuario=self.agricultor)
		pedido_fornecedor = PedidoFornecedor.objects.create(
			pedido=pedido,
			fornecedor=fornecedor,
			status=PedidoFornecedor.Status.ENTREGUE,
		)
		PedidoItem.objects.create(
			pedido_fornecedor=pedido_fornecedor,
			produto=produto,
			quantidade='3',
			preco_unitario='78.82',
		)
		self.client.force_login(fornecedor_usuario)

		response = self.client.get(reverse('fornecedor_dashboard'))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(
			response.context['total_vendido'],
			Decimal('236.46'),
		)
		self.assertContains(response, 'R$ 236,46')
		self.assertNotContains(response, '236,460000')
