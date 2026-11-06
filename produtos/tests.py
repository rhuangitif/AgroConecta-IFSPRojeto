from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.core.exceptions import ValidationError
from django.test import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse

from contas.models import Perfil
from pedidos.models import Pedido, PedidoFornecedor, PedidoItem
from vendedores.models import Vendedor

from .forms import ProdutoForm
from .models import Categoria, Produto

User = get_user_model()


class CatalogoTests(TestCase):
	def setUp(self):
		self.categoria = Categoria.objects.create(nome='Sementes', slug='sementes')
		self.usuario_a = User.objects.create_user(username='a@teste.local', password='Senha#2026')
		self.usuario_b = User.objects.create_user(username='b@teste.local', password='Senha#2026')
		Perfil.objects.create(usuario=self.usuario_a)
		Perfil.objects.create(usuario=self.usuario_b)
		self.fornecedor_a = Vendedor.objects.create(
			usuario=self.usuario_a,
			empresa='Fornecedor A',
			cnpj='12345678000195',
			endereco='Rua A',
			cidade_sede='Maceio',
			uf_sede='AL',
		)
		self.fornecedor_b = Vendedor.objects.create(
			usuario=self.usuario_b,
			empresa='Fornecedor B',
			cnpj='12345678000276',
			endereco='Rua B',
			cidade_sede='Maceio',
			uf_sede='AL',
		)
		self.produto = Produto.objects.create(
			nome='Semente de Milho',
			descricao='Descricao',
			categoria=self.categoria,
			fornecedor=self.fornecedor_a,
			preco=20,
			estoque=10,
		)
		Produto.objects.create(
			nome='Fertilizante',
			descricao='Descricao',
			categoria=self.categoria,
			fornecedor=self.fornecedor_b,
			preco=30,
			estoque=10,
		)

	def test_catalogo_filtra_por_nome(self):
		response = self.client.get(reverse('produtos:catalogo'), {'busca': 'Milho'})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Semente de Milho')
		self.assertNotContains(response, 'Fertilizante')

	def test_fornecedor_nao_edita_produto_de_outro(self):
		self.client.login(username=self.usuario_b.username, password='Senha#2026')

		response = self.client.get(reverse('fornecedor_produto_editar', args=[self.produto.pk]))

		self.assertEqual(response.status_code, 404)

	def test_estoque_decimal_e_aceito_para_unidade_fracionavel(self):
		form = ProdutoForm(data={
			'nome': 'Milho',
			'descricao': 'Descricao',
			'categoria': self.categoria.pk,
			'preco': '12.50',
			'estoque': '1.250',
			'unidade_medida': 'kg',
			'ativo': 'on',
		})

		self.assertTrue(form.is_valid(), form.errors)
		self.assertEqual(form.cleaned_data['estoque'], Decimal('1.250'))

	def test_estoque_fracionario_e_rejeitado_para_unidade_inteira(self):
		form = ProdutoForm(data={
			'nome': 'Milho',
			'descricao': 'Descricao',
			'categoria': self.categoria.pk,
			'preco': '12.50',
			'estoque': '1.250',
			'unidade_medida': 'un',
			'ativo': 'on',
		})

		self.assertFalse(form.is_valid())
		self.assertIn('estoque', form.errors)

	def test_estoque_nao_pode_ser_negativo(self):
		self.produto.estoque = Decimal('-0.001')

		with self.assertRaises(ValidationError):
			self.produto.full_clean()

		with self.assertRaises(IntegrityError):
			with transaction.atomic():
				Produto.objects.filter(pk=self.produto.pk).update(
					estoque=Decimal('-0.001'),
				)

	def test_slug_e_gerado_com_sufixo_unico(self):
		primeira = Categoria.objects.create(nome='Graos', slug='slug-manual')
		segunda = Categoria.objects.create(nome='Grãos', slug='slug-manual')

		self.assertEqual(primeira.slug, 'graos')
		self.assertEqual(segunda.slug, 'graos-2')

	def test_produto_com_venda_e_desativado_e_protegido(self):
		pedido = Pedido.objects.create(usuario=self.usuario_a)
		pedido_fornecedor = PedidoFornecedor.objects.create(
			pedido=pedido,
			fornecedor=self.fornecedor_a,
		)
		PedidoItem.objects.create(
			pedido_fornecedor=pedido_fornecedor,
			produto=self.produto,
			quantidade=1,
			preco_unitario=self.produto.preco,
		)

		self.produto.delete()

		self.produto.refresh_from_db()
		self.assertFalse(self.produto.ativo)
		with self.assertRaises(ProtectedError):
			Produto.objects.filter(pk=self.produto.pk).delete()
