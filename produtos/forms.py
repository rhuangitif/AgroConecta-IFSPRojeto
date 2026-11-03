from django import forms
from django.core.exceptions import ValidationError

from contas.forms import BootstrapFieldsMixin

from .models import Categoria, Produto, validar_quantidade_unidade


class ProdutoForm(BootstrapFieldsMixin, forms.ModelForm):
    class Meta:
        model = Produto
        fields = (
            'nome',
            'descricao',
            'categoria',
            'preco',
            'estoque',
            'unidade_medida',
            'imagem',
            'ativo',
        )
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 5}),
            'preco': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'estoque': forms.NumberInput(attrs={'min': '0', 'step': '0.001'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        estoque = cleaned_data.get('estoque')
        unidade_medida = cleaned_data.get('unidade_medida')
        if estoque is not None and unidade_medida:
            try:
                validar_quantidade_unidade(
                    estoque,
                    unidade_medida,
                    permitir_zero=True,
                )
            except ValidationError as erro:
                self.add_error('estoque', erro)
        return cleaned_data


class CatalogoFiltroForm(BootstrapFieldsMixin, forms.Form):
    busca = forms.CharField(label='Buscar', required=False)
    categoria = forms.ModelChoiceField(
        label='Categoria', queryset=Categoria.objects.filter(ativa=True), required=False,
    )
    fornecedor = forms.ChoiceField(label='Fornecedor', required=False)
    preco_min = forms.DecimalField(label='Preco minimo', min_value=0, required=False)
    preco_max = forms.DecimalField(label='Preco maximo', min_value=0, required=False)
    disponibilidade = forms.ChoiceField(
        label='Disponibilidade',
        required=False,
        choices=(('', 'Todos'), ('disponivel', 'Disponiveis'), ('indisponivel', 'Indisponiveis')),
    )
    ordem = forms.ChoiceField(
        label='Ordenar por',
        required=False,
        choices=(
            ('recente', 'Mais recentes'),
            ('menor_preco', 'Menor preco'),
            ('maior_preco', 'Maior preco'),
            ('mais_vendidos', 'Mais vendidos'),
            ('nome', 'Nome'),
        ),
        initial='recente',
    )

    def __init__(self, *args, **kwargs):
        fornecedores = kwargs.pop('fornecedores', ())
        super().__init__(*args, **kwargs)
        self.fields['fornecedor'].choices = [('', 'Todos')] + [
            (fornecedor.pk, fornecedor.empresa) for fornecedor in fornecedores
        ]
