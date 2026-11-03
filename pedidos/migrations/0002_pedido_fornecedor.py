from django.db import migrations, models
import django.db.models.deletion


def preparar_esquema(apps, schema_editor):
    PedidoFornecedor = apps.get_model('pedidos', 'PedidoFornecedor')
    PedidoItem = apps.get_model('pedidos', 'PedidoItem')
    connection = schema_editor.connection
    tables = set(connection.introspection.table_names())

    if PedidoFornecedor._meta.db_table not in tables:
        schema_editor.create_model(PedidoFornecedor)

    item_columns = {
        column.name
        for column in connection.introspection.get_table_description(
            connection.cursor(),
            PedidoItem._meta.db_table,
        )
    }
    field = PedidoItem._meta.get_field('pedido_fornecedor')
    if field.column not in item_columns:
        schema_editor.add_field(PedidoItem, field)


def vincular_itens_a_fornecedores(apps, schema_editor):
    PedidoItem = apps.get_model('pedidos', 'PedidoItem')
    PedidoFornecedor = apps.get_model('pedidos', 'PedidoFornecedor')

    for item in PedidoItem.objects.select_related('pedido', 'produto').all().iterator():
        pedido_id = item.pedido_id
        fornecedor_id = item.produto.fornecedor_id
        atual = PedidoFornecedor.objects.filter(
            pk=item.pedido_fornecedor_id,
            pedido_id=pedido_id,
            fornecedor_id=fornecedor_id,
        ).first()
        if atual:
            continue

        pedido_fornecedor, _ = PedidoFornecedor.objects.get_or_create(
            pedido_id=pedido_id,
            fornecedor_id=fornecedor_id,
            defaults={'status': item.pedido.status},
        )
        PedidoItem.objects.filter(pk=item.pk).update(
            pedido_fornecedor_id=pedido_fornecedor.pk,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('pedidos', '0001_initial'),
        ('vendedores', '0002_alter_vendedor_options_vendedor_cidade_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='PedidoFornecedor',
                    fields=[
                        ('id', models.BigAutoField(
                            auto_created=True,
                            primary_key=True,
                            serialize=False,
                            verbose_name='ID',
                        )),
                        ('status', models.CharField(
                            choices=[
                                ('pendente', 'Pendente'),
                                ('confirmado', 'Confirmado'),
                                ('preparando', 'Preparando'),
                                ('enviado', 'Enviado'),
                                ('entregue', 'Entregue'),
                                ('cancelado', 'Cancelado'),
                            ],
                            default='pendente',
                            max_length=20,
                        )),
                        ('criado_em', models.DateTimeField(auto_now_add=True)),
                        ('atualizado_em', models.DateTimeField(auto_now=True)),
                        ('fornecedor', models.ForeignKey(
                            on_delete=django.db.models.deletion.PROTECT,
                            related_name='pedidos',
                            to='vendedores.vendedor',
                        )),
                        ('pedido', models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='fornecedores',
                            to='pedidos.pedido',
                        )),
                    ],
                    options={
                        'ordering': ('-criado_em',),
                        'constraints': [
                            models.UniqueConstraint(
                                fields=('pedido', 'fornecedor'),
                                name='pedido_fornecedor_unico',
                            ),
                        ],
                    },
                ),
                migrations.AddField(
                    model_name='pedidoitem',
                    name='pedido_fornecedor',
                    field=models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='itens',
                        to='pedidos.pedidofornecedor',
                    ),
                ),
            ],
        ),
        migrations.RunPython(preparar_esquema, migrations.RunPython.noop),
        migrations.RunPython(vincular_itens_a_fornecedores, migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='pedidoitem',
                    name='pedido_fornecedor',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='itens',
                        to='pedidos.pedidofornecedor',
                    ),
                ),
                migrations.RenameField(
                    model_name='pedidoitem',
                    old_name='pedido',
                    new_name='pedido_legado',
                ),
                migrations.AlterField(
                    model_name='pedidoitem',
                    name='pedido_legado',
                    field=models.ForeignKey(
                        db_column='pedido_id',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='itens_legados',
                        to='pedidos.pedido',
                    ),
                ),
                migrations.RenameField(
                    model_name='pedido',
                    old_name='status',
                    new_name='status_legado',
                ),
                migrations.AlterField(
                    model_name='pedido',
                    name='status_legado',
                    field=models.CharField(
                        choices=[
                            ('pendente', 'Pendente'),
                            ('confirmado', 'Confirmado'),
                            ('preparando', 'Preparando'),
                            ('enviado', 'Enviado'),
                            ('entregue', 'Entregue'),
                            ('cancelado', 'Cancelado'),
                        ],
                        db_column='status',
                        default='pendente',
                        editable=False,
                        max_length=20,
                    ),
                ),
            ],
        ),
    ]
