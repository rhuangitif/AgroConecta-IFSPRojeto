from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from contas.models import Perfil
from produtos.models import Categoria, Produto
from vendedores.models import Vendedor

User = get_user_model()


class Command(BaseCommand):
    help = 'Cria categorias, usuários, fornecedores e produtos de demonstração.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default='AgroConecta#2026',
            help='Senha das contas demonstrativas criadas pelo comando.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options['password']
        categorias = self._criar_categorias()
        agricultor = self._criar_usuario(
            email='agricultor@agroconecta.local',
            nome='Agricultor Demo',
            password=password,
            telefone='82999990000',
            cidade='Maceió',
            estado='AL',
        )
        fornecedor_a = self._criar_fornecedor(
            email='fornecedor.verde@agroconecta.local',
            nome='Fornecedor Verde Demo',
            password=password,
            empresa='Agro Verde Insumos',
            cnpj='12.345.678/0001-95',
            telefone='8233334444',
            endereco='Av. das Plantas, 100',
            cidade='Maceió',
            estado='AL',
            descricao='Insumos agrícolas selecionados para pequenos produtores.',
        )
        fornecedor_b = self._criar_fornecedor(
            email='fornecedor.campo@agroconecta.local',
            nome='Fornecedor Campo Demo',
            password=password,
            empresa='Campo Forte Distribuidora',
            cnpj='12.345.678/0002-76',
            telefone='8233335555',
            endereco='Rua da Colheita, 200',
            cidade='Arapiraca',
            estado='AL',
            descricao='Soluções para cultivo, nutrição e manejo agrícola.',
        )
        administrador = self._criar_administrador(password)
        produtos = self._criar_produtos(categorias, fornecedor_a, fornecedor_b)

        self.stdout.write(self.style.SUCCESS('Dados demonstrativos atualizados com sucesso.'))
        self.stdout.write(f'Categorias: {len(categorias)}')
        self.stdout.write('Usuários: agricultor@agroconecta.local, fornecedor.verde@agroconecta.local, fornecedor.campo@agroconecta.local')
        self.stdout.write(f'Administrador: {administrador.username}')
        self.stdout.write(f'Produtos criados: {produtos}')
        self.stdout.write('Pedidos criados: 0')
        self.stdout.write(f'Senha das contas demonstrativas: {password}')

    def _criar_categorias(self):
        nomes = (
            'Sementes',
            'Fertilizantes',
            'Defensivos',
            'Ferramentas',
            'Equipamentos',
            'Outros',
            'Rações',
        )
        categorias = []
        for nome in nomes:
            categoria, _ = Categoria.objects.update_or_create(
                slug=slugify(nome),
                defaults={'nome': nome, 'ativa': True},
            )
            categorias.append(categoria)
        return categorias

    def _criar_usuario(self, email, nome, password, telefone, cidade, estado):
        user, created = User.objects.get_or_create(
            username=email,
            defaults={'email': email, 'first_name': nome},
        )
        if created:
            user.set_password(password)
        user.email = email
        user.first_name = nome
        user.save(update_fields=['email', 'first_name', 'password'] if created else ['email', 'first_name'])
        Perfil.objects.update_or_create(
            usuario=user,
            defaults={
                'telefone': telefone,
                'cidade': cidade,
                'estado': estado,
            },
        )
        return user

    def _criar_fornecedor(self, email, nome, password, **dados):
        user = self._criar_usuario(
            email=email,
            nome=nome,
            password=password,
            telefone=dados['telefone'],
            cidade=dados['cidade'],
            estado=dados['estado'],
        )
        Vendedor.objects.update_or_create(
            usuario=user,
            defaults={
                'empresa': dados['empresa'],
                'cnpj': dados['cnpj'],
                'endereco': dados['endereco'],
                'cidade_sede': dados['cidade'],
                'uf_sede': dados['estado'],
                'descricao': dados['descricao'],
                'ativo': True,
            },
        )
        return Vendedor.objects.get(usuario=user)

    def _criar_administrador(self, password):
        user, created = User.objects.get_or_create(
            username='admin@agroconecta.local',
            defaults={
                'email': 'admin@agroconecta.local',
                'first_name': 'Administrador Demo',
                'is_staff': True,
                'is_superuser': True,
            },
        )
        if created:
            user.set_password(password)
        user.email = 'admin@agroconecta.local'
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=['email', 'is_staff', 'is_superuser', 'password'] if created else ['email', 'is_staff', 'is_superuser'])
        return user

    def _criar_produtos(self, categorias, fornecedor_a, fornecedor_b):
        por_nome = {categoria.nome: categoria for categoria in categorias}
        for fornecedor in (fornecedor_a, fornecedor_b):
            Produto.objects.filter(
                fornecedor=fornecedor,
                nome='Fertilizante Organico',
            ).update(nome='Fertilizante Orgânico')
            Produto.objects.filter(
                fornecedor=fornecedor,
                nome='Enxada Reforcada',
            ).update(nome='Enxada Reforçada')
        produtos = (
            ('Semente de Milho', 'Sementes', fornecedor_a, 'Sementes híbridas de milho para plantio comercial, vendidas em saco.', '289.90', 18, 'saco'),
            ('Semente de Milho', 'Sementes', fornecedor_b, 'Sementes selecionadas de milho para diferentes ciclos de cultivo.', '249.90', 24, 'saco'),
            ('Fertilizante NPK', 'Fertilizantes', fornecedor_a, 'Adubo granulado NPK 10-10-10, embalagem de 50 kg.', '189.90', 35, 'saco'),
            ('Fertilizante Orgânico', 'Fertilizantes', fornecedor_b, 'Composto orgânico para preparo e melhoria do solo, saco de 20 kg.', '49.90', 42, 'saco'),
            ('Ração para aves de postura', 'Rações', fornecedor_b, 'Ração completa para aves poedeiras, embalagem de 20 kg.', '86.90', 38, 'saco'),
            ('Defensivo biológico para lagartas', 'Defensivos', fornecedor_a, 'Produto biológico para manejo de lagartas, frasco de 1 litro.', '74.90', 16, 'litro'),
            ('Óleo mineral agrícola', 'Defensivos', fornecedor_b, 'Óleo mineral para uso agrícola, embalagem de 1 litro.', '39.90', 28, 'litro'),
            ('Pulverizador Manual', 'Equipamentos', fornecedor_a, 'Pulverizador manual de 16 litros para aplicação em pequenas áreas.', '189.90', 12, 'un'),
            ('Enxada Reforçada', 'Ferramentas', fornecedor_b, 'Enxada de aço reforçado para preparo manual do solo.', '79.90', 18, 'un'),
        )
        criados = 0
        for nome, categoria, fornecedor, descricao, preco, estoque, unidade in produtos:
            _, created = Produto.objects.update_or_create(
                nome=nome,
                fornecedor=fornecedor,
                defaults={
                    'descricao': descricao,
                    'categoria': por_nome[categoria],
                    'preco': preco,
                    'estoque': estoque,
                    'unidade_medida': unidade,
                    'ativo': True,
                },
            )
            criados += int(created)
        return criados
