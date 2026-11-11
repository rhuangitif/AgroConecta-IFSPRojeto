from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from contas.decorators import agricultor_required
from pedidos.forms import PedidoForm
from produtos.models import Produto, validar_quantidade_unidade

from .forms import QuantidadeForm
from .models import Carrinho, ItemCarrinho


def _mensagem_erro_quantidade(request, form):
	messages.error(request, form.errors['quantidade'][0])


def _form_quantidade(request, unidade_medida):
	dados = request.POST.copy()
	dados.setdefault('quantidade', '1')
	return QuantidadeForm(dados, unidade_medida=unidade_medida)


@agricultor_required
def ver_carrinho(request):
	carrinho, _ = Carrinho.objects.get_or_create(usuario=request.user)
	itens = carrinho.itens.select_related('produto', 'produto__fornecedor').order_by('adicionado_em')
	perfil = getattr(request.user, 'perfil', None)
	form = PedidoForm(initial={
		'cidade_entrega': perfil.cidade if perfil else '',
		'estado_entrega': perfil.estado if perfil else '',
	})
	return render(
		request,
		'carrinho/ver.html',
		{'carrinho': carrinho, 'itens': itens, 'pedido_form': form},
	)


@agricultor_required
@require_POST
def adicionar(request, produto_id):
	with transaction.atomic():
		produto = get_object_or_404(
			Produto.objects.select_for_update(),
			pk=produto_id,
			ativo=True,
		)
		form = _form_quantidade(request, produto.unidade_medida)
		if not form.is_valid():
			_mensagem_erro_quantidade(request, form)
			return redirect('produtos:detalhe', produto_id)
		quantidade = form.cleaned_data['quantidade']
		if produto.estoque < quantidade:
			messages.error(request, 'A quantidade solicitada excede o estoque disponível.')
			return redirect('produtos:detalhe', produto_id)
		carrinho, _ = Carrinho.objects.get_or_create(usuario=request.user)
		item, criado = ItemCarrinho.objects.select_for_update().get_or_create(
			carrinho=carrinho,
			produto=produto,
			defaults={'quantidade': quantidade},
		)
		if not criado:
			nova_quantidade = item.quantidade + quantidade
			try:
				validar_quantidade_unidade(nova_quantidade, produto.unidade_medida)
			except ValidationError as erro:
				messages.error(request, erro.messages[0])
				return redirect('produtos:detalhe', produto_id)
			if nova_quantidade > produto.estoque:
				messages.error(request, 'A quantidade total no carrinho excede o estoque disponível.')
				return redirect('produtos:detalhe', produto_id)
			item.quantidade = nova_quantidade
			try:
				item.full_clean()
			except ValidationError as erro:
				messages.error(request, ' '.join(erro.messages))
				return redirect('produtos:detalhe', produto_id)
			item.save(update_fields=['quantidade'])
	messages.success(request, 'Produto adicionado ao carrinho.')
	return redirect('carrinho:ver')


@agricultor_required
@require_POST
def atualizar(request, item_id):
	with transaction.atomic():
		item = get_object_or_404(
			ItemCarrinho.objects.select_for_update().select_related('produto'),
			pk=item_id,
			carrinho__usuario=request.user,
		)
		produto = Produto.objects.select_for_update().get(pk=item.produto_id)
		form = _form_quantidade(request, produto.unidade_medida)
		if not form.is_valid():
			_mensagem_erro_quantidade(request, form)
			return redirect('carrinho:ver')
		quantidade = form.cleaned_data['quantidade']
		if quantidade > produto.estoque:
			messages.error(request, f'O estoque disponível é {produto.estoque}.')
			return redirect('carrinho:ver')
		item.quantidade = quantidade
		try:
			item.full_clean()
		except ValidationError as erro:
			messages.error(request, ' '.join(erro.messages))
			return redirect('carrinho:ver')
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
