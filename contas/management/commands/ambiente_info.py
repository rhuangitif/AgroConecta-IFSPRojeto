import os
import platform
import sys

import django
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
	help = 'Exibe versoes e informacoes de medicao do ambiente.'

	def handle(self, *args, **options):
		engine = connection.settings_dict['ENGINE']
		banco = f'{connection.vendor} ({engine})'
		servidor = (
			os.environ.get('SERVER_SOFTWARE')
			or (
				'Gunicorn'
				if any(modulo == 'gunicorn' or modulo.startswith('gunicorn.') for modulo in sys.modules)
				else 'Nao detectavel nesta execucao de manage.py'
			)
		)

		self.stdout.write(f'Python: {platform.python_version()}')
		self.stdout.write(f'Django: {django.get_version()}')
		self.stdout.write(f'Banco de dados: {banco}')
		self.stdout.write(f'Servidor de aplicacao: {servidor}')
		self.stdout.write('Registros:')

		modelos = (
			('Usuarios', get_user_model()),
			('Perfis', apps.get_model('contas', 'Perfil')),
			('Fornecedores', apps.get_model('vendedores', 'Vendedor')),
			('Categorias', apps.get_model('produtos', 'Categoria')),
			('Produtos', apps.get_model('produtos', 'Produto')),
			('Carrinhos', apps.get_model('carrinho', 'Carrinho')),
			('Itens de carrinho', apps.get_model('carrinho', 'ItemCarrinho')),
			('Pedidos', apps.get_model('pedidos', 'Pedido')),
			('Pedidos de fornecedor', apps.get_model('pedidos', 'PedidoFornecedor')),
			('Itens de pedido', apps.get_model('pedidos', 'PedidoItem')),
		)

		for rotulo, modelo in modelos:
			self.stdout.write(f'  {rotulo}: {modelo.objects.count()}')
