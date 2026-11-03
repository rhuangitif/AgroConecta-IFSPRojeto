from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from produtos.models import UNIDADES_INTEIRAS, validar_quantidade_unidade


class QuantidadeForm(forms.Form):
	quantidade = forms.DecimalField(
		max_digits=10,
		decimal_places=3,
		min_value=Decimal('0.001'),
		widget=forms.NumberInput(attrs={'min': '0.001', 'step': '0.001'}),
	)

	def __init__(self, *args, unidade_medida, **kwargs):
		super().__init__(*args, **kwargs)
		if unidade_medida in UNIDADES_INTEIRAS:
			self.fields['quantidade'].widget.attrs.update({'min': '1', 'step': '1'})

		self.unidade_medida = unidade_medida

	def clean_quantidade(self):
		quantidade = self.cleaned_data['quantidade']
		try:
			validar_quantidade_unidade(quantidade, self.unidade_medida)
		except ValidationError as erro:
			raise forms.ValidationError(erro.messages) from erro
		return quantidade
