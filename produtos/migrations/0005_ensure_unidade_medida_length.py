from django.db import migrations, models


UNIT_CHOICES = [
    ('un', 'Unidade'),
    ('kg', 'Quilograma'),
    ('g', 'Grama'),
    ('saco', 'Saco'),
    ('litro', 'Litro'),
    ('ml', 'Mililitro'),
    ('tonelada', 'Tonelada'),
    ('caixa', 'Caixa'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0004_normalize_unidade_medida'),
    ]

    operations = [
        migrations.AlterField(
            model_name='produto',
            name='unidade_medida',
            field=models.CharField(
                choices=UNIT_CHOICES,
                default='un',
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name='produto',
            name='unidade_medida',
            field=models.CharField(
                choices=UNIT_CHOICES,
                default='un',
                max_length=10,
            ),
        ),
    ]
