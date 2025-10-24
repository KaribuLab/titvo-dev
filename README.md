# Titvo Dev

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
  "task_id": "1234567890",
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
    "Detail": "{\"task_id\":\"1234567890\",\"data\":{\"status\":\"SUCCESS\",\"annotations\":[{\"title\":\"My issue title\",\"description\":\"My issue description\",\"severity\":\"low\",\"path\":\"src/index.js\",\"line\":1,\"summary\":\"My issue summary\",\"code\":\"console.log( \\\"Hello, world!\\\" );\",\"recommendation\":\"Add a new function to the code\"}]}}",
    "EventBusName": "tvo-event-bus-local"
  }
]'
```

## MCP Bitbucket Code Insights

### Input
```json
{
  "task_id": "1234567890",
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
    "Detail": "{\"task_id\":\"1234567890\",\"data\":{\"report_url\":\"https://example.com/reports/1234567890.html\",\"workspace_id\":\"karibu-cl\",\"commit_hash\":\"1535092799115cc465e091fb2f06473e41ed88c5\",\"repo_slug\":\"krb-web-ui-vulnerable\",\"status\":\"SUCCESS\",\"annotations\":[{\"title\":\"My issue title\",\"description\":\"My issue description\",\"severity\":\"low\",\"path\":\"src/index.js\",\"line\":1,\"summary\":\"My issue summary\",\"recommendation\":\"Add a new function to the code\"}]}}",
    "EventBusName": "tvo-event-bus-local"
  }
]'
```