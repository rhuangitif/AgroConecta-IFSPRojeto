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
		Perfil.objects.create(usuario=self.usuario, tipo=Perfil.Tipo.AGRICULTOR)
		fornecedor_user = User.objects.create_user(username='fornecedor@teste.local')
		fornecedor = Vendedor.objects.create(
			usuario=fornecedor_user,
			empresa='Fornecedor',
			cnpj='33.333.333/0001-33',
			email='fornecedor@teste.local',
			telefone='3',
			endereco='Rua C',
			cidade='Maceio',
			estado='AL',
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
