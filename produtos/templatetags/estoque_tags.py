from django import template

from produtos.models import formatar_estoque

register = template.Library()


@register.filter
def estoque_formatado(produto):
	return formatar_estoque(produto)
