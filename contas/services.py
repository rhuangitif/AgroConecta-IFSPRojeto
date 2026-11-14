import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from carrinho.models import Carrinho
from pedidos.models import HistoricoStatus, Pedido
from produtos.models import Produto
from vendedores.models import Vendedor

from .models import Perfil

User = get_user_model()


def _delete_file_after_commit(field_file):
    if field_file and field_file.name:
        storage = field_file.storage
        name = field_file.name
        transaction.on_commit(lambda: storage.delete(name))


@transaction.atomic
def anonimizar_conta(user):
    usuario = User.objects.select_for_update().get(pk=user.pk)
    perfil = Perfil.objects.select_for_update().filter(usuario=usuario).first()
    if perfil and perfil.anonimizado_em:
        raise ValidationError('Esta conta já foi anonimizada.')

    agora = timezone.now()
    if perfil is None:
        perfil = Perfil(usuario=usuario)
    perfil.telefone = ''
    perfil.cidade = ''
    perfil.estado = ''
    perfil.anonimizado_em = agora
    perfil.save()

    Pedido.objects.filter(usuario=usuario).update(
        endereco_entrega='',
        cidade_entrega='',
        estado_entrega='',
        observacoes='',
    )
    HistoricoStatus.objects.filter(autor=usuario).update(autor=None)
    Carrinho.objects.filter(usuario=usuario).delete()

    vendedor = (
        Vendedor.objects.select_for_update()
        .filter(usuario=usuario)
        .first()
    )
    if vendedor:
        _delete_file_after_commit(vendedor.logo)
        vendedor.empresa = f'Fornecedor anonimizado {vendedor.pk}'
        vendedor.cnpj = None
        vendedor.logo = None
        vendedor.endereco = ''
        vendedor.cidade_sede = ''
        vendedor.uf_sede = ''
        vendedor.descricao = ''
        vendedor.ativo = False
        vendedor.save(update_fields=(
            'empresa',
            'cnpj',
            'logo',
            'endereco',
            'cidade_sede',
            'uf_sede',
            'descricao',
            'ativo',
            'atualizado_em',
        ))

        produtos = (
            Produto.objects.select_for_update()
            .filter(fornecedor=vendedor)
            .only('pk', 'imagem')
        )
        for produto in produtos:
            _delete_file_after_commit(produto.imagem)
            produto.imagem = ''
            produto.ativo = False
            produto.atualizado_em = agora
            produto.save(update_fields=('imagem', 'ativo', 'atualizado_em'))

    identificador_anonimo = f'anonimizado-{usuario.pk}-{uuid.uuid4().hex[:12]}'
    usuario.username = identificador_anonimo
    usuario.email = f'{identificador_anonimo}@example.invalid'
    usuario.first_name = ''
    usuario.last_name = ''
    usuario.last_login = None
    usuario.is_active = False
    usuario.is_staff = False
    usuario.is_superuser = False
    usuario.set_unusable_password()
    usuario.save(update_fields=(
        'username',
        'email',
        'first_name',
        'last_name',
        'last_login',
        'is_active',
        'is_staff',
        'is_superuser',
        'password',
    ))
    usuario.groups.clear()
    usuario.user_permissions.clear()
