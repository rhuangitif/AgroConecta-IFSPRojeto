from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import Perfil


def perfil_required(tipo):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            perfil = getattr(request.user, 'perfil', None)
            if not perfil or perfil.tipo != tipo:
                messages.error(request, 'Você não tem permissão para acessar esta área.')
                return redirect('contas:perfil')
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


fornecedor_required = perfil_required(Perfil.Tipo.FORNECEDOR)
agricultor_required = perfil_required(Perfil.Tipo.AGRICULTOR)
