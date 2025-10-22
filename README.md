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
  "issueId": "abc123",
  "issueTitle": "My issue title",
  "issueDescription": "My issue description",
  "issueSeverity": "low",
  "issueStatus": "open"
}
```

### Trigger

```bash
docker compose exec issue-report aws events put-events \
  --entries '[
    {
      "Source": "mcp.tool.issue.report",
      "DetailType": "input",
      "Detail": "{\"issueId\":\"abc123\",\"issueTitle\":\"My issue title\",\"issueDescription\":\"My issue description\",\"issueSeverity\":\"low\",\"issueStatus\":\"open\"}",
      "EventBusName": "tvo-event-bus-local"
    }
  ]'
```