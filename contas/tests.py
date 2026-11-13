from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

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

	def test_cadastro_de_fornecedor_valida_cnpj_e_cria_fornecedor(self):
		response = self.client.post(
			reverse('contas:cadastro'),
			{
				'username': 'fornecedor@teste.local',
				'first_name': 'Fornecedor',
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
