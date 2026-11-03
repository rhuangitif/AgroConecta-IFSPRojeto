from django.test import TestCase

from django.contrib.auth import get_user_model

from contas.models import Perfil
from pedidos.models import Pedido, PedidoFornecedor, PedidoItem
from produtos.models import Categoria, Produto
from vendedores.models import Vendedor

from .services import produtos_recomendados, ranking_mais_vendidos

User = get_user_model()


class RecomendacoesTests(TestCase):
	def test_recomenda_categoria_relacionada_e_calcula_ranking(self):
		agricultor = User.objects.create_user(username='agricultor@teste.local')
		Perfil.objects.create(usuario=agricultor, tipo=Perfil.Tipo.AGRICULTOR)
		fornecedor_user = User.objects.create_user(username='fornecedor@teste.local')
		fornecedor = Vendedor.objects.create(
			usuario=fornecedor_user,
			empresa='Fornecedor',
			cnpj='55.555.555/0001-55',
			email='fornecedor@teste.local',
			telefone='5',
			endereco='Rua E',
			cidade='Maceio',
			estado='AL',
		)
		sementes = Categoria.objects.create(nome='Sementes', slug='sementes')
		fertilizantes = Categoria.objects.create(nome='Fertilizantes', slug='fertilizantes')
		semente = Produto.objects.create(
			nome='Semente', descricao='Descricao', categoria=sementes,
			fornecedor=fornecedor, preco=20, estoque=10,
		)
		fertilizante = Produto.objects.create(
			nome='Fertilizante', descricao='Descricao', categoria=fertilizantes,
			fornecedor=fornecedor, preco=30, estoque=10,
		)
		pedido = Pedido.objects.create(usuario=agricultor, valor_total=80)
		pedido_fornecedor = PedidoFornecedor.objects.create(
			pedido=pedido,
			fornecedor=fornecedor,
			status=PedidoFornecedor.Status.ENTREGUE,
		)
		PedidoItem.objects.create(
			pedido_fornecedor=pedido_fornecedor,
			produto=semente,
			quantidade=4,
			preco_unitario=20,
		)

		recomendados, tem_historico = produtos_recomendados(agricultor)
		ranking = list(ranking_mais_vendidos())

		self.assertTrue(tem_historico)
		self.assertIn(fertilizante, recomendados)
		self.assertEqual(ranking[0].pk, semente.pk)
		self.assertEqual(ranking[0].total_vendido, 4)
