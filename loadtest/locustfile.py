import csv
import os
import re
import threading
from html.parser import HTMLParser
from itertools import count
from pathlib import Path

from locust import HttpUser, task
from locust.exception import StopUser


class _CsrfTokenParser(HTMLParser):
	def __init__(self):
		super().__init__()
		self.token = None

	def handle_starttag(self, tag, attrs):
		if tag != 'input':
			return
		atributos = dict(attrs)
		if atributos.get('name') == 'csrfmiddlewaretoken':
			self.token = atributos.get('value')


def _carregar_contas():
	caminho = Path(os.environ.get(
		'LOADTEST_USERS_CSV',
		Path(__file__).with_name('users.csv'),
	))
	with caminho.open(encoding='utf-8-sig', newline='') as arquivo:
		contas = [
			{
				'username': linha.get('username', '').strip(),
				'password': linha.get('password', ''),
			}
			for linha in csv.DictReader(arquivo)
		]
	contas = [
		conta for conta in contas
		if conta['username'] and conta['password']
	]
	if not contas:
		raise RuntimeError(
			f'Nenhuma conta válida encontrada no CSV de carga: {caminho}'
		)
	return contas


_CONTAS = _carregar_contas()
_INDICES_CONTAS = count()
_TRAVA_CONTAS = threading.Lock()


def _proxima_conta():
	with _TRAVA_CONTAS:
		indice = next(_INDICES_CONTAS)
	if indice >= len(_CONTAS):
		raise RuntimeError(
			'Quantidade de usuários Locust maior que o número de contas no CSV. '
			'Crie uma conta agricultora exclusiva para cada usuário simulado.'
		)
	return _CONTAS[indice]


def _token_csrf(html):
	parser = _CsrfTokenParser()
	parser.feed(html)
	return parser.token


class FluxoCompraUser(HttpUser):
	wait_time = lambda self: 0

	def on_start(self):
		self.conta = _proxima_conta()
		try:
			self.product_id = int(os.environ['LOADTEST_PRODUCT_ID'])
		except (KeyError, ValueError) as erro:
			raise RuntimeError(
				'Defina LOADTEST_PRODUCT_ID com o ID de um produto ativo '
				'e com estoque suficiente.'
			) from erro

	def _get_html(self, path, nome, texto_necessario=None):
		with self.client.get(path, name=nome, catch_response=True) as response:
			if response.status_code != 200:
				response.failure(f'Esperado HTTP 200; recebido {response.status_code}')
				raise StopUser()
			if texto_necessario and texto_necessario not in response.text:
				response.failure(f'Conteúdo esperado ausente: {texto_necessario}')
				raise StopUser()
			return response.text

	def _post_form(self, path, nome, dados, token, location_esperado):
		with self.client.post(
			path,
			name=nome,
			data={**dados, 'csrfmiddlewaretoken': token},
			headers={'Referer': f'{self.host}{path}', 'X-CSRFToken': token},
			allow_redirects=False,
			catch_response=True,
		) as response:
			location = response.headers.get('Location', '')
			if response.status_code not in (301, 302, 303):
				response.failure(
					f'Esperado redirecionamento HTTP; recebido {response.status_code}'
				)
				raise StopUser()
			if not re.search(location_esperado, location):
				response.failure(f'Redirecionamento inesperado: {location}')
				raise StopUser()

	@task
	def fluxo_de_compra(self):
		catalogo = self._get_html('/', '01 - listagem de produtos')
		caminho_detalhe = f'/produtos/{self.product_id}/'
		if f'href="{caminho_detalhe}"' not in catalogo:
			with self.client.get(
				caminho_detalhe,
				name='02 - detalhe do produto',
				catch_response=True,
			) as response:
				response.failure(
					'O produto configurado não aparece no catálogo público.'
				)
			raise StopUser()

		detalhe = self._get_html(
			caminho_detalhe,
			'02 - detalhe do produto',
			'Entre para comprar',
		)
		if 'Esgotado' in detalhe:
			raise StopUser()

		login_html = self._get_html('/login/', '03 - formulário de login')
		csrf_login = _token_csrf(login_html)
		if not csrf_login:
			raise RuntimeError('O formulário de login não contém token CSRF.')
		self._post_form(
			'/login/',
			'04 - login',
			{
				'username': self.conta['username'],
				'password': self.conta['password'],
				'next': '',
			},
			csrf_login,
			r'^/perfil/?$',
		)

		carrinho_html = self._get_html('/carrinho/', '05 - carrinho vazio')
		if 'Seu carrinho está vazio' not in carrinho_html:
			raise RuntimeError(
				f"A conta {self.conta['username']} não está com o carrinho vazio. "
				'Limpe-o antes de executar a carga.'
			)
		csrf_carrinho = _token_csrf(carrinho_html)
		if not csrf_carrinho:
			raise RuntimeError('A página do carrinho não contém token CSRF.')
		self._post_form(
			f'/carrinho/adicionar/{self.product_id}/',
			'06 - adicionar ao carrinho',
			{'quantidade': '1'},
			csrf_carrinho,
			r'^/carrinho/?$',
		)

		carrinho_com_item = self._get_html(
			'/carrinho/',
			'07 - carrinho com produto',
			'Finalizar pedido',
		)
		csrf_checkout = _token_csrf(carrinho_com_item)
		if not csrf_checkout:
			raise RuntimeError('O formulário de checkout não contém token CSRF.')
		self._post_form(
			'/pedidos/finalizar/',
			'08 - finalizar pedido',
			{
				'endereco_entrega': 'Endereço de teste de carga',
				'cidade_entrega': 'Cidade de teste',
				'estado_entrega': 'SP',
				'forma_pagamento': 'pix',
				'observacoes': 'Pedido criado por teste de carga.',
			},
			csrf_checkout,
			r'^/pedidos/\d+/$',
		)
		raise StopUser()
