---
name: deploy-image
description: Publish the gateway Docker image to ECR and roll out a new ECS task without changing the task definition. Use when deploying the MCP gateway to AWS, forcing ECS to pull latest, or restarting the gateway container. Does not apply to agent (AWS Batch).
---

# deploy-image

Publish the **gateway** container image and replace the running ECS task so it pulls the new image, even when the task definition did not change (same tag, e.g. `latest`).

**Scope:** MCP gateway only. The **agent** runs on **AWS Batch** — use [push-ecr](../push-ecr/SKILL.md) for the agent image and do not use this skill.

## When to use

- Deploy the **gateway** after code changes
- The gateway image was already pushed to ECR but ECS still runs the old task
- User asks to restart/redeploy the gateway container in ECS

## Prerequisites

Read and follow these skills first:

- [push-ecr](../push-ecr/SKILL.md) — build and publish the gateway Docker image to ECR
- [dotenv](../dotenv/SKILL.md) — load AWS credentials from the workspace `.env.aws`

Run all commands from the **workspace root** unless noted otherwise.

## Workflow

### 1. Publish the gateway image (skip if already pushed)

Follow [push-ecr](../push-ecr/SKILL.md) with:

| `GIT_URL` | `IMAGE_REPO` |
|---|---|
| `https://github.com/KaribuLab/titvo-mcp-gateway.git` | `tvo-mcp-gateway-ecr-prod` |

Commit and push gateway changes to `main` before publishing.

Save the image digest from the publisher output (for verification).

### 2. Load AWS credentials

```shell
set -a && source /path/to/workspace/.env.aws && set +a
```

Use the full path to `.env.aws` in the workspace root.

### 3. Force a new ECS deployment

When the task definition is unchanged, ECS will not redeploy automatically after a new `:latest` image is pushed. Force a rolling replacement:

```shell
aws ecs update-service \
  --cluster tvo-security-scan-cluster-prod \
  --service tvo-mcp-gateway-service-prod \
  --force-new-deployment \
  --region "${AWS_REGION:-us-east-2}"
```

### 4. Wait for rollout

Poll until there is a single `PRIMARY` deployment with `rolloutState=COMPLETED`:

```shell
aws ecs describe-services \
  --cluster tvo-security-scan-cluster-prod \
  --services tvo-mcp-gateway-service-prod \
  --region "${AWS_REGION:-us-east-2}" \
  --query 'services[0].deployments[*].{status:status,rollout:rolloutState,running:runningCount,desired:desiredCount,createdAt:createdAt}'
```

Expect briefly `runningCount=2` while the new task starts and the old one drains.

### 5. Verify the new task

```shell
TASK=$(aws ecs list-tasks \
  --cluster tvo-security-scan-cluster-prod \
  --service-name tvo-mcp-gateway-service-prod \
  --desired-status RUNNING \
  --region "${AWS_REGION:-us-east-2}" \
  --query 'taskArns[0]' \
  --output text)

aws ecs describe-tasks \
  --cluster tvo-security-scan-cluster-prod \
  --tasks "$TASK" \
  --region "${AWS_REGION:-us-east-2}" \
  --query 'tasks[0].{startedAt:startedAt,image:containers[0].image,digest:containers[0].imageDigest}'
```

Confirm `digest` matches the digest reported by [push-ecr](../push-ecr/SKILL.md).

## Troubleshooting

| Symptom | Action |
|---|---|
| Service/cluster not found | List clusters: `aws ecs list-clusters --region "${AWS_REGION:-us-east-2}"` |
| Rollout stuck `IN_PROGRESS` | Check events: `aws ecs describe-services --cluster ... --services ... --query 'services[0].events[:5]'` |
| Task still on old digest | Confirm ECR publish succeeded; run `--force-new-deployment` again |
| AWS auth errors | Reload credentials with [dotenv](../dotenv/SKILL.md) |

## References

- [push-ecr](../push-ecr/SKILL.md)
- [dotenv](../dotenv/SKILL.md)
