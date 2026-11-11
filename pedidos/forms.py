from django import forms

from contas.forms import BootstrapFieldsMixin

from .models import Pedido


class PedidoForm(BootstrapFieldsMixin, forms.ModelForm):
	endereco_entrega = forms.CharField(label='Endereço de entrega', max_length=255)
	cidade_entrega = forms.CharField(label='Cidade', max_length=100)
	estado_entrega = forms.ChoiceField(
		label='Estado',
		choices=Pedido._meta.get_field('estado_entrega').choices,
	)

	class Meta:
		model = Pedido
		fields = (
			'endereco_entrega',
			'cidade_entrega',
			'estado_entrega',
			'forma_pagamento',
			'observacoes',
		)
		widgets = {
			'observacoes': forms.Textarea(attrs={'rows': 3}),
		}
		labels = {
			'forma_pagamento': 'Forma de pagamento',
			'observacoes': 'Observações',
		}
