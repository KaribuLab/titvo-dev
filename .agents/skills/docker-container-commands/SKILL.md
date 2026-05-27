---
name: docker-container-commands
description: 
---

# docker-container-commands

This skill is used to interact with docker compose containers.:

- logs-lambda: Like a tail command for Cloudwatch in localstack. This shell get the Cloudwatch log name using cdk local.
- api-gateway-url: Get the API Gateway URL from cdk local.
- get-api-key: Get the API Key of Titvo needed for local execution.

## Example:

Get the Titvo API Key:

```bash
docker compose exec cdk get-api-key
```

Get the logs from `git-commit-files` service:

```bash
docker compose exec git-commit-files logs-lambda
```

Get the API Gateway URL of Titvo:

```bash
docker compose exec trigger api-gateway-url
```

Other ways to use with AWS CLI local:

```bash
docker compose exec cdk aws sts get-caller-identity
```

## When to use

This skill should be used when you need get information from this services of `docker-compose.yaml` file:
- trigger
- issue-report
- github-issue
- bitbucket-code-insights
- git-commit-files

## Instructions

Run the command with the following syntax:

```bash
docker compose exec <service> <command>
```
