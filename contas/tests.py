from django.test import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import Perfil

User = get_user_model()


class AutenticacaoTests(TestCase):
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
