from django.db import migrations
from django.db import models


UNIT_ALIASES = {
    'un': 'un',
    'unidade': 'un',
    'unidades': 'un',
    'unit': 'un',
    'kg': 'kg',
    'quilo': 'kg',
    'quilos': 'kg',
    'g': 'g',
    'gr': 'g',
    'grama': 'g',
    'gramas': 'g',
    'sc': 'saco',
    'saco': 'saco',
    'sacos': 'saco',
    'l': 'litro',
    'lt': 'litro',
    'litro': 'litro',
    'litros': 'litro',
    'ml': 'ml',
    'ton': 'tonelada',
    't': 'tonelada',
    'tonelada': 'tonelada',
    'toneladas': 'tonelada',
    'cx': 'caixa',
    'caixa': 'caixa',
    'caixas': 'caixa',
}
REVERSE_UNIT_ALIASES = {
    'un': 'unidade',
    'kg': 'kg',
    'g': 'g',
    'saco': 'sc',
    'litro': 'litro',
    'ml': 'ml',
    'tonelada': 'tonelada',
    'caixa': 'caixa',
}


def normalize_existing_units(apps, schema_editor):
    Produto = apps.get_model('produtos', 'Produto')
    database = schema_editor.connection.alias
    unidades = (
        Produto.objects.using(database)
        .values_list('unidade_medida', flat=True)
        .distinct()
    )
    valores_invalidos = []
    for unidade in unidades:
        canonical = UNIT_ALIASES.get((unidade or '').strip().lower())
        if canonical is None:
            valores_invalidos.append(unidade)
        elif unidade != canonical:
            Produto.objects.using(database).filter(
                unidade_medida=unidade,
            ).update(unidade_medida=canonical)

    if valores_invalidos:
        raise RuntimeError(
            'Unidades de produto sem conversao definida: '
            + ', '.join(repr(unidade) for unidade in valores_invalidos)
        )


def restore_legacy_units(apps, schema_editor):
    Produto = apps.get_model('produtos', 'Produto')
    database = schema_editor.connection.alias
    for unidade, legacy in REVERSE_UNIT_ALIASES.items():
        Produto.objects.using(database).filter(
            unidade_medida=unidade,
        ).update(unidade_medida=legacy)


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0003_alter_produto_estoque_alter_produto_unidade_medida'),
    ]

    operations = [
        migrations.AlterField(
            model_name='produto',
            name='unidade_medida',
            field=models.CharField(
                choices=[
                    ('un', 'Unidade'),
                    ('kg', 'Quilograma'),
                    ('g', 'Grama'),
                    ('saco', 'Saco'),
                    ('litro', 'Litro'),
                    ('ml', 'Mililitro'),
                    ('tonelada', 'Tonelada'),
                    ('caixa', 'Caixa'),
                ],
                default='un',
                max_length=30,
            ),
        ),
        migrations.RunPython(normalize_existing_units, restore_legacy_units),
        migrations.AlterField(
            model_name='produto',
            name='unidade_medida',
            field=models.CharField(
                choices=[
                    ('un', 'Unidade'),
                    ('kg', 'Quilograma'),
                    ('g', 'Grama'),
                    ('saco', 'Saco'),
                    ('litro', 'Litro'),
                    ('ml', 'Mililitro'),
                    ('tonelada', 'Tonelada'),
                    ('caixa', 'Caixa'),
                ],
                default='un',
                max_length=10,
            ),
        ),
    ]
