import re

from django.core.exceptions import ValidationError


def normalizar_cnpj(valor):
	valor = str(valor or '').strip()
	if any(char not in '0123456789./- ' for char in valor):
		raise ValidationError('Informe um CNPJ contendo apenas numeros e formatacao.')
	return re.sub(r'\D', '', valor)


def validar_cnpj(valor):
	cnpj = normalizar_cnpj(valor)
	if len(cnpj) != 14 or len(set(cnpj)) == 1:
		raise ValidationError('Informe um CNPJ valido com 14 digitos.')

	def calcular_digito(base, pesos):
		resto = sum(int(digito) * peso for digito, peso in zip(base, pesos)) % 11
		return '0' if resto < 2 else str(11 - resto)

	pesos_primeiro = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
	pesos_segundo = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
	primeiro = calcular_digito(cnpj[:12], pesos_primeiro)
	segundo = calcular_digito(cnpj[:12] + primeiro, pesos_segundo)
	if cnpj[-2:] != primeiro + segundo:
		raise ValidationError('O digito verificador do CNPJ e invalido.')
	return cnpj


def formatar_cnpj(valor):
	cnpj = str(valor or '')
	if len(cnpj) != 14 or not cnpj.isdigit():
		return cnpj
	return f'{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}'
