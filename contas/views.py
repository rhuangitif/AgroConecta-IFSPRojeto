from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from .forms import CadastroForm, LoginForm, PerfilForm, UsuarioForm, VendedorForm
from .models import Perfil


def cadastro(request):
	if request.user.is_authenticated:
		return redirect('contas:perfil')

	form = CadastroForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		user = form.save()
		login(request, user)
		messages.success(request, 'Conta criada com sucesso.')
		return redirect('contas:perfil')
	return render(request, 'contas/cadastro.html', {'form': form})


def login_view(request):
	if request.user.is_authenticated:
		return redirect('contas:perfil')

	form = LoginForm(request, data=request.POST or None)
	if request.method == 'POST' and form.is_valid():
		login(request, form.get_user())
		next_url = request.POST.get('next') or request.GET.get('next')
		if next_url and url_has_allowed_host_and_scheme(
			next_url,
			allowed_hosts={request.get_host()},
			require_https=request.is_secure(),
		):
			return redirect(next_url)
		return redirect('contas:perfil')
	return render(request, 'contas/login.html', {'form': form, 'next': request.GET.get('next', '')})


@require_POST
def logout_view(request):
	logout(request)
	messages.success(request, 'Você saiu da sua conta.')
	return redirect('contas:login')


@login_required
def perfil(request):
	perfil_usuario = getattr(request.user, 'perfil', None)
	vendedor = getattr(request.user, 'vendedor', None)
	return render(
		request,
		'contas/perfil.html',
		{'perfil_usuario': perfil_usuario, 'vendedor': vendedor},
	)


@login_required
@require_http_methods(['GET', 'POST'])
def editar_perfil(request):
	perfil_usuario = getattr(request.user, 'perfil', None)
	vendedor = getattr(request.user, 'vendedor', None)
	user_form = UsuarioForm(request.POST or None, instance=request.user)
	perfil_instance = perfil_usuario or Perfil(usuario=request.user)
	perfil_form = PerfilForm(request.POST or None, instance=perfil_instance)
	vendedor_form = None
	if perfil_usuario and perfil_usuario.tipo == Perfil.Tipo.FORNECEDOR and vendedor:
		vendedor_form = VendedorForm(request.POST or None, instance=vendedor)

	if request.method == 'POST' and user_form.is_valid() and perfil_form.is_valid():
		if vendedor_form and not vendedor_form.is_valid():
			return render(
				request,
				'contas/editar_perfil.html',
				{
					'user_form': user_form,
					'perfil_form': perfil_form,
					'vendedor_form': vendedor_form,
				},
			)
		with transaction.atomic():
			user_form.save()
			perfil_form.save()
			if vendedor_form:
				vendedor_form.save()
		messages.success(request, 'Perfil atualizado com sucesso.')
		return redirect('contas:perfil')

	return render(
		request,
		'contas/editar_perfil.html',
		{
			'user_form': user_form,
			'perfil_form': perfil_form,
			'vendedor_form': vendedor_form,
		},
	)
