from django.test import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse

from contas.models import Perfil

User = get_user_model()


class DashboardPermissaoTests(TestCase):
	def setUp(self):
		self.agricultor = User.objects.create_user(
			username='agricultor@teste.local', password='Senha#2026',
		)
		Perfil.objects.create(usuario=self.agricultor, tipo=Perfil.Tipo.AGRICULTOR)
		self.admin = User.objects.create_superuser(
			username='admin@teste.local', password='Senha#2026', email='admin@teste.local',
		)

	def test_agricultor_acessa_seu_dashboard_mas_nao_admin(self):
		self.client.login(username=self.agricultor.username, password='Senha#2026')

		self.assertEqual(self.client.get(reverse('dashboard:agricultor')).status_code, 200)
		self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 302)

	def test_staff_acessa_dashboard_administrativo(self):
		self.client.login(username=self.admin.username, password='Senha#2026')

		self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 200)
