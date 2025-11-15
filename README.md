# Titvo Dev

## CDK

La imagen de CDK se encuentra en el archivo `docker/cdk/Dockerfile`. En el archivo `setup.ts` se encuentra la configuración inicial de la aplicación.

Esta imagen tiene algunas utilidades para facilitar el desarrollo de la aplicación.

### Get API Key

```bash
docker compose exec cdk get-api-key
```

## Lambda Functions

### Logs CloudWatch

Para ver los logs de las funciones lambda, se puede usar el siguiente comando:

```bash
docker compose exec git-commit-files logs-lambda
```

Este comando obtiene el nombre del grupo de logs de CloudWatch a partir del stack de CDK (usando la variable `CDK_STACK_NAME`) y muestra los logs en tiempo real.

### API Gateway URL

Para obtener la URL del API Gateway de una función lambda específica, se puede usar el siguiente comando:

```bash
docker compose exec trigger api-gateway-url
```

Este comando obtiene la URL del API Gateway a partir del stack de CDK (usando la variable `CDK_STACK_NAME`). El comando `api-gateway-url` está disponible en todos los contenedores lambda que tienen un API Gateway asociado.

## API Gateway

### Task

Con las utilidades de la imagen de CDK, se puede obtener la URL base de la API Gateway para el servicio de Task.

En el directorio `src/api/task/trigger` se el archivo `task.http` con las peticiones para el servicio de Task.

Antes de ejecutar las peticiones, se debe setear en el archivo `.env` (que debe estar ubicado en el directorio `src/api/task/trigger`) la variable `API_URL` con la URL base de la API Gateway.

```bash
API_URL=https://3i8adfasc1.execute-api.localhost.localstack.cloud:4566/localstack
```

## MCP Git Commit Files

### Input

```json
{
  "status": "success",
  "commitId": "abc123",
  "repository": "https://github.com/my-repo.git",
  "branch": "main",
  "commitMessage": "My commit message",
  "commitAuthor": "My commit author",
  "commitDate": "2021-01-01"
}
```

### Trigger

```bash
docker compose exec localstack awslocal events put-events --region us-east-1 \
  --entries '[
    {
      "Source": "mcp.tool.git.commit-files",
      "DetailType": "input",
      "Detail": "{\"status\":\"success\",\"commitId\":\"abc123\",\"repository\":\"https://github.com/my-repo.git\",\"branch\":\"main\",\"commitMessage\":\"My commit message\",\"commitAuthor\":\"My commit author\",\"commitDate\":\"2021-01-01\"}",
      "EventBusName": "tvo-event-bus-local"
    }
  ]'
```

## MCP Issue Report

### Input

```json
{
  "job_id": "1234567890",
  "data": {
    "status": "SUCCESS",
    "annotations": [
      {
        "title": "My issue title",
        "description": "My issue description",
        "severity": "low",
        "path": "src/index.js",
        "line": 1,
        "summary": "My issue summary",
        "code": "console.log( Hello, world! );",
        "recommendation": "Add a new function to the code"
      }
    ]
  }
}
```

### Trigger

```bash
docker compose exec localstack awslocal events put-events --region us-east-1 --entries '
[
  {
    "Source": "mcp.tool.issue.report",
    "DetailType": "input",
    "Detail": "{\"job_id\":\"1234567890\",\"data\":{\"status\":\"SUCCESS\",\"annotations\":[{\"title\":\"My issue title\",\"description\":\"My issue description\",\"severity\":\"low\",\"path\":\"src/index.js\",\"line\":1,\"summary\":\"My issue summary\",\"code\":\"console.log( \\\"Hello, world!\\\" );\",\"recommendation\":\"Add a new function to the code\"}]}}",
    "EventBusName": "tvo-event-bus-local"
  }
]'
```

## MCP Bitbucket Code Insights

### Input

```json
{
  "job_id": "1234567890",
  "data": {
    "report_url": "https://example.com/reports/1234567890.html",
    "workspace_id": "karibu-cl",
    "commit_hash": "1535092799115cc465e091fb2f06473e41ed88c5",
    "repo_slug": "krb-web-ui-vulnerable",
    "status": "SUCCESS",
    "annotations": [
      {
        "title": "My issue title",
        "description": "My issue description",
        "severity": "low",
        "path": "src/index.js",
        "line": 1,
        "summary": "My issue summary",
        "recommendation": "Add a new function to the code"
      }
    ]
  }
}
```

### Trigger

```bash
docker compose exec localstack awslocal events put-events --region us-east-1 --entries '
[
  {
    "Source": "mcp.tool.bitbucket.code-insights",
    "DetailType": "input",
    "Detail": "{\"job_id\":\"1234567890\",\"data\":{\"report_url\":\"https://example.com/reports/1234567890.html\",\"workspace_id\":\"karibu-cl\",\"commit_hash\":\"1535092799115cc465e091fb2f06473e41ed88c5\",\"repo_slug\":\"krb-web-ui-vulnerable\",\"status\":\"SUCCESS\",\"annotations\":[{\"title\":\"My issue title\",\"description\":\"My issue description\",\"severity\":\"low\",\"path\":\"src/index.js\",\"line\":1,\"summary\":\"My issue summary\",\"recommendation\":\"Add a new function to the code\"}]}}",
    "EventBusName": "tvo-event-bus-local"
  }
]'
```

## MCP Github Issue

### Input

```json
{
  "job_id": "1234567890",
  "data": {
    "repo_owner": "pascencio",
    "repo_name": "devsecops",
    "asignee": "pascencio",
    "commit_hash": "7f5ccb64e095f20ea15d33f20b98375a2d9c78b0",
    "status": "SUCCESS",
    "annotations": [
      {
        "title": "My issue title",
        "description": "My issue description",
        "severity": "low",
        "path": "src/index.js",
        "code": "console.log( \"Hello, world!\" );",
        "line": 1,
        "summary": "My issue summary",
        "recommendation": "Add a new function to the code"
      }
    ]
  }
}
```

### Trigger

```bash
docker compose exec localstack awslocal events put-events --region us-east-1 --entries '
[
  {
    "Source": "mcp.tool.github.issue",
    "DetailType": "input",
    "Detail": "{\"job_id\":\"1234567890\",\"data\":{\"repo_owner\":\"pascencio\",\"repo_name\":\"devsecops\",\"asignee\":\"pascencio\",\"commit_hash\":\"7f5ccb64e095f20ea15d33f20b98375a2d9c78b0\",\"status\":\"SUCCESS\",\"annotations\":[{\"title\":\"My issue title\",\"description\":\"My issue description\",\"severity\":\"low\",\"path\":\"src/index.js\",\"code\":\"console.log( \\\"Hello, world!\\\" );\",\"line\":1,\"summary\":\"My issue summary\",\"recommendation\":\"Add a new function to the code\"}]}}",
    "EventBusName": "tvo-event-bus-local"
  }
]'
```