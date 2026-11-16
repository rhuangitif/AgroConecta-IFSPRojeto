# Teste de carga com Locust

O cenário executa uma única jornada por usuário simulado: abre a listagem de
produtos, acessa o detalhe de um produto, autentica uma conta agricultora,
adiciona uma unidade ao carrinho e finaliza o pedido. Cada etapa aparece
separadamente nas estatísticas do Locust. A jornada única evita que um usuário
virtual consuma estoque repetidamente durante a medição.

## Preparar dados de teste

1. Use uma instância de teste, nunca a produção.
2. Crie 20 contas **agricultoras** exclusivas e ativas, cada uma com carrinho
   vazio. Não use contas reais nem credenciais de produção.
3. Escolha um produto ativo e público, com estoque de pelo menos 20 unidades.
   Anote o ID exibido na URL de detalhes, por exemplo
   `http://127.0.0.1:8000/produtos/123/` tem ID `123`.
4. Crie `loadtest\users.csv` com uma linha para cada conta:

   ```csv
   username,password
   agricultor-teste-01@example.test,senha-de-teste
   agricultor-teste-02@example.test,outra-senha-de-teste
   ```

   O arquivo `users.csv` é ignorado pelo Git. Não o versione. Para usar outro
   caminho, defina `LOADTEST_USERS_CSV`.
5. Instale o Locust no mesmo ambiente Python usado para o projeto:

   ```powershell
   python -m pip install "locust>=2.32,<3"
   ```

   Faça as migrações e inicie o servidor local ou de teste em outro terminal:

   ```powershell
   python manage.py migrate
   python manage.py runserver 127.0.0.1:8000
   ```

## Executar com 20 usuários simultâneos

No PowerShell, na raiz do projeto:

```powershell
$env:LOADTEST_PRODUCT_ID = "123"
python -m locust -f loadtest\locustfile.py --headless --host http://127.0.0.1:8000 --users 20 --spawn-rate 20 --run-time 2m --csv loadtest\resultados
```

Substitua `123` pelo ID do produto escolhido. O CSV precisa conter ao menos 20
contas válidas. A mesma execução e a forma de iniciar o servidor aplicam-se a
outro ambiente de teste; ajuste `--host` para o endereço desse ambiente.

Se uma execução for interrompida após adicionar itens, limpe os carrinhos dessas
contas antes de repetir. Reponha o estoque consumido entre medições. Os pedidos
de teste permanecem no banco e podem ser removidos ou restaurados conforme o
procedimento de limpeza do ambiente de teste.

## Registrar as medições reais

Ao terminar, o Locust cria arquivos como `loadtest\resultados_stats.csv` e
`loadtest\resultados_failures.csv`. No arquivo `_stats.csv`, registre para o
total e para cada etapa relevante:

- **Tempo médio**: coluna `Average Response Time`.
- **Percentil 95 (P95)**: coluna `95%`.
- **Taxa de erro**: `Failures / Requests * 100`, usando as colunas `Failures` e
  `Request Count`. Também confira `Failure %` quando disponível.

Registre junto com os valores a data/hora, URL/ambiente, versão do código,
quantidade de usuários e taxa de inicialização usada. Os resultados dependem
dos dados e do ambiente; este projeto não inclui medições pré-calculadas.
Os arquivos de resultados são locais e não devem ser versionados.
