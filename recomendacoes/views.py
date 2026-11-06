from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import melhores_precos, produtos_recomendados, ranking_mais_vendidos


@login_required
def painel_recomendacoes(request):
	recomendados, tem_historico, fonte_recomendacao = produtos_recomendados(request.user)
	return render(
		request,
		'recomendacoes/painel.html',
		{
			'recomendados': recomendados,
			'tem_historico': tem_historico,
			'fonte_recomendacao': fonte_recomendacao,
			'melhores_precos': melhores_precos(),
		},
	)


def mais_vendidos(request):
	return render(
		request,
		'recomendacoes/mais_vendidos.html',
		{'produtos': ranking_mais_vendidos(20)},
	)
