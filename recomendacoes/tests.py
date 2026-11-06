from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from contas.models import Perfil
from pedidos.models import Pedido, PedidoFornecedor, PedidoItem
from produtos.models import Categoria, Produto
from vendedores.models import Vendedor

from .services import (
    FONTE_HISTORICO,
    FONTE_MAIS_VENDIDOS,
    FONTE_SEM_VENDAS,
    melhores_precos,
    produtos_recomendados,
    ranking_mais_vendidos,
)

User = get_user_model()


class RecomendacoesTests(TestCase):
	def setUp(self):
		self.agricultor = self.criar_usuario('agricultor@teste.local')
		self.comprador = self.criar_usuario('comprador@teste.local')
		self.fornecedor = self.criar_fornecedor()
		self.sementes = Categoria.objects.create(nome='Sementes', slug='sementes')
		self.fertilizantes = Categoria.objects.create(
			nome='Fertilizantes',
			slug='fertilizantes',
		)

	def criar_usuario(self, username):
		usuario = User.objects.create_user(username=username)
		Perfil.objects.create(usuario=usuario, tipo=Perfil.Tipo.AGRICULTOR)
		return usuario

	def criar_fornecedor(self):
		usuario = User.objects.create_user(username='fornecedor@teste.local')
		return Vendedor.objects.create(
			usuario=usuario,
			empresa='Fornecedor',
			cnpj='55.555.555/0001-55',
			email='fornecedor@teste.local',
			telefone='5',
			endereco='Rua E',
			cidade='Maceio',
			estado='AL',
		)

	def criar_produto(self, nome, categoria, preco, unidade='kg'):
		return Produto.objects.create(
			nome=nome,
			descricao='Descricao',
			categoria=categoria,
			fornecedor=self.fornecedor,
			preco=preco,
			estoque=10,
			unidade_medida=unidade,
		)

	def registrar_compra(self, comprador, produto, quantidade, status=None):
		pedido = Pedido.objects.create(usuario=comprador)
		pedido_fornecedor = PedidoFornecedor.objects.create(
			pedido=pedido,
			fornecedor=produto.fornecedor,
			status=status or PedidoFornecedor.Status.ENTREGUE,
		)
		return PedidoItem.objects.create(
			pedido_fornecedor=pedido_fornecedor,
			produto=produto,
			quantidade=quantidade,
			preco_unitario=produto.preco,
		)

	def test_recomenda_so_produtos_vendidos_e_ordena_por_vendas_preco_id(self):
		comprado = self.criar_produto('Ja comprado', self.sementes, 20)
		mais_caro = self.criar_produto('Empate mais caro', self.sementes, 5)
		mais_barato = self.criar_produto('Empate mais barato', self.sementes, 4)
		mesmo_preco = self.criar_produto('Mesmo preco', self.sementes, 4)
		sem_vendas = self.criar_produto('Sem vendas', self.sementes, 1)
		self.registrar_compra(self.agricultor, comprado, 4)
		self.registrar_compra(self.comprador, mais_caro, 3)
		self.registrar_compra(self.comprador, mais_barato, 3)
		self.registrar_compra(self.comprador, mesmo_preco, 3)

		recomendados, tem_historico, fonte = produtos_recomendados(self.agricultor)

		self.assertTrue(tem_historico)
		self.assertEqual(fonte, FONTE_HISTORICO)
		self.assertEqual(
			list(recomendados),
			[mais_barato, mesmo_preco, mais_caro],
		)
		self.assertNotIn(sem_vendas, recomendados)
		self.assertEqual(
			ranking_mais_vendidos()[0].total_vendido,
			Decimal('4.000'),
		)

	def test_prioriza_categoria_com_maior_quantidade_comprada(self):
		comprado_semente = self.criar_produto('Semente comprada', self.sementes, 10)
		comprado_fertilizante = self.criar_produto(
			'Fertilizante comprado',
			self.fertilizantes,
			10,
		)
		candidato_semente = self.criar_produto(
			'Candidato semente',
			self.sementes,
			10,
		)
		candidato_fertilizante = self.criar_produto(
			'Candidato fertilizante',
			self.fertilizantes,
			10,
		)
		self.registrar_compra(self.agricultor, comprado_semente, 5)
		self.registrar_compra(self.agricultor, comprado_fertilizante, 6)
		self.registrar_compra(self.comprador, candidato_semente, 20)
		self.registrar_compra(self.comprador, candidato_fertilizante, 1)

		recomendados, _, fonte = produtos_recomendados(self.agricultor)

		self.assertEqual(fonte, FONTE_HISTORICO)
		self.assertEqual(
			list(recomendados),
			[candidato_fertilizante, candidato_semente],
		)

	def test_usa_fallback_de_mais_vendidos_rotulado_se_historico_nao_tiver_opcoes(self):
		comprado = self.criar_produto('Comprado', self.sementes, 10)
		mais_vendido = self.criar_produto('Popular', self.fertilizantes, 8)
		sem_vendas = self.criar_produto('Sem vendas', self.fertilizantes, 2)
		self.registrar_compra(self.agricultor, comprado, 1)
		self.registrar_compra(self.comprador, mais_vendido, 2)

		recomendados, tem_historico, fonte = produtos_recomendados(self.agricultor)

		self.assertTrue(tem_historico)
		self.assertEqual(fonte, FONTE_MAIS_VENDIDOS)
		self.assertEqual(list(recomendados), [mais_vendido])
		self.assertNotIn(sem_vendas, recomendados)

	def test_rotula_fallback_de_catalogo_quando_nao_ha_vendas(self):
		produto = self.criar_produto('Produto novo', self.sementes, 10)

		recomendados, tem_historico, fonte = produtos_recomendados(self.agricultor)

		self.assertFalse(tem_historico)
		self.assertEqual(fonte, FONTE_SEM_VENDAS)
		self.assertEqual(list(recomendados), [produto])
		self.client.force_login(self.agricultor)
		response = self.client.get(reverse('recomendacoes:painel'))
		self.assertContains(response, 'Fallback: produtos disponiveis')
		self.assertContains(response, 'ainda sem vendas registradas')

	def test_painel_nao_mostra_produto_sem_vendas_como_recomendacao_historica(self):
		comprado = self.criar_produto('Comprado', self.sementes, 10)
		vendido = self.criar_produto('Vendido', self.sementes, 8)
		sem_vendas = self.criar_produto('Sem vendas', self.sementes, 1)
		self.registrar_compra(self.agricultor, comprado, 1)
		self.registrar_compra(self.comprador, vendido, 1)
		self.client.force_login(self.agricultor)

		response = self.client.get(reverse('recomendacoes:painel'))

		self.assertEqual(response.context['fonte_recomendacao'], FONTE_HISTORICO)
		self.assertEqual(
			list(response.context['recomendados']),
			[vendido],
		)
		self.assertNotIn(sem_vendas, response.context['recomendados'])

	def test_melhores_precos_compara_categoria_e_unidade_e_desempata_por_id(self):
		kg_caro = self.criar_produto('Kg caro', self.sementes, 12, 'kg')
		kg_barato = self.criar_produto('Kg barato', self.sementes, 8, 'kg')
		kg_mesmo_preco = self.criar_produto(
			'Kg mesmo preco',
			self.sementes,
			8,
			'kg',
		)
		saco = self.criar_produto('Saco', self.sementes, 3, 'saco')
		outra_categoria = self.criar_produto(
			'Kg outra categoria',
			self.fertilizantes,
			2,
			'kg',
		)

		resultado = melhores_precos()

		self.assertEqual(
			list(resultado),
			[outra_categoria, saco, kg_barato],
		)
		self.assertNotIn(kg_caro, resultado)
		self.assertNotIn(kg_mesmo_preco, resultado)
		self.assertEqual(resultado[-1].preco_por_unidade, Decimal('8.00'))
