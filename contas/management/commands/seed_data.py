from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from contas.models import Perfil
from produtos.models import Categoria, Produto
from vendedores.models import Vendedor

User = get_user_model()


class Command(BaseCommand):
    help = 'Cria categorias, usuarios, fornecedores e produtos de demonstracao.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default='AgroConecta#2026',
            help='Senha das contas de teste criadas pelo comando.',
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
            cidade='Maceio',
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
            cidade='Maceio',
            estado='AL',
            descricao='Insumos para pequenos produtores.',
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
            descricao='Solucoes para cultivo e manejo.',
        )
        administrador = self._criar_administrador(password)
        produtos = self._criar_produtos(categorias, fornecedor_a, fornecedor_b)

        self.stdout.write(self.style.SUCCESS('Seed concluido com sucesso.'))
        self.stdout.write(f'Categorias: {len(categorias)}')
        self.stdout.write('Usuarios: agricultor@agroconecta.local, fornecedor.verde@agroconecta.local, fornecedor.campo@agroconecta.local')
        self.stdout.write(f'Administrador: {administrador.username}')
        self.stdout.write(f'Produtos criados ou atualizados: {produtos}')
        self.stdout.write('Pedidos criados: 0')
        self.stdout.write(f'Senha das contas de teste: {password}')

    def _criar_categorias(self):
        nomes = (
            'Sementes',
            'Fertilizantes',
            'Defensivos',
            'Ferramentas',
            'Equipamentos',
            'Outros',
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
        produtos = (
            ('Semente de Milho', 'Sementes', fornecedor_a, 'Sementes selecionadas de milho para cultivo.', '45.00', 80, 'saco'),
            ('Semente de Milho', 'Sementes', fornecedor_b, 'Sementes de milho para diferentes ciclos.', '42.50', 55, 'saco'),
            ('Fertilizante NPK', 'Fertilizantes', fornecedor_a, 'Formula NPK para reforco nutricional.', '125.90', 30, 'saco'),
            ('Fertilizante Organico', 'Fertilizantes', fornecedor_b, 'Fertilizante organico para manejo do solo.', '98.00', 24, 'saco'),
            ('Pulverizador Manual', 'Equipamentos', fornecedor_a, 'Pulverizador manual para pequenas areas.', '189.90', 12, 'un'),
            ('Enxada Reforcada', 'Ferramentas', fornecedor_b, 'Ferramenta reforcada para preparo do solo.', '79.90', 18, 'un'),
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
