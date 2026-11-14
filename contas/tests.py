from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from carrinho.models import Carrinho, ItemCarrinho
from pedidos.models import HistoricoStatus, Pedido, PedidoFornecedor, PedidoItem
from produtos.models import Categoria
from .models import Perfil
from .forms import CadastroForm
from produtos.forms import ProdutoForm
from produtos.models import Produto
from vendedores.models import Vendedor

User = get_user_model()


class AutenticacaoTests(TestCase):
	def test_campos_select_exibem_prompt_em_portugues(self):
		self.assertEqual(
			CadastroForm().fields['estado'].choices[0],
			('', 'Selecione uma opção'),
		)
		self.assertEqual(
			ProdutoForm().fields['categoria'].empty_label,
			'Selecione uma opção',
		)

	def test_cadastro_de_agricultor_cria_perfil_e_autentica(self):
		response = self.client.post(
			reverse('contas:cadastro'),
			{
				'username': 'agricultor@teste.local',
				'first_name': 'Agricultor',
				'aceite_termos': 'on',
				'tipo': Perfil.Tipo.AGRICULTOR,
				'telefone': '82999999999',
				'cidade': 'Maceio',
				'estado': 'AL',
				'cnpj': '123',
				'password1': 'AgroConecta#2026',
				'password2': 'AgroConecta#2026',
			},
		)

		self.assertRedirects(response, reverse('contas:perfil'))
		user = User.objects.get(username='agricultor@teste.local')
		self.assertEqual(user.perfil.tipo, Perfil.Tipo.AGRICULTOR)
		self.assertTrue(user.check_password('AgroConecta#2026'))
		self.assertIsNotNone(user.perfil.aceite_termos_em)

	def test_cadastro_de_fornecedor_valida_cnpj_e_cria_fornecedor(self):
		response = self.client.post(
			reverse('contas:cadastro'),
			{
				'username': 'fornecedor@teste.local',
				'first_name': 'Fornecedor',
				'aceite_termos': 'on',
				'tipo': Perfil.Tipo.FORNECEDOR,
				'telefone': '82999999999',
				'cidade': 'Maceió',
				'estado': 'AL',
				'empresa': 'Fornecedor Rural',
				'cnpj': '12.345.678/0001-95',
				'endereco': 'Rua das Flores, 10',
				'password1': 'AgroConecta#2026',
				'password2': 'AgroConecta#2026',
			},
		)

		self.assertRedirects(response, reverse('contas:perfil'))
		user = User.objects.get(email='fornecedor@teste.local')
		self.assertEqual(user.perfil.tipo, Perfil.Tipo.FORNECEDOR)
		self.assertEqual(user.vendedor.cnpj, '12345678000195')

	def test_cadastro_de_fornecedor_exibe_erro_para_cnpj_invalido(self):
		response = self.client.post(
			reverse('contas:cadastro'),
			{
				'username': 'cnpj-invalido@teste.local',
				'first_name': 'Fornecedor',
				'aceite_termos': 'on',
				'tipo': Perfil.Tipo.FORNECEDOR,
				'telefone': '82999999999',
				'cidade': 'Maceió',
				'estado': 'AL',
				'empresa': 'Fornecedor Rural',
				'cnpj': '12345678000000',
				'endereco': 'Rua das Flores, 10',
				'password1': 'AgroConecta#2026',
				'password2': 'AgroConecta#2026',
			},
		)

		self.assertContains(response, 'O dígito verificador do CNPJ é inválido.')
		self.assertContains(response, 'id_cnpj_errors')
		self.assertContains(response, 'is-invalid')
		self.assertFalse(User.objects.filter(email='cnpj-invalido@teste.local').exists())

	def test_cadastro_exige_aceite_de_termos_e_privacidade(self):
		response = self.client.post(
			reverse('contas:cadastro'),
			{
				'username': 'sem-aceite@teste.local',
				'first_name': 'Sem aceite',
				'tipo': Perfil.Tipo.AGRICULTOR,
				'telefone': '82999999999',
				'cidade': 'Maceió',
				'estado': 'AL',
				'password1': 'AgroConecta#2026',
				'password2': 'AgroConecta#2026',
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'id_aceite_termos_errors')
		self.assertFalse(User.objects.filter(username='sem-aceite@teste.local').exists())

	def test_paginas_de_termos_e_privacidade_sao_publicas(self):
		for nome_url, conteudo in (
			('contas:termos', 'Termos de Uso'),
			('contas:privacidade', 'Política de Privacidade'),
		):
			with self.subTest(nome_url=nome_url):
				response = self.client.get(reverse(nome_url))

				self.assertEqual(response.status_code, 200)
				self.assertContains(response, conteudo)

	def test_anonimizacao_requer_senha_correta_e_confirmacao(self):
		user = User.objects.create_user(
			username='anonimizar@teste.local',
			email='anonimizar@teste.local',
			password='SenhaCorreta#2026',
		)
		Perfil.objects.create(usuario=user, telefone='82999999999')
		self.client.force_login(user)

		response = self.client.post(
			reverse('contas:anonimizar'),
			{'senha': 'errada', 'confirmar': 'on'},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'A senha informada está incorreta.')
		user.refresh_from_db()
		self.assertTrue(user.is_active)
		self.assertEqual(user.perfil.telefone, '82999999999')

	def test_anonimizacao_exige_confirmacao_explicita(self):
		user = User.objects.create_user(
			username='sem-confirmacao@teste.local',
			password='SenhaCorreta#2026',
		)
		Perfil.objects.create(usuario=user)
		self.client.force_login(user)

		response = self.client.post(
			reverse('contas:anonimizar'),
			{'senha': 'SenhaCorreta#2026'},
		)

		self.assertEqual(response.status_code, 200)
		user.refresh_from_db()
		self.assertTrue(user.is_active)
		self.assertIsNone(user.perfil.anonimizado_em)

	def test_anonimizacao_preserva_pedidos_e_remove_dados_pessoais(self):
		user = User.objects.create_user(
			username='vendedor@teste.local',
			email='vendedor@teste.local',
			first_name='Nome Pessoal',
			last_name='Sobrenome Pessoal',
			password='SenhaCorreta#2026',
		)
		aceite_em = timezone.now()
		Perfil.objects.create(
			usuario=user,
			telefone='82999999999',
			cidade='Maceió',
			estado='AL',
			aceite_termos_em=aceite_em,
		)
		vendedor = Vendedor.objects.create(
			usuario=user,
			empresa='Empresa Identificável',
			cnpj='12345678000195',
			endereco='Rua Particular',
			cidade_sede='Maceió',
			uf_sede='AL',
			descricao='Descrição identificável',
		)
		categoria = Categoria.objects.create(nome='Produtos anonimizacao')
		produto = Produto.objects.create(
			nome='Produto de histórico',
			descricao='Descrição do produto',
			categoria=categoria,
			fornecedor=vendedor,
			preco='12.50',
			estoque=5,
		)
		pedido = Pedido.objects.create(
			usuario=user,
			endereco_entrega='Rua da Casa, 123',
			cidade_entrega='Maceió',
			estado_entrega='AL',
			observacoes='Deixar com a pessoa identificável',
		)
		pedido_fornecedor = PedidoFornecedor.objects.create(
			pedido=pedido,
			fornecedor=vendedor,
		)
		PedidoItem.objects.create(
			pedido_fornecedor=pedido_fornecedor,
			produto=produto,
			quantidade=1,
			preco_unitario='12.50',
		)
		evento = HistoricoStatus.objects.create(
			pedido_fornecedor=pedido_fornecedor,
			status_anterior=PedidoFornecedor.Status.PENDENTE,
			status_novo=PedidoFornecedor.Status.CONFIRMADO,
			autor=user,
		)
		carrinho = Carrinho.objects.create(usuario=user)
		ItemCarrinho.objects.create(
			carrinho=carrinho,
			produto=produto,
			quantidade=1,
		)
		self.client.force_login(user)

		response = self.client.post(
			reverse('contas:anonimizar'),
			{'senha': 'SenhaCorreta#2026', 'confirmar': 'on'},
		)

		self.assertRedirects(response, reverse('contas:login'))
		user.refresh_from_db()
		pedido.refresh_from_db()
		pedido_fornecedor.refresh_from_db()
		vendedor.refresh_from_db()
		produto.refresh_from_db()
		evento.refresh_from_db()
		perfil = Perfil.objects.get(usuario=user)
		self.assertFalse(user.is_active)
		self.assertEqual(user.first_name, '')
		self.assertEqual(user.last_name, '')
		self.assertNotEqual(user.email, 'vendedor@teste.local')
		self.assertFalse(user.has_usable_password())
		self.assertEqual(perfil.telefone, '')
		self.assertEqual(perfil.cidade, '')
		self.assertEqual(perfil.estado, '')
		self.assertIsNotNone(perfil.anonimizado_em)
		self.assertEqual(perfil.aceite_termos_em, aceite_em)
		self.assertEqual(pedido.endereco_entrega, '')
		self.assertEqual(pedido.cidade_entrega, '')
		self.assertEqual(pedido.estado_entrega, '')
		self.assertEqual(pedido.observacoes, '')
		self.assertEqual(pedido.usuario_id, user.pk)
		self.assertIsNone(evento.autor)
		self.assertEqual(vendedor.cnpj, None)
		self.assertFalse(vendedor.ativo)
		self.assertEqual(vendedor.empresa, f'Fornecedor anonimizado {vendedor.pk}')
		self.assertEqual(vendedor.endereco, '')
		self.assertEqual(vendedor.cidade_sede, '')
		self.assertEqual(vendedor.uf_sede, '')
		self.assertFalse(produto.ativo)
		self.assertEqual(produto.imagem.name, '')
		self.assertTrue(Pedido.objects.filter(pk=pedido.pk).exists())
		self.assertTrue(PedidoItem.objects.filter(pedido_fornecedor=pedido_fornecedor).exists())
		self.assertFalse(Carrinho.objects.filter(usuario=user).exists())

	def test_login_com_senha_incorreta_exibe_erro_no_campo(self):
		User.objects.create_user(
			username='login@teste.local',
			email='login@teste.local',
			password='SenhaCorreta#2026',
		)

		response = self.client.post(
			reverse('contas:login'),
			{'username': 'login@teste.local', 'password': 'SenhaErrada#2026'},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'E-mail ou senha incorretos.')
		self.assertContains(response, 'id_password_errors')
		self.assertContains(response, 'is-invalid')
		self.assertFalse(response.wsgi_request.user.is_authenticated)

	def test_logout_encerra_sessao_por_post(self):
		user = User.objects.create_user(username='sair@teste.local', password='Senha#2026')
		self.client.force_login(user)

		response = self.client.post(reverse('contas:logout'))

		self.assertRedirects(response, reverse('contas:login'))
		self.assertFalse(response.wsgi_request.user.is_authenticated)

	def test_perfil_exige_login(self):
		response = self.client.get(reverse('contas:perfil'))

		self.assertRedirects(
			response,
			f"{reverse('contas:login')}?next={reverse('contas:perfil')}",
		)

	def test_paginas_protegidas_redirecionam_quando_nao_ha_login(self):
		for url_name in ('contas:editar_perfil', 'dashboard:agricultor'):
			with self.subTest(url_name=url_name):
				url = reverse(url_name)
				response = self.client.get(url)

				self.assertRedirects(response, f"{reverse('contas:login')}?next={url}")

	def test_edicao_de_email_atualiza_identificador_de_login(self):
		user = User.objects.create_user(
			username='antes@teste.local',
			email='antes@teste.local',
			password='SenhaCorreta#2026',
		)
		self.client.force_login(user)

		response = self.client.post(
			reverse('contas:editar_perfil'),
			{
				'first_name': 'Nome',
				'last_name': 'Sobrenome',
				'email': 'depois@teste.local',
				'telefone': '82999999999',
				'cidade': 'Maceió',
				'estado': 'AL',
			},
		)

		self.assertRedirects(response, reverse('contas:perfil'))
		user.refresh_from_db()
		self.assertEqual(user.username, 'depois@teste.local')
		self.assertEqual(user.perfil.cidade, 'Maceió')
		self.client.logout()
		self.assertTrue(
			self.client.login(username='depois@teste.local', password='SenhaCorreta#2026'),
		)

	def test_edicao_de_perfil_exibe_erro_de_email_duplicado_no_campo(self):
		user = User.objects.create_user(
			username='usuario@teste.local',
			email='usuario@teste.local',
			password='SenhaCorreta#2026',
		)
		User.objects.create_user(
			username='outro@teste.local',
			email='outro@teste.local',
			password='SenhaCorreta#2026',
		)
		Perfil.objects.create(usuario=user)
		self.client.force_login(user)

		response = self.client.post(
			reverse('contas:editar_perfil'),
			{
				'first_name': 'Nome',
				'last_name': 'Sobrenome',
				'email': 'outro@teste.local',
				'telefone': '82999999999',
				'cidade': 'Maceió',
				'estado': 'AL',
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Já existe uma conta com este e-mail.')
		self.assertContains(response, 'id_email_errors')
		self.assertContains(response, 'is-invalid')

	def test_tipo_do_perfil_e_derivado_da_existencia_de_vendedor(self):
		user = User.objects.create_user(username='tipo@teste.local')
		perfil = Perfil.objects.create(usuario=user)

		self.assertEqual(perfil.tipo, Perfil.Tipo.AGRICULTOR)
		Vendedor.objects.create(
			usuario=user,
			empresa='Fornecedor',
			cnpj='12345678000195',
		)
		perfil = Perfil.objects.get(pk=perfil.pk)
		self.assertEqual(perfil.tipo, Perfil.Tipo.FORNECEDOR)

	def test_estado_do_perfil_rejeita_uf_fora_das_choices(self):
		user = User.objects.create_user(username='uf@teste.local')
		perfil = Perfil(usuario=user, estado='XX')

		with self.assertRaises(ValidationError):
			perfil.full_clean()


class SeedDataTests(TestCase):
	def test_seed_preserva_contas_password_e_produtos_realistas(self):
		senha = 'AgroConecta#Teste2026'
		call_command('seed_data', password=senha, stdout=StringIO())

		for email in (
			'agricultor@agroconecta.local',
			'fornecedor.verde@agroconecta.local',
			'fornecedor.campo@agroconecta.local',
			'admin@agroconecta.local',
		):
			usuario = User.objects.get(username=email)
			self.assertTrue(usuario.check_password(senha))

		nomes = set(Produto.objects.values_list('nome', flat=True))
		self.assertIn('Fertilizante NPK', nomes)
		self.assertIn('Ração para aves de postura', nomes)
		self.assertIn('Defensivo biológico para lagartas', nomes)
		self.assertTrue(all(produto.descricao.strip() != 'd' for produto in Produto.objects.all()))

		quantidade_produtos = Produto.objects.count()
		call_command('seed_data', password=senha, stdout=StringIO())
		self.assertEqual(Produto.objects.count(), quantidade_produtos)
