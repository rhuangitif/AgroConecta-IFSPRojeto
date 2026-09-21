from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from contas.decorators import agricultor_required, fornecedor_required
from produtos.models import Produto

from carrinho.models import Carrinho

from .models import Pedido, PedidoItem


@agricultor_required
@require_POST
def finalizar_pedido(request):
	with transaction.atomic():
		carrinho = get_object_or_404(
			Carrinho.objects.select_for_update(),
			usuario=request.user,
		)
		itens = list(carrinho.itens.select_for_update().select_related('produto'))
		if not itens:
			messages.error(request, 'Seu carrinho esta vazio.')
			return redirect('carrinho:ver')

		produtos = {}
		for item in itens:
			produto = Produto.objects.select_for_update().get(pk=item.produto_id)
			if not produto.ativo or item.quantidade > produto.estoque:
				messages.error(
					request,
					f'Estoque insuficiente para {produto.nome}. Revise seu carrinho.',
				)
				return redirect('carrinho:ver')
			produtos[produto.pk] = produto

		pedido = Pedido.objects.create(usuario=request.user)
		total = Decimal('0.00')
		for item in itens:
			produto = produtos[item.produto_id]
			pedido_item = PedidoItem.objects.create(
				pedido=pedido,
				produto=produto,
				quantidade=item.quantidade,
				preco_unitario=produto.preco,
			)
			total += pedido_item.subtotal
			produto.estoque -= item.quantidade
			produto.save(update_fields=['estoque', 'atualizado_em'])
		pedido.valor_total = total
		pedido.save(update_fields=['valor_total'])
		carrinho.itens.all().delete()

	messages.success(request, f'Pedido #{pedido.pk} realizado com sucesso.')
	return redirect('pedidos:detalhe', pedido.pk)


@agricultor_required
def meus_pedidos(request):
	pedidos = Pedido.objects.filter(usuario=request.user).prefetch_related('itens__produto').order_by('-data')
	return render(request, 'pedidos/meus_pedidos.html', {'pedidos': pedidos})


@agricultor_required
def pedido_detalhe(request, pk):
	pedido = get_object_or_404(
		Pedido.objects.prefetch_related('itens__produto__fornecedor'),
		pk=pk,
		usuario=request.user,
	)
	return render(request, 'pedidos/detalhe.html', {'pedido': pedido})


@fornecedor_required
def pedidos_recebidos(request):
	pedidos = (
		Pedido.objects.filter(itens__produto__fornecedor=request.user.vendedor)
		.distinct()
		.prefetch_related('itens__produto', 'usuario')
		.order_by('-data')
	)
	return render(
		request,
		'pedidos/recebidos.html',
		{'pedidos': pedidos, 'status_choices': Pedido.Status.choices},
	)


@fornecedor_required
@require_POST
def atualizar_status(request, pk):
	pedido = get_object_or_404(
		Pedido,
		pk=pk,
		itens__produto__fornecedor=request.user.vendedor,
	)
	status = request.POST.get('status')
	if status not in Pedido.Status.values:
		messages.error(request, 'Status de pedido invalido.')
		return redirect('pedidos:recebidos')
	pedido.status = status
	pedido.save(update_fields=['status'])
	messages.success(request, f'Status do pedido #{pedido.pk} atualizado.')
	return redirect('pedidos:recebidos')
