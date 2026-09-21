from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from contas.decorators import agricultor_required
from produtos.models import Produto

from .models import Carrinho, ItemCarrinho


def _quantidade_enviada(request):
	try:
		quantidade = int(request.POST.get('quantidade', 1))
	except (TypeError, ValueError):
		return None
	return quantidade if quantidade > 0 else None


@agricultor_required
def ver_carrinho(request):
	carrinho, _ = Carrinho.objects.get_or_create(usuario=request.user)
	itens = carrinho.itens.select_related('produto', 'produto__fornecedor').order_by('adicionado_em')
	return render(request, 'carrinho/ver.html', {'carrinho': carrinho, 'itens': itens})


@agricultor_required
@require_POST
def adicionar(request, produto_id):
	quantidade = _quantidade_enviada(request)
	if quantidade is None:
		messages.error(request, 'Informe uma quantidade valida.')
		return redirect('produtos:detalhe', produto_id)

	with transaction.atomic():
		produto = get_object_or_404(
			Produto.objects.select_for_update(),
			pk=produto_id,
			ativo=True,
		)
		if produto.estoque < quantidade:
			messages.error(request, 'A quantidade solicitada excede o estoque disponivel.')
			return redirect('produtos:detalhe', produto_id)
		carrinho, _ = Carrinho.objects.get_or_create(usuario=request.user)
		item, criado = ItemCarrinho.objects.select_for_update().get_or_create(
			carrinho=carrinho,
			produto=produto,
			defaults={'quantidade': quantidade},
		)
		if not criado:
			nova_quantidade = item.quantidade + quantidade
			if nova_quantidade > produto.estoque:
				messages.error(request, 'A quantidade total no carrinho excede o estoque disponivel.')
				return redirect('produtos:detalhe', produto_id)
			item.quantidade = nova_quantidade
			item.save(update_fields=['quantidade'])
	messages.success(request, 'Produto adicionado ao carrinho.')
	return redirect('carrinho:ver')


@agricultor_required
@require_POST
def atualizar(request, item_id):
	quantidade = _quantidade_enviada(request)
	if quantidade is None:
		messages.error(request, 'Informe uma quantidade valida.')
		return redirect('carrinho:ver')

	with transaction.atomic():
		item = get_object_or_404(
			ItemCarrinho.objects.select_for_update().select_related('produto'),
			pk=item_id,
			carrinho__usuario=request.user,
		)
		produto = Produto.objects.select_for_update().get(pk=item.produto_id)
		if quantidade > produto.estoque:
			messages.error(request, f'O estoque disponivel e {produto.estoque}.')
			return redirect('carrinho:ver')
		item.quantidade = quantidade
		item.save(update_fields=['quantidade'])
	messages.success(request, 'Carrinho atualizado.')
	return redirect('carrinho:ver')


@agricultor_required
@require_POST
def remover(request, item_id):
	item = get_object_or_404(ItemCarrinho, pk=item_id, carrinho__usuario=request.user)
	item.delete()
	messages.success(request, 'Produto removido do carrinho.')
	return redirect('carrinho:ver')
