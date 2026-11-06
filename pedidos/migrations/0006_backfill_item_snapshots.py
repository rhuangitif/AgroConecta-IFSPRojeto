from django.db import migrations


def preencher_snapshots_pendentes(apps, schema_editor):
    PedidoItem = apps.get_model('pedidos', 'PedidoItem')
    db_alias = schema_editor.connection.alias
    itens = list(
        PedidoItem.objects.using(db_alias)
        .filter(nome_produto='')
        .select_related('produto')
    )
    for item in itens:
        item.nome_produto = item.produto.nome
        item.unidade_medida = item.produto.unidade_medida
    if itens:
        PedidoItem.objects.using(db_alias).bulk_update(
            itens,
            ('nome_produto', 'unidade_medida'),
        )


class Migration(migrations.Migration):

    dependencies = [
        ('pedidos', '0005_alter_pedido_options_rename_data_pedido_criado_em_and_more'),
    ]

    operations = [
        migrations.RunPython(
            preencher_snapshots_pendentes,
            migrations.RunPython.noop,
        ),
    ]
