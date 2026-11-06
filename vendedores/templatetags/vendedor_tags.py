from django import template

from vendedores.validators import formatar_cnpj


register = template.Library()


@register.filter
def cnpj_formatado(valor):
	return formatar_cnpj(valor)
