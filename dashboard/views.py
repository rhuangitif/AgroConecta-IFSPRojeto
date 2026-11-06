from django.contrib.auth import get_user_model
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render
from decimal import Decimal

from carrinho.models import Carrinho
from contas.decorators import agricultor_required, fornecedor_required
from contas.models import Perfil
from pedidos.models import Pedido, PedidoFornecedor, PedidoItem
from produtos.models import Produto
from recomendacoes.services import STATUS_COM_VENDA, produtos_recomendados, ranking_mais_vendidos

User = get_user_model()


@agricultor_required
def agricultor_dashboard(request):
	recomendados, tem_historico, fonte_recomendacao = produtos_recomendados(
		request.user,
		limite=6,
	)
	pedidos = Pedido.objects.filter(usuario=request.user).prefetch_related(
		'fornecedores__itens__produto',
	)[:5]
	carrinho = Carrinho.objects.filter(usuario=request.user).first()
	return render(
		request,
		'dashboard/agricultor.html',
		{
			'recomendados': recomendados,
			'tem_historico': tem_historico,
			'fonte_recomendacao': fonte_recomendacao,
			'pedidos': pedidos,
			'itens_carrinho': carrinho.itens.count() if carrinho else 0,
		},
	)


@fornecedor_required
def fornecedor_dashboard(request):
	fornecedor = request.user.vendedor
	produtos = Produto.objects.filter(fornecedor=fornecedor)
	pedidos = (
		PedidoFornecedor.objects.filter(fornecedor=fornecedor)
		.select_related('pedido', 'pedido__usuario')
		.prefetch_related('itens__produto')
	)
	total_vendido = PedidoItem.objects.filter(
		pedido_fornecedor__fornecedor=fornecedor,
		pedido_fornecedor__status__in=STATUS_COM_VENDA,
	).aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
	status_counts = {
		status: total
		for status, total in pedidos.values('status').annotate(total=Count('id')).values_list('status', 'total')
	}
	return render(
		request,
		'dashboard/fornecedor.html',
		{
			'total_produtos': produtos.count(),
			'produtos_ativos': produtos.filter(ativo=True).count(),
			'estoque_baixo': produtos.filter(estoque__lte=5, ativo=True),
			'total_pedidos': pedidos.values('pedido_id').distinct().count(),
			'total_vendido': total_vendido,
			'ultimos_pedidos': pedidos.order_by('-pedido__data')[:5],
			'status_labels': [label for value, label in PedidoFornecedor.Status.choices],
			'status_values': [
				status_counts.get(value, 0)
				for value, label in PedidoFornecedor.Status.choices
			],
		},
	)


@staff_member_required(login_url='/login/')
def administrador_dashboard(request):
	vendas = PedidoItem.objects.filter(
		pedido_fornecedor__status__in=STATUS_COM_VENDA,
	).aggregate(total=Sum('subtotal'))['total'] or 0
	return render(
		request,
		'dashboard/administrador.html',
		{
			'total_usuarios': User.objects.count(),
			'total_agricultores': Perfil.objects.filter(tipo=Perfil.Tipo.AGRICULTOR).count(),
			'total_fornecedores': Perfil.objects.filter(tipo=Perfil.Tipo.FORNECEDOR).count(),
			'total_produtos': Produto.objects.count(),
			'total_pedidos': Pedido.objects.count(),
			'total_vendas': vendas,
			'ranking': ranking_mais_vendidos(10),
		},
	)
