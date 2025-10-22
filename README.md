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
docker compose exec git-commit-files aws events put-events \
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
  "taskId": "1234567890",
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
```

### Trigger

```bash
docker compose exec issue-report aws events put-events --entries '
[
  {
    "Source": "mcp.tool.issue.report",
    "DetailType": "input",
    "Detail": "{\"taskId\":\"1234567890\",\"data\":{\"status\":\"SUCCESS\",\"annotations\":[{\"title\":\"My issue title\",\"description\":\"My issue description\",\"severity\":\"low\",\"path\":\"src/index.js\",\"line\":1,\"summary\":\"My issue summary\",\"code\":\"console.log( \\\"Hello, world!\\\" );\",\"recommendation\":\"Add a new function to the code\"}]}}",
    "EventBusName": "tvo-event-bus-local"
  }
]'
```