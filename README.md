# AgroConecta

Marketplace Django de insumos agrícolas que conecta pequenos agricultores a
fornecedores.

## Requisitos e versões verificadas

- Python 3.13 ou superior. Ambiente de referência: **Python 3.13.1**.
- Django **6.1**.
- Banco padrão: SQLite. Ambiente de referência: **SQLite 3.45.3**.
- PostgreSQL pode ser configurado para outros ambientes; esta validação foi
  executada com SQLite.

O comando `python manage.py ambiente_info` informa as versões e o banco
configurado no ambiente em execução. As dependências da aplicação estão em
`requirements.txt`.

## Instalação e execução local

No PowerShell, na pasta do projeto:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/`. O arquivo `.env` usa SQLite por padrão. Para
configurar outro banco, ajuste as variáveis de ambiente conforme `.env.example`
e aplique as migrações nesse banco.

## Dados de demonstração

O comando `seed_data` cria categorias, produtos, contas de agricultor,
fornecedores e administrador. Ele não cria pedidos. Em uma base limpa, a senha
padrão das contas demonstrativas criadas é `AgroConecta#2026`; defina outra
senha ao criar essas contas com:

```powershell
python manage.py seed_data --password "SuaSenhaDeTeste"
```

Contas criadas:

- Agricultor: `agricultor@agroconecta.local`
- Fornecedor: `fornecedor.verde@agroconecta.local`
- Fornecedor: `fornecedor.campo@agroconecta.local`
- Administrador: `admin@agroconecta.local`

Use essas contas apenas em desenvolvimento ou em uma base descartável de teste.
O comando não redefine a senha de contas que já existiam. Não reutilize a senha
padrão em produção.

## Testes e verificações

Execute os comandos na raiz do projeto:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

A suíte cobre transições de status de pedidos, validações de estoque e checkout
concorrente, cálculos e formatação de decimais, recomendações, validação de
CNPJ, permissões de fornecedor e autenticação. Na verificação desta fase,
`python manage.py test` executou **64 testes**, todos aprovados.

Para inspecionar versões, banco e contagens de registros:

```powershell
python manage.py ambiente_info
```

Para preparar os arquivos estáticos:

```powershell
python manage.py collectstatic --noinput
```

## Teste de carga

O cenário usa Locust e percorre catálogo, detalhe de produto, login, adição ao
carrinho e checkout. Antes de executar, use uma base de teste, prepare 20 contas
agricultoras exclusivas com carrinhos vazios e escolha um produto ativo com
estoque suficiente. Cada conta conclui uma jornada, cria um pedido e consome
uma unidade do produto.

Instale o Locust no ambiente virtual:

```powershell
python -m pip install "locust>=2.32,<3"
```

Crie `loadtest\users.csv` com cabeçalho `username,password` e uma linha para
cada conta. Em seguida, inicie o servidor local em um terminal e execute em
outro:

```powershell
$env:LOADTEST_PRODUCT_ID = "123"
python -m locust -f loadtest\locustfile.py --headless --host http://127.0.0.1:8000 --users 20 --spawn-rate 20 --run-time 2m --csv loadtest\resultados
```

Substitua `123` pelo ID do produto escolhido. O Locust grava estatísticas em
arquivos CSV; registre a média, o percentil 95 (P95) e a taxa de erro a partir
dos valores medidos. Não há resultados de desempenho pré-calculados neste
repositório. Como o teste cria pedidos e consome estoque, reponha os dados de
teste antes de executá-lo novamente. Consulte [loadtest/README.md](./loadtest/README.md)
para detalhes de preparação e leitura dos resultados.

## Servidor de aplicação

Para desenvolvimento no Windows, use o servidor integrado do Django:

```powershell
python manage.py runserver
```

Gunicorn é um servidor WSGI para Linux/Unix e não é suportado nativamente no
Windows. Em Linux ou WSL, instale as dependências, aplique as migrações e inicie
a aplicação:

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn setup.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

Antes de expor a aplicação, configure `DJANGO_SECRET_KEY`,
`DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS` e o banco de produção. Sirva
arquivos estáticos e de mídia com um servidor dedicado ou proxy reverso; o
Gunicorn não os serve diretamente.

## Estrutura

- `contas/`: autenticação, perfis e permissões.
- `produtos/`: categorias, produtos e catálogo.
- `vendedores/`: empresas fornecedoras.
- `carrinho/`: carrinho persistido e validação de estoque.
- `pedidos/`: finalização de pedidos e acompanhamento de status.
- `recomendacoes/`: ranking e recomendações baseadas em compras.
- `dashboard/`: painéis de agricultor, fornecedor e administrador.
- `loadtest/`: cenário Locust e instruções para medição de carga.
- `templates/`: templates Django responsivos.
- `static/`: CSS, JavaScript e imagens.

## PostgreSQL

Para usar PostgreSQL, configure `DB_ENGINE`, `DB_NAME`, `DB_USER`,
`DB_PASSWORD`, `DB_HOST` e `DB_PORT` no ambiente, conforme o exemplo comentado
em `.env.example`, e execute `python manage.py migrate` no banco configurado.
