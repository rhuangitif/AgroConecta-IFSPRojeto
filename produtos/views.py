from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from contas.decorators import fornecedor_required

from vendedores.models import Vendedor
from recomendacoes.services import ranking_mais_vendidos

from .forms import CatalogoFiltroForm, ProdutoForm
from .models import Produto


def _produtos_publicos():
	return (
		Produto.objects.filter(ativo=True)
		.select_related('categoria', 'fornecedor')
		.annotate(
			total_vendido=Coalesce(
				Sum('itens_pedido__quantidade'),
				Value(0),
				output_field=DecimalField(max_digits=20, decimal_places=3),
			)
		)
	)


def catalogo(request):
	fornecedores = Vendedor.objects.filter(ativo=True).order_by('empresa')
	form = CatalogoFiltroForm(request.GET or None, fornecedores=fornecedores)
	produtos = _produtos_publicos()
	if form.is_valid():
		dados = form.cleaned_data
		if dados.get('busca'):
			produtos = produtos.filter(nome__icontains=dados['busca'])
		if dados.get('categoria'):
			produtos = produtos.filter(categoria=dados['categoria'])
		if dados.get('fornecedor'):
			produtos = produtos.filter(fornecedor_id=dados['fornecedor'])
		if dados.get('preco_min') is not None:
			produtos = produtos.filter(preco__gte=dados['preco_min'])
		if dados.get('preco_max') is not None:
			produtos = produtos.filter(preco__lte=dados['preco_max'])
		if dados.get('disponibilidade') == 'disponivel':
			produtos = produtos.filter(estoque__gt=0)
		elif dados.get('disponibilidade') == 'indisponivel':
			produtos = produtos.filter(estoque=0)

		ordenacao = dados.get('ordem')
		if ordenacao == 'menor_preco':
			produtos = produtos.order_by('preco', 'nome')
		elif ordenacao == 'maior_preco':
			produtos = produtos.order_by('-preco', 'nome')
		elif ordenacao == 'mais_vendidos':
			produtos = produtos.order_by('-total_vendido', 'nome')
		elif ordenacao == 'nome':
			produtos = produtos.order_by('nome')
		else:
			produtos = produtos.order_by('-criado_em')
	else:
		produtos = produtos.order_by('-criado_em')

	return render(
		request,
		'produtos/catalogo.html',
		{'form': form, 'produtos': produtos, 'fornecedores': fornecedores},
	)


def produto_detalhe(request, pk):
	produto = get_object_or_404(_produtos_publicos(), pk=pk)
	return render(request, 'produtos/detalhe.html', {'produto': produto})


def mais_vendidos(request):
	return render(
		request,
		'recomendacoes/mais_vendidos.html',
		{'produtos': ranking_mais_vendidos(20)},
	)


@fornecedor_required
def meus_produtos(request):
	produtos = Produto.objects.filter(fornecedor=request.user.vendedor).select_related('categoria')
	return render(request, 'produtos/meus_produtos.html', {'produtos': produtos})


@fornecedor_required
@require_http_methods(['GET', 'POST'])
def produto_novo(request):
	form = ProdutoForm(request.POST or None, request.FILES or None)
	if request.method == 'POST' and form.is_valid():
		produto = form.save(commit=False)
		produto.fornecedor = request.user.vendedor
		produto.save()
		messages.success(request, 'Produto cadastrado com sucesso.')
		return redirect('produtos:meus_produtos')
	return render(request, 'produtos/form.html', {'form': form, 'titulo': 'Novo produto'})


@fornecedor_required
@require_http_methods(['GET', 'POST'])
def produto_editar(request, pk):
	produto = get_object_or_404(Produto, pk=pk, fornecedor=request.user.vendedor)
	form = ProdutoForm(request.POST or None, request.FILES or None, instance=produto)
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, 'Produto atualizado com sucesso.')
		return redirect('produtos:meus_produtos')
	return render(request, 'produtos/form.html', {'form': form, 'titulo': 'Editar produto', 'produto': produto})


@fornecedor_required
@require_POST
def produto_excluir(request, pk):
	produto = get_object_or_404(Produto, pk=pk, fornecedor=request.user.vendedor)
	produto.delete()
	messages.success(request, 'Produto excluido com sucesso.')
	return redirect('produtos:meus_produtos')
