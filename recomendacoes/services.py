from django.db.models import IntegerField, Q, Sum, Value
from django.db.models.functions import Coalesce

from pedidos.models import PedidoFornecedor, PedidoItem
from produtos.models import Categoria, Produto


STATUS_COM_VENDA = [
    PedidoFornecedor.Status.PENDENTE,
    PedidoFornecedor.Status.CONFIRMADO,
    PedidoFornecedor.Status.PREPARANDO,
    PedidoFornecedor.Status.ENVIADO,
    PedidoFornecedor.Status.ENTREGUE,
]

CATEGORIAS_RELACIONADAS = {
    'semente': ('fertilizante', 'defensivo'),
    'fertilizante': ('semente', 'defensivo'),
    'defensivo': ('semente', 'fertilizante'),
    'ferramenta': ('equipamento',),
    'equipamento': ('ferramenta',),
}


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
                output_field=IntegerField(),
            )
        )
    )


def ranking_mais_vendidos(limite=10):
    return produtos_com_vendas().order_by('-total_vendido', 'nome')[:limite]


def produtos_recomendados(usuario, limite=8):
    historico = PedidoItem.objects.filter(
        pedido_fornecedor__pedido__usuario=usuario,
        pedido_fornecedor__status__in=STATUS_COM_VENDA,
    )
    categorias_compradas = set(historico.values_list('produto__categoria_id', flat=True))
    produtos_comprados = set(historico.values_list('produto_id', flat=True))

    if not categorias_compradas:
        return ranking_mais_vendidos(limite), False

    nomes_categorias = Categoria.objects.filter(pk__in=categorias_compradas).values_list('nome', flat=True)
    termos_relacionados = set()
    for nome in nomes_categorias:
        nome_normalizado = nome.lower()
        for termo, relacionados in CATEGORIAS_RELACIONADAS.items():
            if termo in nome_normalizado:
                termos_relacionados.update(relacionados)

    categorias_relacionadas = Categoria.objects.filter(
        ativa=True,
        pk__in=categorias_compradas,
    )
    for termo in termos_relacionados:
        categorias_relacionadas = categorias_relacionadas | Categoria.objects.filter(
            ativa=True,
            nome__icontains=termo,
        )

    recomendados = produtos_com_vendas().filter(
        categoria__in=categorias_relacionadas,
        estoque__gt=0,
    ).exclude(pk__in=produtos_comprados).order_by('-total_vendido', 'preco', 'nome')
    return recomendados[:limite], True


def melhores_precos(limite=6):
    produtos = produtos_com_vendas().filter(estoque__gt=0).order_by('categoria_id', 'preco', 'nome')
    encontrados = []
    categorias_vistas = set()
    for produto in produtos:
        if produto.categoria_id in categorias_vistas:
            continue
        categorias_vistas.add(produto.categoria_id)
        encontrados.append(produto)
        if len(encontrados) == limite:
            break
    return encontrados
