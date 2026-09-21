# AgroConecta

Marketplace Django de insumos agricolas para conectar pequenos agricultores a fornecedores.

## Requisitos

- Python 3.13+
- Ambiente virtual Python
- SQLite para desenvolvimento ou PostgreSQL para producao

## Instalacao

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/`.

## Contas de teste

O comando `seed_data` cria contas demonstrativas com a senha informada em `--password` ou, por padrao, `AgroConecta#2026`:

- Agricultor: `agricultor@agroconecta.local`
- Fornecedor: `fornecedor.verde@agroconecta.local`
- Fornecedor: `fornecedor.campo@agroconecta.local`
- Administrador: `admin@agroconecta.local`

Nenhum pedido e criado automaticamente.

## Comandos uteis

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py collectstatic --noinput
```

## Estrutura

- `contas/`: autenticacao, perfis e permissoes.
- `produtos/`: categorias, produtos e catalogo.
- `vendedores/`: empresas fornecedoras.
- `carrinho/`: carrinho persistido e validacao de estoque.
- `pedidos/`: checkout, pedidos e status.
- `recomendacoes/`: ranking e recomendacoes baseadas em compras.
- `dashboard/`: paineis de agricultor, fornecedor e administrador.
- `templates/`: templates Django responsivos.
- `static/`: CSS, JavaScript e imagens.

## PostgreSQL

Para trocar o SQLite, configure no ambiente as variaveis `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` e `DB_PORT`, usando o exemplo em `.env.example`, e execute as migrations novamente.
