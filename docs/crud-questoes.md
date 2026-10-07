# Gestao de questoes

O painel do instrutor permite criar, consultar, publicar e excluir questoes.
Nao existe edicao de questoes nem gerenciamento de categorias nesta entrega.
As categorias continuam predefinidas, consultadas por `GET /api/categories`.

## Rotas

| Metodo | Rota | Comportamento |
| --- | --- | --- |
| GET | /api/questions | Instrutor ve todas; aluno ou visitante ve somente PUBLISHED. |
| GET | /api/questions/{id} | Detalhes e estado SOLVED/UNSOLVED do usuario. |
| POST | /api/questions | Instrutor cria uma questao validada no estado READY. |
| POST | /api/questions/{id}/publish | Instrutor publica uma questao READY. Repetir a publicacao nao duplica auditoria. |
| DELETE | /api/questions/{id} | Instrutor exclui os recursos associados. |

`publishedStatus` representa o ciclo de vida da questao; `status` nas consultas
representa SOLVED/UNSOLVED. As questoes ja publicadas permanecem publicadas.
Alunos recebem 403 ao tentar criar, publicar ou excluir. IDs inexistentes
retornam 404. Detalhes de questoes nao publicadas retornam 403 para alunos.
Submissoes tambem exigem uma questao PUBLISHED.

## Criacao e publicacao

1. A API valida titulo, dificuldade e categorias existentes, removendo categorias duplicadas.
2. O RDS reserva o ID dentro da transacao.
3. O validador executa schema.sql, data.sql e answer.sql, exige ORDER BY e calcula tabelas de exemplo, colunas e hash.
4. Os tres scripts sao enviados ao S3 antes de confirmar o registro READY no RDS.
5. Uma falha de persistencia provoca rollback e tentativa de limpeza dos arquivos e schema criados.
6. A API invalida o cache, grava o hash no Redis e registra CREATE_EXERCISE no DynamoDB.
7. O instrutor publica pelo painel. A API altera READY para PUBLISHED, atualiza o cache e registra PUBLISH_EXERCISE.

Os metadados calculados pelo validador prevalecem sobre os enviados pelo cliente.

## Exclusao

A API marca a questao como DELETING antes de limpar S3, schema PostgreSQL,
resolucoes e registro RDS. Esse estado impede novas submissoes e publicacao.
O prefixo S3 termina em `/`: excluir a questao 1 nao afeta a questao 10.
Falhas parciais do S3 ou do banco retornam 503; o painel permite repetir a
exclusao para concluir a limpeza. Apos concluir, a API invalida o cache e
registra DELETE_EXERCISE. O historico de submissoes no DynamoDB e os pontos
ja conquistados permanecem preservados.

## Limites de consistencia

Nao existe transacao distribuida entre RDS, S3, Redis e DynamoDB. Se a limpeza
compensatoria da criacao falhar, os logs identificam o ID para reconciliacao.
Redis e auditoria mantem o comportamento tolerante a falhas do projeto:
indisponibilidade gera logs, sem desfazer uma operacao ja confirmada no RDS.
Caches antigos podem durar ate o TTL de 300 segundos se a invalidacao falhar.
A auditoria nao possui fila persistente de reenvio; entrega garantida durante
indisponibilidade do DynamoDB exigiria um outbox e processamento posterior.

## Verificacao

Na raiz do repositorio, com as dependencias Python instaladas:

```powershell
.venv\Scripts\python.exe -m pytest app/testes/test_questions_crud.py -q
```

Os testes usam SQLite com chaves estrangeiras habilitadas e simulam os
servicos externos. Cobrem ciclo completo, permissoes, validacao, cache,
auditoria, rollback e retomada de exclusao. Nao substituem a verificacao
integrada com PostgreSQL, Redis, S3 e DynamoDB em execucao.

No diretorio frontend:

```powershell
npm.cmd run build
npm.cmd run dev
```
