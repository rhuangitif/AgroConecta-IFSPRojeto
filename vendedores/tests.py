from django.test import TestCase

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from contas.forms import VendedorForm
from .models import Vendedor
from .validators import formatar_cnpj

User = get_user_model()


class VendedorIntegridadeTests(TestCase):
	def criar_usuario(self, username):
		return User.objects.create_user(username=username)

	def test_cnpj_mascarado_e_persistido_apenas_com_digitos(self):
		vendedor = Vendedor.objects.create(
			usuario=self.criar_usuario('cnpj@teste.local'),
			empresa='Fornecedor',
			cnpj='12.345.678/0001-95',
		)

		self.assertEqual(vendedor.cnpj, '12345678000195')
		self.assertEqual(formatar_cnpj(vendedor.cnpj), '12.345.678/0001-95')

	def test_cnpj_com_digito_verificador_invalido_e_rejeitado(self):
		with self.assertRaises(ValidationError):
			Vendedor.objects.create(
				usuario=self.criar_usuario('cnpj-invalido@teste.local'),
				empresa='Fornecedor',
				cnpj='12345678000000',
			)

	def test_cnpj_e_obrigatorio_para_fornecedor_ativo(self):
		with self.assertRaises(ValidationError):
			Vendedor.objects.create(
				usuario=self.criar_usuario('sem-cnpj@teste.local'),
				empresa='Fornecedor',
				cnpj=None,
			)

	def test_fornecedores_anonimizados_podem_ter_cnpj_nulo(self):
		for numero in (1, 2):
			Vendedor.objects.create(
				usuario=self.criar_usuario(f'anonimo{numero}@teste.local'),
				empresa=f'Fornecedor anonimizado {numero}',
				cnpj=None,
				ativo=False,
			)

		self.assertEqual(
			Vendedor.objects.filter(cnpj__isnull=True).count(),
			2,
		)

	def test_cnpj_duplicado_com_mascara_e_rejeitado_no_formulario(self):
		Vendedor.objects.create(
			usuario=self.criar_usuario('existente@teste.local'),
			empresa='Fornecedor existente',
			cnpj='12345678000195',
		)
		form = VendedorForm(data={
			'empresa': 'Outro fornecedor',
			'cnpj': '12.345.678/0001-95',
			'endereco': '',
			'cidade_sede': '',
			'uf_sede': '',
			'descricao': '',
		})

		self.assertFalse(form.is_valid())
		self.assertIn('cnpj', form.errors)

	def test_cnpj_legado_invalido_pode_ser_preservado_sem_alteracao(self):
		usuario = self.criar_usuario('legado@teste.local')
		Vendedor.objects.bulk_create([
			Vendedor(
				usuario=usuario,
				empresa='Fornecedor legado',
				cnpj='12345678000100',
			),
		])
		vendedor = Vendedor.objects.get(usuario=usuario)
		vendedor.empresa = 'Fornecedor legado atualizado'

		vendedor.save()

		self.assertEqual(vendedor.cnpj, '12345678000100')
