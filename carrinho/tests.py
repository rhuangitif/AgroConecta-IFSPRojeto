from decimal import Decimal

from django.test import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse

from contas.models import Perfil
from produtos.models import Categoria, Produto
from vendedores.models import Vendedor

from .models import Carrinho

User = get_user_model()


class CarrinhoTests(TestCase):
	def setUp(self):
		self.usuario = User.objects.create_user(
			username='agricultor@teste.local',
			password='Senha#2026',
		)
		Perfil.objects.create(usuario=self.usuario)
		fornecedor_user = User.objects.create_user(username='fornecedor@teste.local')
		fornecedor = Vendedor.objects.create(
			usuario=fornecedor_user,
			empresa='Fornecedor',
			cnpj='12345678000357',
			endereco='Rua C',
			cidade_sede='Maceio',
			uf_sede='AL',
		)
		categoria = Categoria.objects.create(nome='Outros', slug='outros')
		self.produto = Produto.objects.create(
			nome='Produto',
			descricao='Descricao',
			categoria=categoria,
			fornecedor=fornecedor,
			preco=12.50,
			estoque=3,
		)
		self.client.login(username=self.usuario.username, password='Senha#2026')

	def test_adiciona_item_e_impede_excesso_de_estoque(self):
		self.client.post(
			reverse('carrinho:adicionar', args=[self.produto.pk]),
			{'quantidade': 2},
		)
		carrinho = Carrinho.objects.get(usuario=self.usuario)
		item = carrinho.itens.get(produto=self.produto)
		self.assertEqual(item.quantidade, 2)

		self.client.post(
			reverse('carrinho:adicionar', args=[self.produto.pk]),
			{'quantidade': 2},
		)
		self.assertEqual(carrinho.itens.get(pk=item.pk).quantidade, 2)

	def test_adiciona_quantidade_fracionaria_para_produto_fracionavel(self):
		self.produto.unidade_medida = 'kg'
		self.produto.estoque = 2.500
		self.produto.save(update_fields=['unidade_medida', 'estoque'])

		response = self.client.post(
			reverse('carrinho:adicionar', args=[self.produto.pk]),
			{'quantidade': '0.125'},
		)

		self.assertEqual(response.status_code, 302)
		item = Carrinho.objects.get(usuario=self.usuario).itens.get()
		self.assertEqual(item.quantidade, Decimal('0.125'))
		self.assertEqual(item.subtotal, Decimal('1.56'))

	def test_rejeita_quantidade_fracionaria_para_unidade_inteira(self):
		response = self.client.post(
			reverse('carrinho:adicionar', args=[self.produto.pk]),
			{'quantidade': '1.5'},
			follow=True,
		)

		self.assertContains(response, 'não aceita fração')
		self.assertFalse(Carrinho.objects.filter(usuario=self.usuario).exists())

	def test_total_do_carrinho_e_calculado_dinamicamente(self):
		self.client.post(
			reverse('carrinho:adicionar', args=[self.produto.pk]),
			{'quantidade': 2},
		)
		carrinho = Carrinho.objects.get(usuario=self.usuario)
		self.assertEqual(carrinho.total, Decimal('25.00'))
		self.assertNotIn('total', {field.name for field in Carrinho._meta.fields})

		self.produto.preco = Decimal('15.00')
		self.produto.save(update_fields=['preco'])
		self.assertEqual(carrinho.total, Decimal('30.00'))
