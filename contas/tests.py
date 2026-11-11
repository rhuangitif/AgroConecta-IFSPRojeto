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
				'password1': 'AgroConecta#2026',
				'password2': 'AgroConecta#2026',
			},
		)

		self.assertRedirects(response, reverse('contas:perfil'))
		user = User.objects.get(username='agricultor@teste.local')
		self.assertEqual(user.perfil.tipo, Perfil.Tipo.AGRICULTOR)
		self.assertTrue(user.check_password('AgroConecta#2026'))

	def test_perfil_exige_login(self):
		response = self.client.get(reverse('contas:perfil'))

		self.assertRedirects(
			response,
			f"{reverse('contas:login')}?next={reverse('contas:perfil')}",
		)

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
