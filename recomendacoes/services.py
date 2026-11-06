from django.db.models import Case, DecimalField, F, IntegerField, Q, Sum, Value, When
from django.db.models.functions import Coalesce

from pedidos.models import PedidoFornecedor, PedidoItem
from produtos.models import Produto


STATUS_COM_VENDA = [
    PedidoFornecedor.Status.PENDENTE,
    PedidoFornecedor.Status.CONFIRMADO,
    PedidoFornecedor.Status.PREPARANDO,
    PedidoFornecedor.Status.ENVIADO,
    PedidoFornecedor.Status.ENTREGUE,
]

FONTE_HISTORICO = 'historico'
FONTE_MAIS_VENDIDOS = 'mais_vendidos'
FONTE_SEM_VENDAS = 'sem_vendas'
FONTE_VAZIA = 'vazia'


def produtos_com_vendas():
    return (
        Produto.objects.filter(ativo=True)
        .select_related('categoria', 'fornecedor')
        .annotate(
            total_vendido=Coalesce(
                Sum(
                    'itens_pedido__quantidade',
                    filter=Q(itens_pedido__pedido_fornecedor__status__in=STATUS_COM_VENDA),
                ),
                Value(0),
                output_field=DecimalField(max_digits=20, decimal_places=3),
            )
        )
    )


def ranking_mais_vendidos(limite=10):
    return produtos_com_vendas().order_by('-total_vendido', 'nome')[:limite]


def produtos_recomendados(usuario, limite=8):
    """Recommend in-stock products using purchase-category demand and real sales.

    Inputs are the user's non-cancelled order items and active products with
    available stock. Categories are ranked by the total quantity the user
    bought, descending, with category ID as the tie-breaker. Previously bought
    products and products with no non-cancelled sales are excluded. Remaining
    products are ordered by category rank, sales quantity descending, unit
    price ascending, then product ID ascending. If this produces no results,
    use best sellers (sales, price, ID) as an explicitly labeled fallback;
    when no products have sales yet, fall back to available catalog products.

    Returns the products, whether the user has qualifying history, and a
    source key for the UI to label any fallback.
    """
    historico = PedidoItem.objects.filter(
        pedido_fornecedor__pedido__usuario=usuario,
        pedido_fornecedor__status__in=STATUS_COM_VENDA,
    )
    produtos_comprados = set(historico.values_list('produto_id', flat=True))
    categorias_compradas = list(
        historico.values('produto__categoria_id')
        .annotate(quantidade_comprada=Sum('quantidade'))
        .order_by('-quantidade_comprada', 'produto__categoria_id')
    )
    tem_historico = bool(categorias_compradas)

    if categorias_compradas:
        prioridades = {
            categoria['produto__categoria_id']: prioridade
            for prioridade, categoria in enumerate(categorias_compradas)
        }
        recomendados = (
            produtos_com_vendas()
            .filter(
                categoria_id__in=prioridades,
                estoque__gt=0,
                total_vendido__gt=0,
            )
            .exclude(pk__in=produtos_comprados)
            .annotate(
                prioridade_categoria=Case(
                    *(
                        When(categoria_id=categoria_id, then=Value(prioridade))
                        for categoria_id, prioridade in prioridades.items()
                    ),
                    output_field=IntegerField(),
                )
            )
            .order_by('prioridade_categoria', '-total_vendido', 'preco', 'pk')
        )

        if recomendados.exists():
            return recomendados[:limite], True, FONTE_HISTORICO

    mais_vendidos = (
        produtos_com_vendas()
        .filter(estoque__gt=0, total_vendido__gt=0)
        .exclude(pk__in=produtos_comprados)
        .order_by('-total_vendido', 'preco', 'pk')
    )
    if mais_vendidos.exists():
        return mais_vendidos[:limite], tem_historico, FONTE_MAIS_VENDIDOS

    catalogo = (
        produtos_com_vendas()
        .filter(estoque__gt=0)
        .exclude(pk__in=produtos_comprados)
        .order_by('preco', 'pk')
    )
    if catalogo.exists():
        return catalogo[:limite], tem_historico, FONTE_SEM_VENDAS
    return catalogo.none(), tem_historico, FONTE_VAZIA


def melhores_precos(limite=6):
    """Return one lowest-price item per equivalent category and measure unit.

    Product price is already specified per its listed unit. Products are
    comparable only when both category and unit match, so the cheapest product
    wins each group; equal prices are resolved by product ID. Winners are
    returned by price-per-unit ascending, then category, unit, and product ID.
    """
    produtos = (
        produtos_com_vendas()
        .filter(estoque__gt=0)
        .annotate(preco_por_unidade=F('preco'))
        .order_by('categoria_id', 'unidade_medida', 'preco_por_unidade', 'pk')
    )
    encontrados = []
    grupos_vistos = set()
    for produto in produtos:
        grupo = (produto.categoria_id, produto.unidade_medida)
        if grupo in grupos_vistos:
            continue
        grupos_vistos.add(grupo)
        encontrados.append(produto)
    return sorted(
        encontrados,
        key=lambda produto: (
            produto.preco_por_unidade,
            produto.categoria_id,
            produto.unidade_medida,
            produto.pk,
        ),
    )[:limite]
