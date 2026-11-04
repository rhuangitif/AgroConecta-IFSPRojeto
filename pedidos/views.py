from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from contas.decorators import agricultor_required, fornecedor_required
from produtos.models import Produto

from carrinho.models import Carrinho

from .models import Pedido, PedidoFornecedor, PedidoItem


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

		produto_ids = sorted({item.produto_id for item in itens})
		produtos = {
			produto.pk: produto
			for produto in Produto.objects.select_for_update()
			.filter(pk__in=produto_ids)
			.order_by('pk')
		}
		for item in itens:
			produto = produtos[item.produto_id]
			try:
				item.full_clean()
			except ValidationError as erro:
				messages.error(
					request,
					f'Quantidade invalida para {produto.nome}: {" ".join(erro.messages)}',
				)
				return redirect('carrinho:ver')
			if not produto.ativo or item.quantidade > produto.estoque:
				messages.error(
					request,
					f'Estoque insuficiente para {produto.nome}. Revise seu carrinho.',
				)
				return redirect('carrinho:ver')

		pedido = Pedido.objects.create(usuario=request.user)
		total = Decimal('0.00')
		pedidos_fornecedor = {}
		for item in itens:
			produto = produtos[item.produto_id]
			pedido_fornecedor = pedidos_fornecedor.get(produto.fornecedor_id)
			if pedido_fornecedor is None:
				pedido_fornecedor = PedidoFornecedor.objects.create(
					pedido=pedido,
					fornecedor=produto.fornecedor,
				)
				pedidos_fornecedor[produto.fornecedor_id] = pedido_fornecedor
			pedido_item = PedidoItem(
				pedido_fornecedor=pedido_fornecedor,
				pedido_legado=pedido,
				produto=produto,
				quantidade=item.quantidade,
				preco_unitario=produto.preco,
			)
			pedido_item.full_clean()
			pedido_item.save()
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
	pedidos = Pedido.objects.filter(usuario=request.user).prefetch_related(
		'fornecedores__itens__produto',
	).order_by('-data')
	return render(request, 'pedidos/meus_pedidos.html', {'pedidos': pedidos})


@agricultor_required
def pedido_detalhe(request, pk):
	pedido = get_object_or_404(
		Pedido.objects.prefetch_related('fornecedores__itens__produto__fornecedor'),
		pk=pk,
		usuario=request.user,
	)
	return render(request, 'pedidos/detalhe.html', {'pedido': pedido})


@fornecedor_required
def pedidos_recebidos(request):
	pedidos = (
		PedidoFornecedor.objects.filter(fornecedor=request.user.vendedor)
		.select_related('pedido', 'pedido__usuario', 'fornecedor')
		.prefetch_related('itens__produto')
	)
	return render(
		request,
		'pedidos/recebidos.html',
		{'pedidos': pedidos, 'status_choices': PedidoFornecedor.Status.choices},
	)


@fornecedor_required
@require_POST
def atualizar_status(request, pk):
	with transaction.atomic():
		pedido_fornecedor = get_object_or_404(
			PedidoFornecedor.objects.select_for_update(),
			pk=pk,
			fornecedor=request.user.vendedor,
		)
		try:
			pedido_fornecedor.alterar_status(request.POST.get('status'))
		except ValidationError as erro:
			messages.error(
				request,
				' '.join(erro.messages),
				extra_tags='status-transition',
			)
			return redirect('pedidos:recebidos')
	messages.success(request, f'Status do pedido #{pedido_fornecedor.pedido_id} atualizado.')
	return redirect('pedidos:recebidos')
