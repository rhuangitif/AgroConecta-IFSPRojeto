from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm
from django.db import transaction

from vendedores.models import Vendedor

from .models import Perfil

User = get_user_model()


class BootstrapFieldsMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', 'form-select')
            else:
                field.widget.attrs.setdefault('class', 'form-control')


class CadastroForm(BootstrapFieldsMixin, UserCreationForm):
    username = forms.EmailField(label='Email')
    first_name = forms.CharField(label='Nome', max_length=150)
    tipo = forms.ChoiceField(label='Tipo de conta', choices=Perfil.Tipo.choices)
    telefone = forms.CharField(label='Telefone', max_length=20)
    cidade = forms.CharField(label='Cidade', max_length=100)
    estado = forms.CharField(label='Estado', max_length=2)
    empresa = forms.CharField(label='Nome da empresa', max_length=150, required=False)
    cnpj = forms.CharField(label='CNPJ', max_length=18, required=False)
    endereco = forms.CharField(label='Endereco', max_length=255, required=False)
    descricao = forms.CharField(label='Descricao', widget=forms.Textarea, required=False)

    class Meta:
        model = User
        fields = (
            'username',
            'first_name',
            'tipo',
            'telefone',
            'cidade',
            'estado',
            'empresa',
            'cnpj',
            'endereco',
            'descricao',
            'password1',
            'password2',
        )

    def clean_username(self):
        email = self.cleaned_data['username'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ja existe uma conta com este email.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('tipo') == Perfil.Tipo.FORNECEDOR:
            for field in ('empresa', 'cnpj', 'endereco'):
                if not cleaned_data.get(field):
                    self.add_error(field, 'Este campo e obrigatorio para fornecedores.')
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data['username']
        user.username = email
        user.email = email
        if not commit:
            return user

        user.save()
        tipo = self.cleaned_data['tipo']
        Perfil.objects.create(
            usuario=user,
            tipo=tipo,
            telefone=self.cleaned_data['telefone'],
            cidade=self.cleaned_data['cidade'],
            estado=self.cleaned_data['estado'].upper(),
        )
        if tipo == Perfil.Tipo.FORNECEDOR:
            Vendedor.objects.create(
                usuario=user,
                empresa=self.cleaned_data['empresa'],
                cnpj=self.cleaned_data['cnpj'],
                email=email,
                telefone=self.cleaned_data['telefone'],
                endereco=self.cleaned_data['endereco'],
                cidade=self.cleaned_data['cidade'],
                estado=self.cleaned_data['estado'].upper(),
                descricao=self.cleaned_data.get('descricao', ''),
            )
        return user


class LoginForm(BootstrapFieldsMixin, AuthenticationForm):
    username = forms.EmailField(label='Email')


class UsuarioForm(BootstrapFieldsMixin, UserChangeForm):
    password = None

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Ja existe uma conta com este email.')
        return email


class PerfilForm(BootstrapFieldsMixin, forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ('telefone', 'cidade', 'estado')

    def clean_estado(self):
        return self.cleaned_data['estado'].upper()


class VendedorForm(BootstrapFieldsMixin, forms.ModelForm):
    class Meta:
        model = Vendedor
        fields = ('empresa', 'cnpj', 'telefone', 'endereco', 'cidade', 'estado', 'descricao')

    def clean_estado(self):
        return self.cleaned_data['estado'].upper()
